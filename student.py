import re
from datetime import datetime, timezone
from bson import ObjectId
from models.database import get_db

class StudentModel:
    COLLECTION = "students"

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalizes name for fair, case-insensitive, space-tolerant A-Z sorting."""
        if not name:
            return ""
        # Remove consecutive spaces and strip leading/trailing whitespace, convert to lowercase
        return re.sub(r"\s+", " ", name.strip()).lower()

    @classmethod
    def register_student(
        cls,
        student_id: str,
        full_name: str,
        roll_number: int,
        class_id: str,
        section: str,
        academic_year: str = "2025-2026",
        consent_status: bool = False,
        contact_email: str = "",
        contact_phone: str = "",
        guardian_name: str = ""
    ):
        db = get_db()
        student_id = student_id.strip()
        full_name = full_name.strip()
        class_id = class_id.strip()
        section = section.strip().upper()
        roll_number = int(roll_number)

        if not student_id or not full_name or not class_id or not section:
            raise ValueError("Student ID, Full Name, Class ID, and Section are mandatory fields.")

        # Check unique student_id
        if db[cls.COLLECTION].find_one({"student_id": student_id}):
            raise ValueError(f"Student with ID '{student_id}' is already registered.")

        # Check unique roll number within the same class and section
        if db[cls.COLLECTION].find_one({
            "class_id": class_id,
            "section": section,
            "roll_number": roll_number,
            "is_active": True
        }):
            raise ValueError(f"Roll number {roll_number} is already assigned in Class {class_id}-{section}.")

        student_doc = {
            "student_id": student_id,
            "full_name": full_name,
            "normalized_name": cls.normalize_name(full_name),
            "roll_number": roll_number,
            "class_id": class_id,
            "section": section,
            "academic_year": academic_year,
            "enrollment_status": "enrolled",
            "consent_status": bool(consent_status),
            "has_face_enrolled": False,
            "is_active": True,
            "contact_email": contact_email.strip(),
            "contact_phone": contact_phone.strip(),
            "guardian_name": guardian_name.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        result = db[cls.COLLECTION].insert_one(student_doc)
        student_doc["_id"] = str(result.inserted_id)
        return student_doc

    @classmethod
    def update_student(cls, student_id: str, updates: dict):
        db = get_db()
        existing = db[cls.COLLECTION].find_one({"student_id": student_id})
        if not existing:
            raise ValueError(f"Student with ID '{student_id}' does not exist.")

        allowed_fields = [
            "full_name", "roll_number", "class_id", "section",
            "academic_year", "consent_status", "contact_email",
            "contact_phone", "guardian_name", "is_active"
        ]
        sanitized = {}
        for k, v in updates.items():
            if k in allowed_fields:
                sanitized[k] = v

        if "full_name" in sanitized:
            sanitized["full_name"] = sanitized["full_name"].strip()
            sanitized["normalized_name"] = cls.normalize_name(sanitized["full_name"])

        if "roll_number" in sanitized:
            sanitized["roll_number"] = int(sanitized["roll_number"])
            target_class = sanitized.get("class_id", existing["class_id"])
            target_sec = sanitized.get("section", existing["section"])
            conflict = db[cls.COLLECTION].find_one({
                "student_id": {"$ne": student_id},
                "class_id": target_class,
                "section": target_sec,
                "roll_number": sanitized["roll_number"],
                "is_active": True
            })
            if conflict:
                raise ValueError(f"Roll number {sanitized['roll_number']} is already taken in {target_class}-{target_sec}.")

        sanitized["updated_at"] = datetime.now(timezone.utc).isoformat()
        db[cls.COLLECTION].update_one({"student_id": student_id}, {"$set": sanitized})
        return cls.get_by_student_id(student_id)

    @classmethod
    def deactivate_student(cls, student_id: str):
        """Soft-deactivates student without deleting historical attendance."""
        return cls.update_student(student_id, {"is_active": False})

    @classmethod
    def get_by_student_id(cls, student_id: str):
        db = get_db()
        doc = db[cls.COLLECTION].find_one({"student_id": student_id})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

    @classmethod
    def get_students(
        cls,
        class_id: str = None,
        section: str = None,
        search_query: str = None,
        sort_by: str = "alphabetical",
        include_inactive: bool = False
    ):
        db = get_db()
        query = {}
        if not include_inactive:
            query["is_active"] = True
        if class_id:
            query["class_id"] = class_id
        if section:
            query["section"] = section.upper()
        if search_query:
            regex = re.compile(re.escape(search_query.strip()), re.IGNORECASE)
            query["$or"] = [
                {"full_name": regex},
                {"student_id": regex}
            ]

        cursor = list(db[cls.COLLECTION].find(query))

        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        # Alphabetical sorting with roll_number as secondary key
        if sort_by == "alphabetical":
            # Primary: normalized_name, Secondary: roll_number
            cursor.sort(key=lambda s: (s.get("normalized_name", ""), s.get("roll_number", 0)))
        elif sort_by == "alphabetical_desc":
            cursor.sort(key=lambda s: (s.get("normalized_name", ""), s.get("roll_number", 0)), reverse=True)
        elif sort_by == "roll_number":
            cursor.sort(key=lambda s: (s.get("roll_number", 0), s.get("normalized_name", "")))

        return cursor
