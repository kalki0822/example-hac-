import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from src.data.load_data import load_raw_data

client = TestClient(app)

def get_valid_patient_payload():
    return {
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

def test_root_landing_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["model_name"] == "LogisticRegression"
    assert data["operating_threshold"] == pytest.approx(0.2562, abs=1e-3)
    assert data["cost_fn"] == 5.0
    assert data["cost_fp"] == 1.0
    assert data["dataset_rows"] == 25000
    assert data["model_path"] == "models/best_model.pkl"
    assert data["metadata_path"] == "models/model_metadata.json"
    assert data["shap_global_path"] == "reports/figures/shap_summary.png"
    assert data["features_count"] == 16
    assert "timestamp" in data
    assert data["message"] == "Vitals API is running successfully"

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "model_name" in data
    assert "operating_threshold" in data

def test_model_metrics_endpoint():
    response = client.get("/model/metrics")
    assert response.status_code == 200
    data = response.json()
    
    with open("models/model_metadata.json", "r") as f:
        expected_meta = json.load(f)
        
    assert data["model_name"] == expected_meta["model_name"]
    assert data["version"] == expected_meta["version"]
    assert data["dataset_rows"] == 25000
    assert data["optimal_threshold"] == pytest.approx(expected_meta["optimal_threshold"])
    assert data["evaluation_metrics_oof"]["roc_auc"] == pytest.approx(expected_meta["evaluation_metrics_oof"]["roc_auc"])

def test_patients_pagination_page_1():
    response = client.get("/patients?page=1&page_size=15")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 25000
    assert data["page"] == 1
    assert data["page_size"] == 15
    assert data["total_pages"] == 1667
    assert len(data["patients"]) == 15
    
    first_pt = data["patients"][0]
    assert "readmitted" not in first_pt
    assert first_pt["patient_id"] == "PT-10001"

def test_patients_pagination_page_2_and_uniqueness():
    response_p1 = client.get("/patients?page=1&page_size=15")
    response_p2 = client.get("/patients?page=2&page_size=15")
    
    assert response_p1.status_code == 200
    assert response_p2.status_code == 200
    
    p1_data = response_p1.json()
    p2_data = response_p2.json()
    
    assert p2_data["page"] == 2
    assert len(p2_data["patients"]) == 15
    assert p2_data["patients"][0]["patient_id"] == "PT-10016"
    
    # Verify page 1 and page 2 contain different patient records
    p1_ids = [pt["patient_id"] for pt in p1_data["patients"]]
    p2_ids = [pt["patient_id"] for pt in p2_data["patients"]]
    assert set(p1_ids).isdisjoint(set(p2_ids))

def test_patients_pagination_final_page():
    response = client.get("/patients?page=1667&page_size=15")
    assert response.status_code == 200
    data = response.json()
    
    assert data["page"] == 1667
    assert len(data["patients"]) == 10  # 25,000 % 15 = 10
    assert data["patients"][-1]["patient_id"] == "PT-35000"

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
    for pred in b_data["predictions"]:
        assert "readmission_probability" in pred
        assert "clinical_risk_tier" in pred
        assert "predicted_readmitted" in pred

def test_predict_endpoint_valid_patient():
    payload = get_valid_patient_payload()
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert 0.0 <= data["readmission_probability"] <= 1.0
    assert data["predicted_readmitted"] in ["yes", "no"]
    assert data["clinical_risk_tier"] in ["Low Risk", "Moderate Risk", "High Risk"]
    assert len(data["top_3_shap_drivers"]) == 3

def test_predict_endpoint_invalid_patient_missing_fields():
    payload = get_valid_patient_payload()
    del payload["time_in_hospital"]
    
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_predict_batch_csv_upload_with_target_stripping():
    raw_df = load_raw_data()
    sample_slice = raw_df.head(7).copy()
    assert "readmitted" in sample_slice.columns
    
    csv_bytes = sample_slice.to_csv(index=False).encode("utf-8")
    files = {"file": ("test_patients_with_target.csv", csv_bytes, "text/csv")}
    
    response = client.post("/predict_batch", files=files)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_patients"] == 7
    assert len(data["predictions"]) == 7
