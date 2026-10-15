import os
import logging
from flask import Flask, jsonify, render_template, send_from_directory
from config import Config
from models.database import get_db, DatabaseManager
from models.user import UserModel
from api import auth_bp, student_bp, face_bp, attendance_bp, report_bp

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(config_class)

    # 1. Connect database & ensure indexes
    with app.app_context():
        try:
            db = get_db()
            logger.info("Database initialized successfully.")
            _seed_default_accounts()
        except Exception as e:
            logger.error("Database initialization warning: %s", e)

    # 2. Register REST Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(face_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(report_bp)

    # 3. Health-Check Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        db_alive = False
        try:
            db = get_db()
            db.command("ping")
            db_alive = True
        except Exception:
            db_alive = DatabaseManager.is_mock

        models_loaded = (
            os.path.exists(Config.YUNET_MODEL_PATH) and
            os.path.exists(Config.SFACE_MODEL_PATH)
        )

        return jsonify({
            "status": "healthy" if (db_alive and models_loaded) else "degraded",
            "service": "AlphabetAI Attendance",
            "version": "1.0.0",
            "database": {
                "connected": db_alive,
                "is_fallback_mock": DatabaseManager.is_mock
            },
            "models": {
                "yunet_detection_ready": os.path.exists(Config.YUNET_MODEL_PATH),
                "sface_recognition_ready": os.path.exists(Config.SFACE_MODEL_PATH)
            }
        })

    # 4. Frontend Web Dashboard
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    # 5. Centralized Error Handlers (Secure, consistent JSON, zero stack trace leak)
    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({"success": False, "error_code": "BAD_REQUEST", "error": "Bad request format or invalid parameters."}), 400

    @app.errorhandler(401)
    def handle_unauthorized(e):
        return jsonify({"success": False, "error_code": "UNAUTHORIZED", "error": "Authentication required."}), 401

    @app.errorhandler(403)
    def handle_forbidden(e):
        return jsonify({"success": False, "error_code": "FORBIDDEN", "error": "Access forbidden for this account."}), 403

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"success": False, "error_code": "NOT_FOUND", "error": "The requested resource was not found."}), 404

    @app.errorhandler(422)
    def handle_unprocessable(e):
        return jsonify({"success": False, "error_code": "UNPROCESSABLE_ENTITY", "error": "Unable to process payload."}), 422

    @app.errorhandler(500)
    def handle_server_error(e):
        logger.error("Internal Server Error: %s", e)
        return jsonify({"success": False, "error_code": "INTERNAL_SERVER_ERROR", "error": "An internal server error occurred. Please try again later."}), 500

    return app

def _seed_default_accounts():
    """Seeds default teacher and admin accounts for testing and demonstration."""
    try:
        if not UserModel.find_by_username("admin"):
            UserModel.create_user(
                username="admin",
                password="AdminPassword123!",
                full_name="System Administrator",
                role="admin",
                assigned_classes=["Grade-10A", "Grade-10B", "Grade-11A"]
            )
            logger.info("Default admin created: admin / AdminPassword123!")

        if not UserModel.find_by_username("teacher"):
            UserModel.create_user(
                username="teacher",
                password="TeacherPassword123!",
                full_name="Prof. Sarah Jenkins",
                role="teacher",
                assigned_classes=["Grade-10A", "Grade-10B"]
            )
            logger.info("Default teacher created: teacher / TeacherPassword123!")

        db = get_db()
        if db.students.count_documents({}) == 0:
            from scripts.seed_data import seed_database
            seed_database()
            logger.info("Auto-seeded initial A-Z students.")
    except Exception as e:
        logger.warning("Could not auto-seed accounts: %s", e)

if __name__ == "__main__":
    app = create_app()
    # Runs locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=False)
