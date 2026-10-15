import os
import sys

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.database import get_db
from models.user import UserModel
from models.student import StudentModel
from models.attendance import AttendanceModel

SAMPLE_STUDENTS = [
    {"full_name": "Aarav Sharma", "roll_number": 1, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Ananya Verma", "roll_number": 2, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Bhavya Patel", "roll_number": 3, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Charan Reddy", "roll_number": 4, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Divya Nair", "roll_number": 5, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Ethan Davis", "roll_number": 6, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Fatima Khan", "roll_number": 7, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Gaurav Gupta", "roll_number": 8, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Hina Joshi", "roll_number": 9, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Ishaan Malhotra", "roll_number": 10, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Jaya Iyer", "roll_number": 11, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Kavya Rao", "roll_number": 12, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Liam Wilson", "roll_number": 13, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Maya Sen", "roll_number": 14, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Nikhil Das", "roll_number": 15, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Omkar Muddada", "roll_number": 16, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Pooja Hegde", "roll_number": 17, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Rahul Bose", "roll_number": 18, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Sneha Roy", "roll_number": 19, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Tanvi Bhat", "roll_number": 20, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Varun Kapoor", "roll_number": 21, "class_id": "Grade-10A", "section": "A"},
    {"full_name": "Zoya Akhtar", "roll_number": 22, "class_id": "Grade-10A", "section": "A"},
]

def seed_database():
    print("Seeding AlphabetAI Attendance database...")
    db = get_db()

    # 1. Ensure Teacher & Admin
    if not UserModel.find_by_username("admin"):
        UserModel.create_user("admin", "AdminPassword123!", "System Administrator", "admin")
        print("  [+] Admin account created: admin / AdminPassword123!")

    if not UserModel.find_by_username("teacher"):
        UserModel.create_user("teacher", "TeacherPassword123!", "Prof. Sarah Jenkins", "teacher", ["Grade-10A", "Grade-10B"])
        print("  [+] Teacher account created: teacher / TeacherPassword123!")

    # 2. Seed Students
    seeded_students = 0
    for idx, s in enumerate(SAMPLE_STUDENTS, start=101):
        sid = f"STU-{idx}"
        existing = db.students.find_one({"student_id": sid})
        if not existing:
            StudentModel.register_student(
                student_id=sid,
                full_name=s["full_name"],
                roll_number=s["roll_number"],
                class_id=s["class_id"],
                section=s["section"],
                consent_status=True,
                contact_email=f"{s['full_name'].split()[0].lower()}@school.edu"
            )
            seeded_students += 1

    print(f"  [+] Seeded {seeded_students} students for Grade-10A (Roll 1-22, Names A-Z).")
    print("Seeding complete.")

if __name__ == "__main__":
    seed_database()
