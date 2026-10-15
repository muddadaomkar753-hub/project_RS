import json
import base64
from datetime import datetime, timezone
from models.database import get_db

class FaceEnrollmentModel:
    COLLECTION = "face_enrollments"
    MODEL_VERSION = "OpenCV-SFace-128D-v1"

    @classmethod
    def save_enrollment(
        cls,
        student_id: str,
        feature_vector: list,
        quality_score: float,
        blur_metric: float,
        brightness_metric: float,
        consent_signed: bool = True
    ):
        if not consent_signed:
            raise ValueError("Explicit biometric enrollment consent is mandatory before registering face data.")

        if not isinstance(feature_vector, list) or len(feature_vector) == 0:
            raise ValueError("Invalid biometric feature vector representation.")

        db = get_db()
        # Protect embedding vector by storing as serialized float array (never raw face photos)
        now_iso = datetime.now(timezone.utc).isoformat()
        doc = {
            "student_id": student_id,
            "feature_vector": [float(x) for x in feature_vector],
            "vector_dimension": len(feature_vector),
            "model_version": cls.MODEL_VERSION,
            "enrollment_timestamp": now_iso,
            "consent_status": True,
            "retention_policy": "academic_year_active",
            "enrollment_status": "enrolled",
            "quality_metrics": {
                "quality_score": round(quality_score, 4),
                "blur_metric": round(blur_metric, 2),
                "brightness_metric": round(brightness_metric, 2)
            },
            "updated_at": now_iso
        }

        db[cls.COLLECTION].update_one(
            {"student_id": student_id},
            {"$set": doc},
            upsert=True
        )

        # Also update student table flag
        db.students.update_one(
            {"student_id": student_id},
            {"$set": {"has_face_enrolled": True, "consent_status": True, "updated_at": now_iso}}
        )

        return cls.get_by_student_id(student_id, include_vector=False)

    @classmethod
    def get_by_student_id(cls, student_id: str, include_vector: bool = False):
        db = get_db()
        doc = db[cls.COLLECTION].find_one({"student_id": student_id, "enrollment_status": "enrolled"})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        if not include_vector:
            doc.pop("feature_vector", None)
        return doc

    @classmethod
    def revoke_enrollment(cls, student_id: str):
        """Privacy-compliant permanent deletion of biometric representation."""
        db = get_db()
        now_iso = datetime.now(timezone.utc).isoformat()
        db[cls.COLLECTION].delete_one({"student_id": student_id})
        db.students.update_one(
            {"student_id": student_id},
            {"$set": {"has_face_enrolled": False, "updated_at": now_iso}}
        )
        return True
