from models.database import get_db
from models.student import StudentModel
from models.attendance import AttendanceModel

class AttendanceEngine:
    """
    Alphabetical Attendance Queue Engine.
    Coordinates A-Z student queue progression, verification status merging,
    skipped queue tracking, and progress statistics.
    """

    @classmethod
    def get_session_queue(
        cls,
        session_id: str,
        sort_by: str = "alphabetical",
        current_student_id: str = None,
        skipped_ids: list = None
    ) -> dict:
        session = AttendanceModel.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        # 1. Fetch all eligible active students in this class and section
        students = StudentModel.get_students(
            class_id=session["class_id"],
            section=session["section"],
            sort_by=sort_by,
            include_inactive=False
        )

        # 2. Fetch all recorded attendance for this session
        records = AttendanceModel.get_session_records(session_id)
        records_map = {r["student_id"]: r for r in records}

        # 3. Construct Queue items
        queue = []
        skipped_set = set(skipped_ids or [])
        verified_count = 0
        absent_count = 0
        uncertain_count = 0
        pending_list = []
        skipped_list = []

        for idx, s in enumerate(students):
            sid = s["student_id"]
            rec = records_map.get(sid)

            if rec:
                item_status = rec.get("status", "present")
                outcome = rec.get("verification_outcome", "")
                if item_status == "present":
                    verified_count += 1
                elif item_status == "absent":
                    absent_count += 1
            elif sid in skipped_set:
                item_status = "skipped"
                outcome = "temporarily_skipped"
                skipped_list.append(sid)
            else:
                item_status = "pending"
                outcome = "awaiting_verification"
                pending_list.append(sid)

            # Alphabetical letter tag (e.g. 'A' for Aarav, 'B' for Bhavya)
            letter = s.get("full_name", "?").strip()[:1].upper()

            queue.append({
                "index": idx + 1,
                "student_id": sid,
                "full_name": s["full_name"],
                "normalized_name": s.get("normalized_name", ""),
                "roll_number": s["roll_number"],
                "letter": letter,
                "has_face_enrolled": s.get("has_face_enrolled", False),
                "consent_status": s.get("consent_status", False),
                "status": item_status,
                "outcome": outcome,
                "record": rec,
                "is_skipped": sid in skipped_set
            })

        total = len(students)
        completed_count = verified_count + absent_count
        progress_pct = round((completed_count / total * 100), 1) if total > 0 else 0.0

        # Determine currently active student
        active_student = None
        if current_student_id:
            active_student = next((item for item in queue if item["student_id"] == current_student_id), None)

        if not active_student:
            # Auto-select the next pending student in A-Z order
            active_student = next((item for item in queue if item["status"] == "pending"), None)
            # If no pending left, check if any skipped remain
            if not active_student and skipped_list:
                active_student = next((item for item in queue if item["student_id"] == skipped_list[0]), None)

        return {
            "session": session,
            "sort_by": sort_by,
            "total_students": total,
            "verified_count": verified_count,
            "absent_count": absent_count,
            "pending_count": len(pending_list),
            "skipped_count": len(skipped_list),
            "progress_percentage": progress_pct,
            "current_student": active_student,
            "queue": queue,
            "pending_student_ids": pending_list,
            "skipped_student_ids": skipped_list
        }
