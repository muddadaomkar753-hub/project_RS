from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from models.database import get_db

class UserModel:
    COLLECTION = "users"

    @classmethod
    def hash_password(cls, password: str) -> str:
        return generate_password_hash(password, method="scrypt")

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password)

    @classmethod
    def create_user(cls, username: str, password: str, full_name: str, role: str = "teacher", assigned_classes: list = None):
        db = get_db()
        username = username.strip().lower()
        if db[cls.COLLECTION].find_one({"username": username}):
            raise ValueError(f"User '{username}' already exists.")

        user_doc = {
            "username": username,
            "password_hash": cls.hash_password(password),
            "full_name": full_name.strip(),
            "role": role if role in ["admin", "teacher"] else "teacher",
            "assigned_classes": assigned_classes or ["Grade-10A", "Grade-10B"],
            "account_status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        result = db[cls.COLLECTION].insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        return user_doc

    @classmethod
    def find_by_username(cls, username: str):
        db = get_db()
        doc = db[cls.COLLECTION].find_one({"username": username.strip().lower()})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    @classmethod
    def find_by_id(cls, user_id: str):
        db = get_db()
        try:
            oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            doc = db[cls.COLLECTION].find_one({"_id": oid})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception:
            return None

    @classmethod
    def to_safe_dict(cls, doc: dict) -> dict:
        if not doc:
            return None
        safe = dict(doc)
        safe.pop("password_hash", None)
        if "_id" in safe and isinstance(safe["_id"], ObjectId):
            safe["_id"] = str(safe["_id"])
        return safe
