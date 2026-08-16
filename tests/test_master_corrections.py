import pytest
import hashlib
import os
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_model_artifact_hash():
    model_path = "models/best_model.pkl"
    assert os.path.exists(model_path), "Model artifact missing!"
    computed_hash = hashlib.sha256(open(model_path, "rb").read()).hexdigest().upper()
    expected_hash = "74BA9C6508BAD62F6378E35679E0BB8C693FDC7B2D33AD51C2C859FCBF9FB3C0"
    assert computed_hash == expected_hash, f"Model hash changed! Got {computed_hash}, expected {expected_hash}"

def test_dataset_hash():
    dataset_path = "data/raw/hospital_readmissions.csv"
    assert os.path.exists(dataset_path), "Raw dataset missing!"
    computed_hash = hashlib.sha256(open(dataset_path, "rb").read()).hexdigest().upper()
    expected_hash = "AC59A074708D90F9C0F80478E51D13D9E092085AE40FC35468CEB2C4016211B4"
    assert computed_hash == expected_hash, f"Dataset hash changed! Got {computed_hash}, expected {expected_hash}"

def test_kaggle_predictions_are_real_and_not_hardcoded_low():
    res = client.get("/api/v1/patients?page=1&page_size=15&source=KAGGLE&sort_by=RISK_DESC")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 25000
    assert data["high_risk_count"] > 0, "High Risk count should be > 0 for real Kaggle dataset"
    assert data["moderate_risk_count"] > 0, "Moderate Risk count should be > 0"
    
    first_pt = data["patients"][0]
    assert first_pt["readmission_probability"] >= 0.2562
    assert first_pt["clinical_risk_tier"] in ["High Risk", "Moderate Risk"]

def test_demo_records_removed():
    res = client.get("/api/v1/patients?page=1&page_size=15&source=ALL&search=DEMO")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0, "Zero demo records should be returned"

def test_manual_patient_intake_persistence_and_search():
    payload = {
        "patient_name": "Arun Kumar Test",
        "date_of_birth": "15/08/1954",
        "age": "[80-90)",
        "time_in_hospital": 8,
        "n_procedures": 3,
        "n_lab_procedures": 70,
        "n_medications": 25,
        "n_outpatient": 2,
        "n_inpatient": 4,
        "n_emergency": 3,
        "medical_specialty": "Cardiology",
        "diag_1": "Circulatory",
        "diag_2": "Respiratory",
        "diag_3": "Diabetes",
        "glucose_test": "high",
        "A1Ctest": "high",
        "change": "yes",
        "diabetes_med": "yes"
    }
    pred_res = client.post("/api/v1/predict", json=payload)
    assert pred_res.status_code == 200
    p_data = pred_res.json()
    assert p_data["patient_name"] == "Arun Kumar Test"
    assert p_data["date_of_birth"] == "15/08/1954"
    p_id = p_data["patient_id"]

    # Search for patient by Name globally
    search_res = client.get("/api/v1/patients?page=1&page_size=50&search=Arun%20Kumar%20Test")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] >= 1
    assert any(p["patient_id"] == p_id for p in search_data["patients"])

def test_global_sorting_and_pagination():
    res_desc = client.get("/api/v1/patients?page=1&page_size=15&sort_by=RISK_DESC")
    assert res_desc.status_code == 200
    data_desc = res_desc.json()
    p1 = data_desc["patients"][0]["readmission_probability"]
    p15 = data_desc["patients"][-1]["readmission_probability"]
    assert p1 >= p15

    res_asc = client.get("/api/v1/patients?page=1&page_size=15&sort_by=RISK_ASC")
    assert res_asc.status_code == 200
    data_asc = res_asc.json()
    p1_asc = data_asc["patients"][0]["readmission_probability"]
    assert p1_asc <= p1

def test_patient_specific_recommendations():
    high_cardiac = {
        "age": "[80-90)",
        "time_in_hospital": 8,
        "n_procedures": 3,
        "n_lab_procedures": 70,
        "n_medications": 25,
        "n_outpatient": 2,
        "n_inpatient": 4,
        "n_emergency": 3,
        "medical_specialty": "Cardiology",
        "diag_1": "Circulatory",
        "diag_2": "Respiratory",
        "diag_3": "Diabetes",
        "glucose_test": "high",
        "A1Ctest": "high",
        "change": "yes",
        "diabetes_med": "yes"
    }
    low_surgery = {
        "age": "[40-50)",
        "time_in_hospital": 1,
        "n_procedures": 0,
        "n_lab_procedures": 5,
        "n_medications": 2,
        "n_outpatient": 0,
        "n_inpatient": 0,
        "n_emergency": 0,
        "medical_specialty": "Surgery",
        "diag_1": "Other",
        "diag_2": "Other",
        "diag_3": "Other",
        "glucose_test": "no",
        "A1Ctest": "no",
        "change": "no",
        "diabetes_med": "no"
    }
    r1 = client.post("/api/v1/predict", json=high_cardiac).json()
    r2 = client.post("/api/v1/predict", json=low_surgery).json()

    rec1 = r1["preventive_actions"]
    rec2 = r2["preventive_actions"]

    assert rec1[0]["priority"] == "High"
    assert rec2[0]["priority"] in ["Routine", "Medium"]
    assert rec1[0]["title"] != rec2[0]["title"]
