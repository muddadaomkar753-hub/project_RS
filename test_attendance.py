import pytest
from models.database import get_db
from models.student import StudentModel
from models.attendance import AttendanceModel

@pytest.fixture(autouse=True)
def clean_db():
    db = get_db()
    db.students.delete_many({})
    db.attendance_sessions.delete_many({})
    db.attendance_records.delete_many({})
    db.audit_logs.delete_many({})
    yield
    db.students.delete_many({})
    db.attendance_sessions.delete_many({})
    db.attendance_records.delete_many({})
    db.audit_logs.delete_many({})

def test_atomic_duplicate_attendance_prevention():
    StudentModel.register_student(
        student_id="STU-010",
        full_name="Aarav Sharma",
        roll_number=1,
        class_id="Grade-10A",
        section="A"
    )
    session = AttendanceModel.create_session("Grade-10A", "A", "teacher_user")
    sess_id = session["_id"]

    # First attendance record
    rec1 = AttendanceModel.record_attendance(
        session_id=sess_id,
        student_id="STU-010",
        status="present",
        verification_method="ai_face_verification",
        verification_outcome="verified",
        recorded_by="teacher_user",
        confidence_score=0.91
    )
    assert rec1["status"] == "present"

    # Second attendance record for same session & student MUST raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        AttendanceModel.record_attendance(
            session_id=sess_id,
            student_id="STU-010",
            status="present",
            verification_method="ai_face_verification",
            verification_outcome="duplicate_test",
            recorded_by="teacher_user"
        )

def test_attendance_correction_with_audit_trail():
    StudentModel.register_student(
        student_id="STU-011",
        full_name="Bhavya Patel",
        roll_number=2,
        class_id="Grade-10A",
        section="A"
    )
    session = AttendanceModel.create_session("Grade-10A", "A", "teacher_user")
    rec = AttendanceModel.record_attendance(
        session_id=session["_id"],
        student_id="STU-011",
        status="absent",
        verification_method="teacher_manual_override",
        verification_outcome="manual_absent",
        recorded_by="teacher_user"
    )

    # Correct record to "present" with mandatory documented reason
    updated = AttendanceModel.correct_attendance_record(
        record_id=rec["_id"],
        new_status="present",
        reason="Student arrived with signed clinic pass",
        corrected_by="teacher_user"
    )
    assert updated["status"] == "present"
    assert len(updated["correction_history"]) == 1
    assert updated["correction_history"][0]["old_status"] == "absent"
    assert updated["correction_history"][0]["new_status"] == "present"
    assert updated["correction_history"][0]["reason"] == "Student arrived with signed clinic pass"

def test_close_session_policy():
    StudentModel.register_student(
        student_id="STU-012",
        full_name="Charan Reddy",
        roll_number=3,
        class_id="Grade-10A",
        section="A"
    )
    StudentModel.register_student(
        student_id="STU-013",
        full_name="Divya Nair",
        roll_number=4,
        class_id="Grade-10A",
        section="A"
    )
    session = AttendanceModel.create_session("Grade-10A", "A", "teacher_user")

    # Mark Charan present, leave Divya unprocessed
    AttendanceModel.record_attendance(
        session_id=session["_id"],
        student_id="STU-012",
        status="present",
        verification_method="ai_face_verification",
        verification_outcome="verified",
        recorded_by="teacher_user"
    )

    # Close session with standard policy: mark unprocessed as absent
    closed = AttendanceModel.close_session(session["_id"], "teacher_user", "mark_unprocessed_absent")
    assert closed["status"] == "completed"

    records = AttendanceModel.get_session_records(session["_id"])
    rec_map = {r["student_id"]: r["status"] for r in records}
    assert rec_map["STU-012"] == "present"
    assert rec_map["STU-013"] == "absent"  # Divya automatically marked absent by explicit policy
