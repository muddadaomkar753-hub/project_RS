import pytest
from models.database import get_db
from models.student import StudentModel
from models.attendance import AttendanceModel
from services.report_service import ReportService

@pytest.fixture(autouse=True)
def clean_db():
    db = get_db()
    db.students.delete_many({})
    db.attendance_sessions.delete_many({})
    db.attendance_records.delete_many({})
    yield
    db.students.delete_many({})
    db.attendance_sessions.delete_many({})
    db.attendance_records.delete_many({})

def test_attendance_percentage_and_session_report():
    # Register 4 students
    for i in range(1, 5):
        StudentModel.register_student(
            student_id=f"STU-0{i}",
            full_name=f"Student {i}",
            roll_number=i,
            class_id="Grade-10A",
            section="A"
        )

    session = AttendanceModel.create_session("Grade-10A", "A", "teacher_user")
    sess_id = session["_id"]

    # Mark 3 present, 1 absent
    for i in range(1, 4):
        AttendanceModel.record_attendance(
            session_id=sess_id,
            student_id=f"STU-0{i}",
            status="present",
            verification_method="ai_face_verification",
            verification_outcome="verified",
            recorded_by="teacher_user"
        )
    AttendanceModel.record_attendance(
        session_id=sess_id,
        student_id="STU-04",
        status="absent",
        verification_method="session_close_policy",
        verification_outcome="absent",
        recorded_by="teacher_user"
    )

    report = ReportService.get_session_report(sess_id)
    assert report["total_students"] == 4
    assert report["present_count"] == 3
    assert report["absent_count"] == 1
    # 3 / 4 = 75.0%
    assert report["attendance_percentage"] == 75.0

def test_csv_export_format():
    StudentModel.register_student(
        student_id="STU-100",
        full_name="Aarav Sharma",
        roll_number=1,
        class_id="Grade-10A",
        section="A"
    )
    session = AttendanceModel.create_session("Grade-10A", "A", "teacher_user")
    AttendanceModel.record_attendance(
        session_id=session["_id"],
        student_id="STU-100",
        status="present",
        verification_method="ai_face_verification",
        verification_outcome="verified",
        recorded_by="teacher_user"
    )

    csv_data = ReportService.generate_csv_report(session["_id"])
    assert "AlphabetAI Attendance - Official Session Report" in csv_data
    assert "Aarav Sharma" in csv_data
    assert "PRESENT" in csv_data
    assert "ai_face_verification" in csv_data
