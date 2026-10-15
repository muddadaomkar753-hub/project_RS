import pytest
from models.student import StudentModel

def test_name_normalization():
    # Leading/trailing whitespace
    assert StudentModel.normalize_name("  Aarav Sharma  ") == "aarav sharma"
    # Multiple internal spaces
    assert StudentModel.normalize_name("Bhavya    Patel") == "bhavya patel"
    # Mixed cases
    assert StudentModel.normalize_name("cHaRaN rEdDy") == "charan reddy"
    # Empty string
    assert StudentModel.normalize_name("") == ""

def test_alphabetical_sorting_order():
    # Test sort key function logic
    sample_students = [
        {"full_name": "Zoya Akhtar", "normalized_name": "zoya akhtar", "roll_number": 20},
        {"full_name": "  Aarav Sharma ", "normalized_name": "aarav sharma", "roll_number": 1},
        {"full_name": "Bhavya Patel", "normalized_name": "bhavya patel", "roll_number": 2},
        {"full_name": "aarav sharma", "normalized_name": "aarav sharma", "roll_number": 15}, # Same name, higher roll
        {"full_name": "Charan Reddy", "normalized_name": "charan reddy", "roll_number": 5},
    ]

    # Primary key: normalized_name, Secondary key: roll_number
    sorted_students = sorted(sample_students, key=lambda s: (s["normalized_name"], s["roll_number"]))

    names_and_rolls = [(s["normalized_name"], s["roll_number"]) for s in sorted_students]
    expected = [
        ("aarav sharma", 1),
        ("aarav sharma", 15), # Secondary sort ensures lower roll number first
        ("bhavya patel", 2),
        ("charan reddy", 5),
        ("zoya akhtar", 20)
    ]
    assert names_and_rolls == expected
