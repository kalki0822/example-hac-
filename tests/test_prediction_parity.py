import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from api.main import app
from api.dependencies import ModelService
from src.features.build_features import build_canonical_model_features

client = TestClient(app)

# 5 Golden Patient Deterministic Test Records
GOLDEN_PATIENTS = [
    {
        "name": "Patient 1 - High Risk Cardiac",
        "uci_format": {
            "hospital_stay": 8, "num_procedures": 3, "num_lab_procedures": 70, "num_medications": 25,
            "number_outpatient": 2, "number_inpatient": 4, "number_emergency": 3,
            "specialty": "Cardiology", "diag_1": "414", "diag_2": "486", "diag_3": "250.00",
            "age": "85 years", "max_glu_serum": ">200", "A1Cresult": ">8", "change": "Ch", "diabetesMed": "Yes"
        },
        "kaggle_format": {
            "time_in_hospital": 8, "n_procedures": 3, "n_lab_procedures": 70, "n_medications": 25,
            "n_outpatient": 2, "n_inpatient": 4, "n_emergency": 3,
            "medical_specialty": "Cardiology", "diag_1": "Circulatory", "diag_2": "Respiratory", "diag_3": "Diabetes",
            "age": "[80-90)", "glucose_test": "high", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"
        },
        "manual_format": {
            "patient_name": "High Cardiac Patient", "date_of_birth": "12/04/1945",
            "time_in_hospital": "8", "n_procedures": "3", "n_lab_procedures": "70", "n_medications": "25",
            "n_outpatient": "2", "n_inpatient": "4", "n_emergency": "3",
            "medical_specialty": "cardiology", "diag_1": "circulatory", "diag_2": "respiratory", "diag_3": "diabetes",
            "age": "80-90", "glucose_test": "HIGH", "A1Ctest": "HIGH", "change": "YES", "diabetes_med": "YES"
        }
    },
    {
        "name": "Patient 2 - Low Risk Surgery",
        "uci_format": {
            "hospital_stay": 1, "num_procedures": 0, "num_lab_procedures": 10, "num_medications": 3,
            "number_outpatient": 0, "number_inpatient": 0, "number_emergency": 0,
            "specialty": "Surgery", "diag_1": "other", "diag_2": "other", "diag_3": "other",
            "age": "45 years", "max_glu_serum": "None", "A1Cresult": "None", "change": "No", "diabetesMed": "No"
        },
        "kaggle_format": {
            "time_in_hospital": 1, "n_procedures": 0, "n_lab_procedures": 10, "n_medications": 3,
            "n_outpatient": 0, "n_inpatient": 0, "n_emergency": 0,
            "medical_specialty": "Surgery", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other",
            "age": "[40-50)", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"
        },
        "manual_format": {
            "patient_name": "Low Surgery Patient", "date_of_birth": "05/11/1982",
            "time_in_hospital": "1", "n_procedures": "0", "n_lab_procedures": "10", "n_medications": "3",
            "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "0",
            "medical_specialty": "surgery", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other",
            "age": "40-50", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"
        }
    },
    {
        "name": "Patient 3 - Moderate Risk Internal Medicine",
        "uci_format": {
            "hospital_stay": 4, "num_procedures": 1, "num_lab_procedures": 40, "num_medications": 12,
            "number_outpatient": 1, "number_inpatient": 1, "number_emergency": 0,
            "specialty": "Internal Medicine", "diag_1": "250", "diag_2": "other", "diag_3": "other",
            "age": "65", "max_glu_serum": "norm", "A1Cresult": "norm", "change": "no", "diabetesMed": "yes"
        },
        "kaggle_format": {
            "time_in_hospital": 4, "n_procedures": 1, "n_lab_procedures": 40, "n_medications": 12,
            "n_outpatient": 1, "n_inpatient": 1, "n_emergency": 0,
            "medical_specialty": "InternalMedicine", "diag_1": "Diabetes", "diag_2": "Other", "diag_3": "Other",
            "age": "[60-70)", "glucose_test": "normal", "A1Ctest": "normal", "change": "no", "diabetes_med": "yes"
        },
        "manual_format": {
            "patient_name": "Moderate IntMed Patient", "date_of_birth": "20/06/1960",
            "time_in_hospital": "4", "n_procedures": "1", "n_lab_procedures": "40", "n_medications": "12",
            "n_outpatient": "1", "n_inpatient": "1", "n_emergency": "0",
            "medical_specialty": "InternalMedicine", "diag_1": "Diabetes", "diag_2": "Other", "diag_3": "Other",
            "age": "60-70", "glucose_test": "normal", "A1Ctest": "normal", "change": "no", "diabetes_med": "yes"
        }
    }
]

