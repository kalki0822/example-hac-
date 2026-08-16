import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.recommendations import generate_preventive_actions
from api.main import app

client = TestClient(app)

def test_generate_preventive_actions_high_risk():
    patient_data = {
        "age": "[80-90)",
        "time_in_hospital": 7,
        "n_inpatient": 3,
        "n_emergency": 2,
        "n_outpatient": 1,
        "n_medications": 20,
        "diag_1": "Circulatory",
        "diag_2": "Diabetes",
        "diag_3": "Other",
        "diabetes_med": "yes",
        "change": "yes"
    }
    actions = generate_preventive_actions(patient_data, risk_tier="High Risk")
    
    assert isinstance(actions, list)
    assert 2 <= len(actions) <= 4
    for act in actions:
        assert act["priority"] == "High"
        assert "title" in act
        assert "reason" in act

def test_generate_preventive_actions_high_utilization_trigger():
    patient_data = {
        "n_inpatient": 2,
        "n_emergency": 1,
        "n_medications": 5,
        "time_in_hospital": 2,
        "age": "[40-50)"
    }
    actions = generate_preventive_actions(patient_data, risk_tier="Moderate Risk")
    assert any("early post-discharge follow-up" in a["title"].lower() for a in actions)

def test_generate_preventive_actions_high_medication_trigger():
    patient_data = {
        "n_medications": 18,
        "n_inpatient": 0,
        "n_emergency": 0,
        "time_in_hospital": 2,
        "age": "[50-60)"
    }
    actions = generate_preventive_actions(patient_data, risk_tier="Moderate Risk")
    assert any("medication reconciliation" in a["title"].lower() for a in actions)

def test_generate_preventive_actions_older_age_trigger():
    patient_data = {
        "age": "[80-90)",
        "n_medications": 5,
        "n_inpatient": 0,
        "n_emergency": 0,
        "time_in_hospital": 2
    }
    actions = generate_preventive_actions(patient_data, risk_tier="Moderate Risk")
    assert any("clinical monitoring" in a["title"].lower() or "age" in a["reason"].lower() for a in actions)

def test_generate_preventive_actions_low_risk():
    patient_data = {
        "age": "[40-50)",
        "n_inpatient": 0,
        "n_emergency": 0,
        "n_outpatient": 0,
        "n_medications": 4,
        "time_in_hospital": 1
    }
    actions = generate_preventive_actions(patient_data, risk_tier="Low Risk")
    assert len(actions) == 1
    assert actions[0]["priority"] == "Routine"
    assert "Low Risk" in actions[0]["reason"]

def test_api_predict_includes_preventive_actions():
    payload = {
        "age": "[70-80)",
        "time_in_hospital": 6,
        "n_procedures": 2,
        "n_lab_procedures": 55,
        "n_medications": 22,
        "n_outpatient": 1,
        "n_inpatient": 3,
        "n_emergency": 2,
        "medical_specialty": "InternalMedicine",
        "diag_1": "Circulatory",
        "diag_2": "Respiratory",
        "diag_3": "Diabetes",
        "glucose_test": "high",
        "A1Ctest": "high",
        "change": "yes",
        "diabetes_med": "yes"
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "preventive_actions" in data
    assert len(data["preventive_actions"]) > 0
    for act in data["preventive_actions"]:
        assert "title" in act
        assert "reason" in act
        assert act["priority"] in ["High", "Medium", "Routine"]

def test_api_predict_batch_includes_preventive_actions_per_patient():
    p1 = {
        "age": "[80-90)", "time_in_hospital": 8, "n_procedures": 3, "n_lab_procedures": 70,
        "n_medications": 25, "n_outpatient": 2, "n_inpatient": 4, "n_emergency": 3,
        "medical_specialty": "Cardiology", "diag_1": "Circulatory", "diag_2": "Respiratory",
        "diag_3": "Diabetes", "glucose_test": "high", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"
    }
    p2 = {
        "age": "[40-50)", "time_in_hospital": 2, "n_procedures": 1, "n_lab_procedures": 20,
        "n_medications": 4, "n_outpatient": 0, "n_inpatient": 0, "n_emergency": 0,
        "medical_specialty": "Surgery", "diag_1": "Digestive", "diag_2": "Other",
        "diag_3": "Other", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"
    }
    response = client.post("/predict_batch", json=[p1, p2])
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_patients"] == 2
    for pred in data["predictions"]:
        assert "preventive_actions" in pred
        assert isinstance(pred["preventive_actions"], list)
        assert len(pred["preventive_actions"]) > 0
    
    # Confirm recommendations differ between high risk (p1) and low risk (p2)
    p1_actions = data["predictions"][0]["preventive_actions"]
    p2_actions = data["predictions"][1]["preventive_actions"]
    assert p1_actions[0]["priority"] != p2_actions[0]["priority"]
