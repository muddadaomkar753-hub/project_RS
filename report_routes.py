from flask import Blueprint, request, jsonify, Response
from services.report_service import ReportService
from services.auth_service import require_auth
from models.audit import AuditLogModel

report_bp = Blueprint("report_bp", __name__, url_prefix="/api/reports")

@report_bp.route("/dashboard", methods=["GET"])
@require_auth()
def get_dashboard():
    stats = ReportService.get_dashboard_stats()
    return jsonify({"success": True, "stats": stats})

@report_bp.route("/session/<session_id>", methods=["GET"])
@require_auth()
def get_session_report(session_id: str):
    try:
        data = ReportService.get_session_report(session_id)
        return jsonify({"success": True, "report": data})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/session/<session_id>/csv", methods=["GET"])
@require_auth()
def download_session_csv(session_id: str):
    try:
        csv_content = ReportService.generate_csv_report(session_id)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=attendance_session_{session_id}.csv"}
        )
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/student/<student_id>", methods=["GET"])
@require_auth()
def get_student_report(student_id: str):
    try:
        data = ReportService.get_student_history(student_id)
        return jsonify({"success": True, "history": data})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/audit", methods=["GET"])
@require_auth(roles=["admin"])
def get_audit_trail():
    limit = int(request.args.get("limit", 100))
    logs = AuditLogModel.get_logs(limit=limit)
    return jsonify({"success": True, "count": len(logs), "logs": logs})
