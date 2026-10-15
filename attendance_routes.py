from flask import Blueprint, request, jsonify, g
from models.attendance import AttendanceModel
from models.audit import AuditLogModel
from services.attendance_engine import AttendanceEngine
from services.auth_service import require_auth

attendance_bp = Blueprint("attendance_bp", __name__, url_prefix="/api/attendance")

@attendance_bp.route("/sessions", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def create_session():
    data = request.get_json(silent=True) or {}
    class_id = data.get("class_id", "").strip()
    section = data.get("section", "").strip().upper()
    session_date = data.get("session_date")
    session_name = data.get("session_name", "Regular Attendance")
    academic_year = data.get("academic_year", "2025-2026")

    if not class_id or not section:
        return jsonify({"success": False, "error": "Class ID and Section are required to start an attendance session."}), 400

    try:
        session = AttendanceModel.create_session(
            class_id=class_id,
            section=section,
            created_by=g.current_user["username"],
            session_date=session_date,
            session_name=session_name,
            academic_year=academic_year
        )
        AuditLogModel.log_event(
            g.current_user["username"],
            "CREATE_SESSION",
            {"session_id": session["_id"], "class_id": class_id, "section": section}
        )
        return jsonify({"success": True, "session": session}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@attendance_bp.route("/sessions", methods=["GET"])
@require_auth()
def list_sessions():
    class_id = request.args.get("class_id")
    section = request.args.get("section")
    session_date = request.args.get("session_date")
    status = request.args.get("status")

    sessions = AttendanceModel.get_sessions(
        class_id=class_id,
        section=section,
        session_date=session_date,
        status=status
    )
    return jsonify({"success": True, "count": len(sessions), "sessions": sessions})

@attendance_bp.route("/sessions/<session_id>", methods=["GET"])
@require_auth()
def get_session(session_id: str):
    session = AttendanceModel.get_session(session_id)
    if not session:
        return jsonify({"success": False, "error": "Attendance session not found."}), 404
    return jsonify({"success": True, "session": session})

@attendance_bp.route("/sessions/<session_id>/queue", methods=["GET"])
@require_auth()
def get_session_queue(session_id: str):
    """
    Returns the real-time Alphabetical Attendance Queue for the given session.
    """
    sort_by = request.args.get("sort_by", "alphabetical")
    current_student_id = request.args.get("current_student_id")
    skipped_param = request.args.get("skipped_ids", "")
    skipped_ids = [s.strip() for s in skipped_param.split(",") if s.strip()]

    try:
        queue_data = AttendanceEngine.get_session_queue(
            session_id=session_id,
            sort_by=sort_by,
            current_student_id=current_student_id,
            skipped_ids=skipped_ids
        )
        return jsonify({"success": True, "queue_data": queue_data})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@attendance_bp.route("/sessions/<session_id>/records", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def record_attendance(session_id: str):
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id", "").strip()
    status = data.get("status", "present").strip().lower()
    method = data.get("verification_method", "teacher_manual_override")
    outcome = data.get("verification_outcome", f"manual_{status}")
    confidence_score = data.get("confidence_score")

    if not student_id:
        return jsonify({"success": False, "error": "Student ID is required."}), 400

    try:
        record = AttendanceModel.record_attendance(
            session_id=session_id,
            student_id=student_id,
            status=status,
            verification_method=method,
            verification_outcome=outcome,
            recorded_by=g.current_user["username"],
            confidence_score=confidence_score
        )
        AuditLogModel.log_event(
            g.current_user["username"],
            "RECORD_ATTENDANCE",
            {"session_id": session_id, "student_id": student_id, "status": status, "method": method}
        )
        return jsonify({"success": True, "record": record}), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@attendance_bp.route("/records/<record_id>", methods=["PATCH"])
@require_auth(roles=["admin", "teacher"])
def correct_record(record_id: str):
    data = request.get_json(silent=True) or {}
    new_status = data.get("new_status", "").strip().lower()
    reason = data.get("reason", "").strip()

    if not new_status or not reason:
        return jsonify({"success": False, "error": "Both new_status and an explicit reason are mandatory for corrections."}), 400

    try:
        updated = AttendanceModel.correct_attendance_record(
            record_id=record_id,
            new_status=new_status,
            reason=reason,
            corrected_by=g.current_user["username"]
        )
        return jsonify({"success": True, "record": updated, "message": "Attendance record successfully corrected."})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@attendance_bp.route("/sessions/<session_id>/close", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def close_session(session_id: str):
    data = request.get_json(silent=True) or {}
    policy = data.get("closing_policy", "mark_unprocessed_absent")

    try:
        closed = AttendanceModel.close_session(
            session_id=session_id,
            closed_by=g.current_user["username"],
            closing_policy=policy
        )
        AuditLogModel.log_event(
            g.current_user["username"],
            "CLOSE_SESSION",
            {"session_id": session_id, "closing_policy": policy}
        )
        return jsonify({"success": True, "session": closed, "message": "Session completed successfully."})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
