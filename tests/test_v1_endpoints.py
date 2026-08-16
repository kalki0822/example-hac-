import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import init_db

client = TestClient(app)

def test_v1_live_check():
    res = client.get("/api/v1/live")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"

def test_v1_ready_check():
    res = client.get("/api/v1/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert res.json()["model_loaded"] is True

def test_v1_model_info():
    res = client.get("/api/v1/model/info")
    assert res.status_code == 200
    data = res.json()
    assert data["model_name"] == "LogisticRegression"
    assert data["version"] == "1.0.0"
    assert data["dataset_rows"] == 25000

def test_v1_dashboard_summary():
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_patients_dataset"] == 25000
    assert "active_users_count" in data

def test_v1_auth_flow():
    init_db()
    # Register demo clinician for test
    reg_payload = {
        "email": "doctor_test@vitals.health",
        "password": "Clinician123!",
        "full_name": "Dr. Test Clinician",
        "role": "CLINICIAN"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code in [200, 400]  # Created or already registered

    login_res = client.post("/api/v1/auth/login", json={"email": "doctor_test@vitals.health", "password": "Clinician123!"})
    assert login_res.status_code == 200
    tok = login_res.json()["access_token"]
    assert tok is not None

    headers = {"Authorization": f"Bearer {tok}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "doctor_test@vitals.health"
    assert me_res.json()["role"] == "CLINICIAN"
