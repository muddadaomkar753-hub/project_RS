import pytest
import time
from models.user import UserModel
from services.auth_service import AuthService

def test_password_hashing():
    pwd = "SecureTeacherPass2026!"
    hashed = UserModel.hash_password(pwd)
    assert hashed != pwd
    assert UserModel.verify_password(pwd, hashed) is True
    assert UserModel.verify_password("WrongPassword!", hashed) is False

def test_jwt_token_generation_and_verification():
    user_doc = {
        "_id": "507f1f77bcf86cd799439011",
        "username": "teacher_sarah",
        "role": "teacher",
        "full_name": "Sarah Jenkins",
        "assigned_classes": ["Grade-10A"]
    }
    token = AuthService.generate_token(user_doc)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    payload = AuthService.verify_token(token)
    assert payload is not None
    assert payload["username"] == "teacher_sarah"
    assert payload["role"] == "teacher"
    assert payload["sub"] == "507f1f77bcf86cd799439011"

def test_tampered_token_rejection():
    user_doc = {
        "_id": "507f1f77bcf86cd799439011",
        "username": "teacher_sarah",
        "role": "teacher"
    }
    token = AuthService.generate_token(user_doc)
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tamperedSignatureHere123"
    assert AuthService.verify_token(tampered_token) is None