def test_feature_vector_parity():
    """Verifies that Kaggle, CSV, and Manual inputs produce 100% identical feature vectors and probabilities."""
    ms = ModelService()
    
    for gp in GOLDEN_PATIENTS:
        f_uci = build_canonical_model_features(gp["uci_format"])
        f_kaggle = build_canonical_model_features(gp["kaggle_format"])
        f_manual = build_canonical_model_features(gp["manual_format"])
        
        # Verify Feature Values Match 100%
        pd.testing.assert_frame_equal(f_uci, f_kaggle, check_dtype=False)
        pd.testing.assert_frame_equal(f_manual, f_kaggle, check_dtype=False)
        
        # Verify Model Probabilities Match Within 1e-6
        p_uci = float(ms.pipeline.predict_proba(f_uci)[0, 1])
        p_kaggle = float(ms.pipeline.predict_proba(f_kaggle)[0, 1])
        p_manual = float(ms.pipeline.predict_proba(f_manual)[0, 1])
        
        assert abs(p_uci - p_kaggle) < 1e-6, f"{gp['name']}: UCI vs Kaggle probability mismatch!"
        assert abs(p_manual - p_kaggle) < 1e-6, f"{gp['name']}: Manual vs Kaggle probability mismatch!"
        
        # Verify Risk Tier Mappings Match 100%
        t_uci = ms.assign_risk_tier(p_uci)
        t_kaggle = ms.assign_risk_tier(p_kaggle)
        t_manual = ms.assign_risk_tier(p_manual)
        
        assert t_uci == t_kaggle == t_manual, f"{gp['name']}: Risk tier mismatch ({t_uci} vs {t_kaggle} vs {t_manual})"

def test_api_endpoint_parity():
    """Verifies that /api/v1/predict (manual) and /api/v1/predict_batch (CSV) return identical probabilities."""
    for gp in GOLDEN_PATIENTS:
        # 1. Manual Endpoint POST /api/v1/predict
        res_man = client.post("/api/v1/predict", json=gp["manual_format"])
        assert res_man.status_code == 200
        man_data = res_man.json()
        
        # 2. CSV Batch Endpoint POST /api/v1/predict_batch
        res_batch = client.post("/api/v1/predict_batch", json={"patients": [gp["kaggle_format"]]})
        assert res_batch.status_code == 200
        batch_data = res_batch.json()["predictions"][0]
        
        # Compare Probabilities & Risk Tiers
        man_prob = man_data["readmission_probability"]
        batch_prob = batch_data["readmission_probability"]
        
        assert abs(man_prob - batch_prob) < 1e-4, f"API probability mismatch for {gp['name']}: {man_prob} vs {batch_prob}"
        assert man_data["clinical_risk_tier"] == batch_data["clinical_risk_tier"], f"API risk tier mismatch for {gp['name']}"

def test_vitals_pipeline_test_20_csv_vs_manual():
    """Golden consistency test: verifies vitals_pipeline_test_20.csv yields identical probability via CSV and Manual intake."""
    import os
    csv_path = "data/vitals_pipeline_test_20.csv"
    assert os.path.exists(csv_path), "data/vitals_pipeline_test_20.csv does not exist"
    
    df = pd.read_csv(csv_path)
    assert len(df) == 20
    
    # 1. Process row 0 via CSV upload endpoint
    with open(csv_path, "rb") as f:
        files = {"file": ("vitals_pipeline_test_20.csv", f.read(), "text/csv")}
    res_csv = client.post("/api/v1/predict_batch", files=files)
    assert res_csv.status_code == 200
    csv_prob = res_csv.json()["predictions"][0]["readmission_probability"]
    csv_tier = res_csv.json()["predictions"][0]["clinical_risk_tier"]
    
    # 2. Process row 0 via Manual Intake payload
    row0 = df.iloc[0].to_dict()
    manual_payload = {
        "patient_name": "Pipeline Test Patient 0",
        "date_of_birth": "01/01/1955",
        "age": str(row0.get("age")),
        "time_in_hospital": int(row0.get("time_in_hospital")),
        "n_procedures": int(row0.get("n_procedures")),
        "n_lab_procedures": int(row0.get("n_lab_procedures")),
        "n_medications": int(row0.get("n_medications")),
        "n_outpatient": int(row0.get("n_outpatient")),
        "n_inpatient": int(row0.get("n_inpatient")),
        "n_emergency": int(row0.get("n_emergency")),
        "medical_specialty": str(row0.get("medical_specialty")),
        "diag_1": str(row0.get("diag_1")),
        "diag_2": str(row0.get("diag_2")),
        "diag_3": str(row0.get("diag_3")),
        "glucose_test": str(row0.get("glucose_test")),
        "A1Ctest": str(row0.get("A1Ctest")),
        "change": str(row0.get("change")),
        "diabetes_med": str(row0.get("diabetes_med"))
    }
    res_man = client.post("/api/v1/predict", json=manual_payload)
    assert res_man.status_code == 200
    man_prob = res_man.json()["readmission_probability"]
    man_tier = res_man.json()["clinical_risk_tier"]
    
    assert abs(csv_prob - man_prob) < 1e-4, f"vitals_pipeline_test_20 probability disparity: CSV={csv_prob} vs Manual={man_prob}"
    assert csv_tier == man_tier, f"vitals_pipeline_test_20 risk tier disparity: CSV={csv_tier} vs Manual={man_tier}"

