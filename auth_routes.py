from flask import Blueprint, request, jsonify, g
from models.user import UserModel
from models.audit import AuditLogModel
from services.auth_service import AuthService, require_auth

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400

    user = UserModel.find_by_username(username)
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password."}), 401

    if user.get("account_status") != "active":
        return jsonify({"success": False, "error": "Account is disabled. Contact your administrator."}), 403

    if not UserModel.verify_password(password, user["password_hash"]):
        return jsonify({"success": False, "error": "Invalid username or password."}), 401

    token = AuthService.generate_token(user)
    AuditLogModel.log_event(user["username"], "USER_LOGIN", {"role": user.get("role")})

    resp = jsonify({
        "success": True,
        "token": token,
        "user": UserModel.to_safe_dict(user)
    })
    resp.set_cookie("alphabetai_token", token, httponly=True, samesite="Lax")
    return resp

@auth_bp.route("/logout", methods=["POST"])
@require_auth()
def logout():
    AuditLogModel.log_event(g.current_user["username"], "USER_LOGOUT")
    resp = jsonify({"success": True, "message": "Logged out successfully."})
    resp.delete_cookie("alphabetai_token")
    return resp

@auth_bp.route("/me", methods=["GET"])
@require_auth()
def get_me():
    return jsonify({
        "success": True,
        "user": UserModel.to_safe_dict(g.current_user)
    })
