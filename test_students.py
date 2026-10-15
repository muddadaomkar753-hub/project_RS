import pytest
from models.database import get_db
from models.student import StudentModel

@pytest.fixture(autouse=True)
def clean_db():
    db = get_db()
    db.students.delete_many({})
    yield
    db.students.delete_many({})

def test_register_student_success():
    student = StudentModel.register_student(
        student_id="STU-001",
        full_name="Aarav Sharma",
        roll_number=1,
        class_id="Grade-10A",
        section="A",
        consent_status=True
    )
    assert student["student_id"] == "STU-001"
    assert student["normalized_name"] == "aarav sharma"
    assert student["roll_number"] == 1
    assert student["is_active"] is True

def test_duplicate_student_id_rejection():
    StudentModel.register_student(
        student_id="STU-001",
        full_name="Aarav Sharma",
        roll_number=1,
        class_id="Grade-10A",
        section="A"
    )
    with pytest.raises(ValueError, match="already registered"):
        StudentModel.register_student(
            student_id="STU-001",
            full_name="Another Student",
            roll_number=2,
            class_id="Grade-10A",
            section="A"
        )

def test_duplicate_roll_number_in_same_class_rejection():
    StudentModel.register_student(
        student_id="STU-001",
        full_name="Aarav Sharma",
        roll_number=1,
        class_id="Grade-10A",
        section="A"
    )
    with pytest.raises(ValueError, match="already assigned"):
        StudentModel.register_student(
            student_id="STU-002",
            full_name="Bhavya Patel",
            roll_number=1, # Conflict!
            class_id="Grade-10A",
            section="A"
        )

def test_deactivate_student_preserves_record():
    StudentModel.register_student(
        student_id="STU-003",
        full_name="Charan Reddy",
        roll_number=3,
        class_id="Grade-10A",
        section="A"
    )
    StudentModel.deactivate_student("STU-003")
    
    # Excluded from active student list
    active_students = StudentModel.get_students(class_id="Grade-10A", include_inactive=False)
    assert not any(s["student_id"] == "STU-003" for s in active_students)

    # Exists in database with is_active: False
    stored = StudentModel.get_by_student_id("STU-003")
    assert stored is not None
    assert stored["is_active"] is False
