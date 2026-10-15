from datetime import datetime, timezone
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from models.database import get_db

class AttendanceModel:
    SESSIONS_COLL = "attendance_sessions"
    RECORDS_COLL = "attendance_records"

    # --- SESSIONS ---
    @classmethod
    def create_session(
        cls,
        class_id: str,
        section: str,
        created_by: str,
        session_date: str = None,
        session_name: str = "Regular Session",
        academic_year: str = "2025-2026"
    ):
        db = get_db()
        if not session_date:
            session_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        now_iso = datetime.now(timezone.utc).isoformat()
        session_doc = {
            "class_id": class_id.strip(),
            "section": section.strip().upper(),
            "session_date": session_date,
            "session_name": session_name.strip(),
            "academic_year": academic_year,
            "created_by": created_by,
            "status": "active",  # active, completed, cancelled
            "created_at": now_iso,
            "closed_at": None,
            "closing_policy": None
        }

        result = db[cls.SESSIONS_COLL].insert_one(session_doc)
        session_doc["_id"] = str(result.inserted_id)
        return session_doc

    @classmethod
    def get_session(cls, session_id: str):
        db = get_db()
        try:
            oid = ObjectId(session_id) if ObjectId.is_valid(session_id) else session_id
            doc = db[cls.SESSIONS_COLL].find_one({"_id": oid})
            if doc and "_id" in doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception:
            return None

    @classmethod
    def get_sessions(cls, class_id: str = None, section: str = None, session_date: str = None, status: str = None):
        db = get_db()
        query = {}
        if class_id:
            query["class_id"] = class_id
        if section:
            query["section"] = section.upper()
        if session_date:
            query["session_date"] = session_date
        if status:
            query["status"] = status

        cursor = list(db[cls.SESSIONS_COLL].find(query).sort("created_at", -1))
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return cursor

    @classmethod
    def close_session(cls, session_id: str, closed_by: str, closing_policy: str = "mark_unprocessed_absent"):
        """
        Closes an attendance session according to an explicit teacher-controlled closing policy.
        Optionally marks any unprocessed students in the class as 'absent'.
        """
        db = get_db()
        session = cls.get_session(session_id)
        if not session:
            raise ValueError("Attendance session not found.")
        if session.get("status") == "completed":
            raise ValueError("Attendance session is already completed.")

        now_iso = datetime.now(timezone.utc).isoformat()

        # If policy is to mark remaining eligible students as absent
        if closing_policy == "mark_unprocessed_absent":
            # Find all active students in this class/section
            eligible = list(db.students.find({
                "class_id": session["class_id"],
                "section": session["section"],
                "is_active": True
            }))
            # Find students who already have records in this session
            existing_recs = {
                r["student_id"] for r in db[cls.RECORDS_COLL].find({"session_id": session_id})
            }
            unprocessed = [s for s in eligible if s["student_id"] not in existing_recs]

            for s in unprocessed:
                rec_doc = {
                    "session_id": session_id,
                    "student_id": s["student_id"],
                    "class_id": session["class_id"],
                    "section": session["section"],
                    "status": "absent",
                    "timestamp": now_iso,
                    "verification_method": "session_close_policy",
                    "verification_outcome": "auto_absent_unprocessed",
                    "confidence_score": None,
                    "recorded_by": closed_by,
                    "correction_history": []
                }
                try:
                    db[cls.RECORDS_COLL].insert_one(rec_doc)
                except DuplicateKeyError:
                    pass

        oid = ObjectId(session_id) if ObjectId.is_valid(session_id) else session_id
        db[cls.SESSIONS_COLL].update_one(
            {"_id": oid},
            {"$set": {
                "status": "completed",
                "closed_at": now_iso,
                "closing_policy": closing_policy,
                "closed_by": closed_by
            }}
        )
        return cls.get_session(session_id)

    # --- RECORDS ---
    @classmethod
    def record_attendance(
        cls,
        session_id: str,
        student_id: str,
        status: str,
        verification_method: str,
        verification_outcome: str,
        recorded_by: str,
        confidence_score: float = None
    ):
        db = get_db()
        session = cls.get_session(session_id)
        if not session:
            raise ValueError("Invalid attendance session ID.")
        if session.get("status") != "active":
            raise ValueError(f"Session is {session.get('status')}; attendance submissions are only accepted for active sessions.")

        student = db.students.find_one({"student_id": student_id, "is_active": True})
        if not student:
            raise ValueError(f"Active student '{student_id}' not found.")

        if student["class_id"] != session["class_id"] or student["section"] != session["section"]:
            raise ValueError(f"Student '{student_id}' does not belong to session class {session['class_id']}-{session['section']}.")

        valid_statuses = ["present", "absent", "late", "excused"]
        if status.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")

        now_iso = datetime.now(timezone.utc).isoformat()
        record_doc = {
            "session_id": session_id,
            "student_id": student_id,
            "class_id": session["class_id"],
            "section": session["section"],
            "session_date": session["session_date"],
            "status": status.lower(),
            "timestamp": now_iso,
            "verification_method": verification_method,
            "verification_outcome": verification_outcome,
            "confidence_score": round(confidence_score, 4) if confidence_score is not None else None,
            "recorded_by": recorded_by,
            "correction_history": []
        }

        try:
            result = db[cls.RECORDS_COLL].insert_one(record_doc)
            record_doc["_id"] = str(result.inserted_id)
            return record_doc
        except DuplicateKeyError:
            raise ValueError(f"Attendance record already exists for student '{student_id}' in this session.")

    @classmethod
    def get_session_records(cls, session_id: str):
        db = get_db()
        cursor = list(db[cls.RECORDS_COLL].find({"session_id": session_id}))
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return cursor

    @classmethod
    def correct_attendance_record(
        cls,
        record_id: str,
        new_status: str,
        reason: str,
        corrected_by: str
    ):
        db = get_db()
        if not reason or not reason.strip():
            raise ValueError("A clear reason must be documented for any manual attendance correction.")

        valid_statuses = ["present", "absent", "late", "excused"]
        if new_status.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")

        oid = ObjectId(record_id) if ObjectId.is_valid(record_id) else record_id
        existing = db[cls.RECORDS_COLL].find_one({"_id": oid})
        if not existing:
            raise ValueError(f"Attendance record with ID '{record_id}' not found.")

        old_status = existing.get("status")
        now_iso = datetime.now(timezone.utc).isoformat()

        audit_entry = {
            "corrected_by": corrected_by,
            "old_status": old_status,
            "new_status": new_status.lower(),
            "reason": reason.strip(),
            "timestamp": now_iso
        }

        db[cls.RECORDS_COLL].update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": new_status.lower(),
                    "verification_outcome": f"corrected_by_teacher:{new_status.lower()}",
                    "updated_at": now_iso
                },
                "$push": {"correction_history": audit_entry}
            }
        )

        # Log into audit_logs
        db.audit_logs.insert_one({
            "actor_id": corrected_by,
            "action": "CORRECT_ATTENDANCE",
            "record_id": record_id,
            "student_id": existing.get("student_id"),
            "session_id": existing.get("session_id"),
            "old_status": old_status,
            "new_status": new_status.lower(),
            "reason": reason.strip(),
            "timestamp": now_iso
        })

        updated = db[cls.RECORDS_COLL].find_one({"_id": oid})
        if updated and "_id" in updated:
            updated["_id"] = str(updated["_id"])
        return updated
