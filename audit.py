from datetime import datetime, timezone
from models.database import get_db

class AuditLogModel:
    COLLECTION = "audit_logs"

    @classmethod
    def log_event(cls, actor_id: str, action: str, details: dict = None, reason: str = ""):
        db = get_db()
        entry = {
            "actor_id": actor_id,
            "action": action,
            "details": details or {},
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        db[cls.COLLECTION].insert_one(entry)
        return entry

    @classmethod
    def get_logs(cls, limit: int = 100):
        db = get_db()
        cursor = list(db[cls.COLLECTION].find().sort("timestamp", -1).limit(limit))
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return cursor
