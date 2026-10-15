import io
import csv
from datetime import datetime, timezone
from models.database import get_db
from models.student import StudentModel
from models.attendance import AttendanceModel

class ReportService:

    @classmethod
    def get_dashboard_stats(cls) -> dict:
        """
        Calculates authentic, real-time statistics from the database.
        Never fabricates numbers.
        """
        db = get_db()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        total_students = db.students.count_documents({"is_active": True})
        enrolled_faces = db.face_enrollments.count_documents({"enrollment_status": "enrolled"})
        total_sessions = db.attendance_sessions.count_documents({})
        active_sessions = db.attendance_sessions.count_documents({"status": "active"})

        # Today's records
        today_records = list(db.attendance_records.find({"session_date": today_str}))
        present_today = sum(1 for r in today_records if r.get("status") == "present")
        absent_today = sum(1 for r in today_records if r.get("status") == "absent")
        late_today = sum(1 for r in today_records if r.get("status") == "late")
        excused_today = sum(1 for r in today_records if r.get("status") == "excused")

        today_total_marked = len(today_records)
        attendance_pct = round((present_today / today_total_marked * 100), 1) if today_total_marked > 0 else 0.0

        # Recent attendance activity (latest 10 records)
        recent_records = list(db.attendance_records.find().sort("timestamp", -1).limit(10))
        student_ids = [r["student_id"] for r in recent_records]
        student_docs = {s["student_id"]: s for s in db.students.find({"student_id": {"$in": student_ids}})}

        activity_feed = []
        for r in recent_records:
            st = student_docs.get(r["student_id"], {})
            activity_feed.append({
                "record_id": str(r.get("_id")),
                "student_id": r["student_id"],
                "student_name": st.get("full_name", r["student_id"]),
                "roll_number": st.get("roll_number", "-"),
                "class_id": r.get("class_id", "-"),
                "section": r.get("section", "-"),
                "status": r.get("status"),
                "verification_method": r.get("verification_method"),
                "timestamp": r.get("timestamp")
            })

        return {
            "total_students": total_students,
            "enrolled_faces": enrolled_faces,
            "face_enrollment_rate": round((enrolled_faces / total_students * 100), 1) if total_students > 0 else 0.0,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "today_date": today_str,
            "present_today": present_today,
            "absent_today": absent_today,
            "late_today": late_today,
            "excused_today": excused_today,
            "today_total_marked": today_total_marked,
            "attendance_percentage_today": attendance_pct,
            "recent_activity": activity_feed
        }

    @classmethod
    def get_session_report(cls, session_id: str) -> dict:
        session = AttendanceModel.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        students = StudentModel.get_students(
            class_id=session["class_id"],
            section=session["section"],
            sort_by="alphabetical"
        )
        records = AttendanceModel.get_session_records(session_id)
        records_map = {r["student_id"]: r for r in records}

        rows = []
        present_count = 0
        absent_count = 0
        unmarked_count = 0

        for s in students:
            sid = s["student_id"]
            rec = records_map.get(sid)
            status = rec.get("status", "unmarked") if rec else "unmarked"

            if status == "present":
                present_count += 1
            elif status == "absent":
                absent_count += 1
            else:
                unmarked_count += 1

            rows.append({
                "student_id": sid,
                "full_name": s["full_name"],
                "roll_number": s["roll_number"],
                "status": status,
                "verification_method": rec.get("verification_method", "none") if rec else "-",
                "verification_outcome": rec.get("verification_outcome", "-") if rec else "-",
                "timestamp": rec.get("timestamp", "-") if rec else "-",
                "confidence_score": rec.get("confidence_score") if rec else None,
                "record_id": str(rec["_id"]) if rec and "_id" in rec else None,
                "correction_history": rec.get("correction_history", []) if rec else []
            })

        total = len(students)
        pct = round((present_count / total * 100), 1) if total > 0 else 0.0

        return {
            "session": session,
            "total_students": total,
            "present_count": present_count,
            "absent_count": absent_count,
            "unmarked_count": unmarked_count,
            "attendance_percentage": pct,
            "rows": rows
        }

    @classmethod
    def get_student_history(cls, student_id: str) -> dict:
        db = get_db()
        student = StudentModel.get_by_student_id(student_id)
        if not student:
            raise ValueError(f"Student '{student_id}' not found.")

        # Find all closed/completed or active sessions for this student's class
        sessions = list(db.attendance_sessions.find({
            "class_id": student["class_id"],
            "section": student["section"]
        }).sort("session_date", -1))
        sessions_map = {str(s["_id"]): s for s in sessions}

        records = list(db.attendance_records.find({"student_id": student_id}).sort("timestamp", -1))

        history = []
        present_count = 0
        absent_count = 0

        for r in records:
            status = r.get("status")
            if status == "present":
                present_count += 1
            elif status == "absent":
                absent_count += 1

            sess = sessions_map.get(r["session_id"], {})
            history.append({
                "session_id": r["session_id"],
                "session_date": r.get("session_date", sess.get("session_date", "-")),
                "session_name": sess.get("session_name", "Regular"),
                "status": status,
                "verification_method": r.get("verification_method"),
                "confidence_score": r.get("confidence_score"),
                "timestamp": r.get("timestamp"),
                "recorded_by": r.get("recorded_by"),
                "correction_history": r.get("correction_history", [])
            })

        total_sessions = len(sessions)
        eligible_sessions = len(history)
        pct = round((present_count / eligible_sessions * 100), 1) if eligible_sessions > 0 else 0.0

        return {
            "student": student,
            "total_class_sessions": total_sessions,
            "total_recorded_sessions": eligible_sessions,
            "present_count": present_count,
            "absent_count": absent_count,
            "attendance_percentage": pct,
            "history": history
        }

    @classmethod
    def generate_csv_report(cls, session_id: str) -> str:
        report_data = cls.get_session_report(session_id)
        session = report_data["session"]

        output = io.StringIO()
        writer = csv.writer(output)

        # Header metadata
        writer.writerow(["AlphabetAI Attendance - Official Session Report"])
        writer.writerow(["Class:", session.get("class_id"), "Section:", session.get("section")])
        writer.writerow(["Date:", session.get("session_date"), "Session:", session.get("session_name")])
        writer.writerow(["Total Students:", report_data["total_students"], "Present:", report_data["present_count"], "Percentage:", f"{report_data['attendance_percentage']}%"])
        writer.writerow([])

        # Table header
        writer.writerow(["Roll Number", "Student Name", "Student ID", "Status", "Verification Method", "Verification Outcome", "Recorded Timestamp"])

        for r in report_data["rows"]:
            writer.writerow([
                r["roll_number"],
                r["full_name"],
                r["student_id"],
                r["status"].upper(),
                r["verification_method"],
                r["verification_outcome"],
                r["timestamp"]
            ])

        return output.getvalue()
