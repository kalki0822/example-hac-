import os
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_root_landing_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["dataset_rows"] == 25000
    assert round(data["operating_threshold"], 4) == 0.2562

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_name"] == "LogisticRegression"

def test_v1_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] is True
    assert data["database"] is True

def test_model_metrics_endpoint():
    response = client.get("/model/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "LogisticRegression"
    assert "evaluation_metrics_oof" in data
    assert "roc_curve_points" in data
    assert data["dataset_rows"] == 25000

def test_predict_endpoint_valid_patient():
    valid_patient = {
        "age": "[70-80)",
        "time_in_hospital": 5,
        "n_procedures": 2,
        "n_lab_procedures": 45,
        "n_medications": 18,
        "n_outpatient": 1,
        "n_inpatient": 2,
        "n_emergency": 1,
        "medical_specialty": "InternalMedicine",
        "diag_1": "Circulatory",
        "diag_2": "Respiratory",
        "diag_3": "Diabetes",
        "glucose_test": "high",
        "A1Ctest": "high",
        "change": "yes",
        "diabetes_med": "yes"
    }
    response = client.post("/predict", json=valid_patient)
    assert response.status_code == 200
    data = response.json()
    assert "readmission_probability" in data
    assert 0.0 <= data["readmission_probability"] <= 1.0
    assert data["predicted_readmitted"] in ["yes", "no"]
    assert data["clinical_risk_tier"] in ["High Risk", "Moderate Risk", "Low Risk"]
    assert len(data["top_3_shap_drivers"]) == 3
    assert len(data["preventive_actions"]) > 0

def test_predict_endpoint_invalid_patient_missing_fields():
    invalid_patient = {
        "age": "[70-80)",
        "time_in_hospital": 5
    }
    response = client.post("/predict", json=invalid_patient)
    assert response.status_code == 422

def test_patients_pagination_page_1():
    response = client.get("/patients?page=1&page_size=15&source=KAGGLE")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] >= 25000
    assert data["page"] == 1
    assert data["page_size"] == 15
    assert len(data["patients"]) == 15
    
    first_pt = data["patients"][0]
    assert "readmitted" not in first_pt
    assert first_pt["patient_id"] is not None

def test_patients_pagination_page_2_and_uniqueness():
    response_p1 = client.get("/patients?page=1&page_size=15&source=KAGGLE")
    response_p2 = client.get("/patients?page=2&page_size=15&source=KAGGLE")
    
    assert response_p1.status_code == 200
    assert response_p2.status_code == 200
    
    p1_data = response_p1.json()
    p2_data = response_p2.json()
    
    assert p2_data["page"] == 2
    assert len(p2_data["patients"]) == 15
    
    # Verify page 1 and page 2 contain different patient records
    p1_ids = [pt["patient_id"] for pt in p1_data["patients"]]
    p2_ids = [pt["patient_id"] for pt in p2_data["patients"]]
    assert set(p1_ids).isdisjoint(set(p2_ids))

def test_patients_pagination_final_page():
    response = client.get("/patients?page=1667&page_size=15&source=KAGGLE")
    assert response.status_code == 200
    data = response.json()
    
    assert data["page"] == 1667
    assert len(data["patients"]) > 0

def test_end_to_end_patients_to_predict_batch():
    p_res = client.get("/patients?page=1&page_size=15")
    assert p_res.status_code == 200
    patients = p_res.json()["patients"]
    assert len(patients) == 15
    
    b_res = client.post("/predict_batch", json=patients)
    assert b_res.status_code == 200
    b_data = b_res.json()
    
    assert b_data["total_patients"] == 15
    assert len(b_data["predictions"]) == 15

def test_predict_batch_csv_upload_with_target_stripping():
    csv_content = """age,time_in_hospital,n_procedures,n_lab_procedures,n_medications,n_outpatient,n_inpatient,n_emergency,medical_specialty,diag_1,diag_2,diag_3,glucose_test,A1Ctest,change,diabetes_med,readmitted
[70-80),5,2,45,18,1,2,1,InternalMedicine,Circulatory,Respiratory,Diabetes,high,high,yes,yes,1
[40-50),2,1,20,5,0,0,0,Surgery,Digestive,Other,Other,no,no,no,no,0
"""
    files = {"file": ("batch_test.csv", csv_content.encode("utf-8"), "text/csv")}
    response = client.post("/predict_batch", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_patients"] == 2
    assert len(data["predictions"]) == 2
    assert data["high_risk_count"] + data["moderate_risk_count"] + data["low_risk_count"] == 2
