import pytest
import json
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["service"] == "AlphabetAI Attendance"
    assert "models" in data
    assert data["models"]["yunet_detection_ready"] is True
    assert data["models"]["sface_recognition_ready"] is True

def test_login_flow_and_authenticated_routes(client):
    # 1. Login with teacher
    login_res = client.post("/api/auth/login", json={
        "username": "teacher",
        "password": "TeacherPassword123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.get_json()
    assert login_data["success"] is True
    token = login_data["token"]
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Access /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.get_json()["user"]["username"] == "teacher"

    # 3. Access /api/students
    students_res = client.get("/api/students?class_id=Grade-10A", headers=headers)
    assert students_res.status_code == 200
    st_data = students_res.get_json()
    assert st_data["success"] is True
    assert st_data["count"] > 0

    # 4. Access /api/reports/dashboard
    dash_res = client.get("/api/reports/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.get_json()
    assert dash_data["success"] is True
    assert dash_data["stats"]["total_students"] > 0

def test_unauthenticated_request_rejected(client):
    res = client.get("/api/students")
    assert res.status_code == 401
    assert res.get_json()["success"] is False
