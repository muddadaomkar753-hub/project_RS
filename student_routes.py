from flask import Blueprint, request, jsonify, g
from models.student import StudentModel
from models.face_enrollment import FaceEnrollmentModel
from models.audit import AuditLogModel
from services.auth_service import require_auth

student_bp = Blueprint("student_bp", __name__, url_prefix="/api/students")

@student_bp.route("", methods=["GET"])
@require_auth()
def list_students():
    class_id = request.args.get("class_id")
    section = request.args.get("section")
    search_query = request.args.get("search")
    sort_by = request.args.get("sort_by", "alphabetical")
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    students = StudentModel.get_students(
        class_id=class_id,
        section=section,
        search_query=search_query,
        sort_by=sort_by,
        include_inactive=include_inactive
    )
    return jsonify({
        "success": True,
        "count": len(students),
        "sort_by": sort_by,
        "students": students
    })

@student_bp.route("", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def register_student():
    data = request.get_json(silent=True) or {}
    try:
        student = StudentModel.register_student(
            student_id=data.get("student_id", ""),
            full_name=data.get("full_name", ""),
            roll_number=data.get("roll_number", 0),
            class_id=data.get("class_id", ""),
            section=data.get("section", ""),
            academic_year=data.get("academic_year", "2025-2026"),
            consent_status=data.get("consent_status", False),
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            guardian_name=data.get("guardian_name", "")
        )
        AuditLogModel.log_event(
            g.current_user["username"],
            "REGISTER_STUDENT",
            {"student_id": student["student_id"], "class_id": student["class_id"], "roll": student["roll_number"]}
        )
        return jsonify({"success": True, "student": student}), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal registration error: {str(e)}"}), 500

@student_bp.route("/<student_id>", methods=["GET"])
@require_auth()
def get_student(student_id: str):
    student = StudentModel.get_by_student_id(student_id)
    if not student:
        return jsonify({"success": False, "error": f"Student '{student_id}' not found."}), 404

    enrollment = FaceEnrollmentModel.get_by_student_id(student_id, include_vector=False)
    student["face_enrollment_details"] = enrollment
    return jsonify({"success": True, "student": student})

@student_bp.route("/<student_id>", methods=["PATCH"])
@require_auth(roles=["admin", "teacher"])
def update_student(student_id: str):
    data = request.get_json(silent=True) or {}
    try:
        updated = StudentModel.update_student(student_id, data)
        AuditLogModel.log_event(g.current_user["username"], "UPDATE_STUDENT", {"student_id": student_id, "fields": list(data.keys())})
        return jsonify({"success": True, "student": updated})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@student_bp.route("/<student_id>/deactivate", methods=["POST"])
@require_auth(roles=["admin", "teacher"])
def deactivate_student(student_id: str):
    try:
        updated = StudentModel.deactivate_student(student_id)
        AuditLogModel.log_event(g.current_user["username"], "DEACTIVATE_STUDENT", {"student_id": student_id})
        return jsonify({"success": True, "message": "Student deactivated. Historical records preserved.", "student": updated})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
