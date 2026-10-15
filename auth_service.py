import hmac
import hashlib
import json
import base64
import time
from functools import wraps
from flask import request, jsonify, g
from config import Config
from models.user import UserModel

class AuthService:
    SECRET = Config.SECRET_KEY.encode("utf-8")

    @classmethod
    def generate_token(cls, user_doc: dict) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": str(user_doc["_id"]),
            "username": user_doc["username"],
            "role": user_doc.get("role", "teacher"),
            "full_name": user_doc.get("full_name", ""),
            "assigned_classes": user_doc.get("assigned_classes", []),
            "iat": now,
            "exp": now + Config.TOKEN_EXPIRY_SECONDS
        }

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature_raw = hmac.new(cls.SECRET, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(signature_raw).decode().rstrip("=")

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    @classmethod
    def verify_token(cls, token: str):
        if not token:
            return None
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        expected_sig_raw = hmac.new(cls.SECRET, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig_raw).decode().rstrip("=")

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        try:
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += "=" * (4 - rem)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
            if payload.get("exp", 0) < int(time.time()):
                return None  # Expired
            return payload
        except Exception:
            return None

    @classmethod
    def get_token_from_request(cls):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        # Fallback to cookie
        return request.cookies.get("alphabetai_token", None)

def require_auth(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = AuthService.get_token_from_request()
            if not token:
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401

            payload = AuthService.verify_token(token)
            if not payload:
                return jsonify({"success": False, "error": "Invalid or expired session token."}), 401

            user = UserModel.find_by_id(payload.get("sub"))
            if not user or user.get("account_status") != "active":
                return jsonify({"success": False, "error": "User account inactive or not found."}), 401

            g.current_user = user
            g.user_payload = payload

            if roles and user.get("role") not in roles:
                return jsonify({"success": False, "error": f"Forbidden: '{user.get('role')}' role lacks permission."}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
