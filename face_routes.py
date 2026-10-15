from flask import Blueprint, request, jsonify, g
from models.student import StudentModel
from models.face_enrollment import FaceEnrollmentModel
from models.attendance import AttendanceModel
from models.audit import AuditLogModel
from services.auth_service import require_auth
from services.face_service import FaceService

face_bp = Blueprint("face_bp", __name__, url_prefix="/api/face")

@face_bp.route("/enroll", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def enroll_face():
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id", "").strip()
    image_data = data.get("image_data", "")
    consent_signed = bool(data.get("consent_signed", False))

    if not student_id or not image_data:
        return jsonify({"success": False, "error": "Student ID and image frame data are required."}), 400

    if not consent_signed:
        return jsonify({"success": False, "error": "Explicit biometric consent must be acknowledged before enrollment."}), 400

    student = StudentModel.get_by_student_id(student_id)
    if not student or not student.get("is_active"):
        return jsonify({"success": False, "error": f"Active student '{student_id}' not found."}), 404

    try:
        img = FaceService.decode_base64_image(image_data)
        detection_result = FaceService.detect_and_extract_face(img, check_quality=True)

        if not detection_result["success"]:
            return jsonify({
                "success": False,
                "error_code": detection_result.get("error_code"),
                "error": detection_result.get("error"),
                "quality": detection_result.get("quality")
            }), 422

        feature_vector = detection_result["feature_vector"]
        quality = detection_result.get("quality", {})
        blur_val = quality.get("blur_score", 50.0)
        bright_val = quality.get("brightness", 100.0)
        conf = detection_result.get("face_box", {}).get("confidence", 0.95)

        saved = FaceEnrollmentModel.save_enrollment(
            student_id=student_id,
            feature_vector=feature_vector,
            quality_score=conf,
            blur_metric=blur_val,
            brightness_metric=bright_val,
            consent_signed=True
        )

        AuditLogModel.log_event(
            g.current_user["username"],
            "ENROLL_FACE",
            {"student_id": student_id, "quality_score": conf}
        )

        return jsonify({
            "success": True,
            "message": f"Biometric face representation enrolled successfully for student '{student['full_name']}'.",
            "enrollment": saved
        })

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Biometric processing failure: {str(e)}"}), 500

@face_bp.route("/verify", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def verify_face():
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id", "").strip()
    session_id = data.get("session_id", "").strip()
    image_data = data.get("image_data", "")
    auto_record = data.get("auto_record", True)

    if not student_id or not session_id or not image_data:
        return jsonify({"success": False, "error": "student_id, session_id, and image_data are required."}), 400

    # 1. Validate Session
    session = AttendanceModel.get_session(session_id)
    if not session:
        return jsonify({"success": False, "error": "Invalid attendance session ID."}), 404
    if session.get("status") != "active":
        return jsonify({"success": False, "error": f"Attendance session is '{session.get('status')}'. Only active sessions can record attendance."}), 400

    # 2. Validate Student & Enrollment
    student = StudentModel.get_by_student_id(student_id)
    if not student or not student.get("is_active"):
        return jsonify({"success": False, "error": f"Active student '{student_id}' not found."}), 404

    enrolled = FaceEnrollmentModel.get_by_student_id(student_id, include_vector=True)
    if not enrolled or not enrolled.get("feature_vector"):
        return jsonify({
            "success": False,
            "error_code": "NOT_ENROLLED",
            "error": f"Student '{student['full_name']}' does not have an enrolled biometric face profile. Use manual attendance or enroll face first."
        }), 400

    # 3. Decode & Detect Face in Captured Camera Frame
    try:
        img = FaceService.decode_base64_image(image_data)
        detection = FaceService.detect_and_extract_face(img, check_quality=True)

        if not detection["success"]:
            return jsonify({
                "success": False,
                "verified": False,
                "error_code": detection.get("error_code"),
                "error": detection.get("error"),
                "quality": detection.get("quality")
            }), 422

        captured_vector = detection["feature_vector"]
        enrolled_vector = enrolled["feature_vector"]

        # 4. Authenticate 1-to-1 Cosine Similarity
        verification = FaceService.verify_identity(captured_vector, enrolled_vector)
        score = verification["similarity_score"]
        status = verification["status"]

        record = None
        if verification["verified"] and auto_record:
            # Atomic database insertion with duplicate protection
            try:
                record = AttendanceModel.record_attendance(
                    session_id=session_id,
                    student_id=student_id,
                    status="present",
                    verification_method="ai_face_verification",
                    verification_outcome="verified_match",
                    recorded_by=g.current_user["username"],
                    confidence_score=score
                )
            except ValueError as ve:
                # Catch duplicate record attempts
                return jsonify({
                    "success": True,
                    "verified": True,
                    "already_recorded": True,
                    "similarity_score": score,
                    "message": str(ve)
                }), 200

        return jsonify({
            "success": True,
            "student_id": student_id,
            "student_name": student["full_name"],
            "verification": verification,
            "face_box": detection.get("face_box"),
            "quality": detection.get("quality"),
            "record": record
        })

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Verification pipeline error: {str(e)}"}), 500

@face_bp.route("/enroll/<student_id>", methods=["DELETE"])
@require_auth(roles=["admin", "teacher"])
def revoke_biometrics(student_id: str):
    """Controlled deletion of biometric representation for privacy rights."""
    try:
        FaceEnrollmentModel.revoke_enrollment(student_id)
        AuditLogModel.log_event(g.current_user["username"], "REVOKE_BIOMETRICS", {"student_id": student_id})
        return jsonify({"success": True, "message": f"Biometric data for student '{student_id}' has been permanently purged."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
