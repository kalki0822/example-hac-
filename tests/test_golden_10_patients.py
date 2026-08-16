import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from api.main import app
from api.dependencies import ModelService
from src.features.build_features import build_canonical_model_features

client = TestClient(app)

# 10 Golden Patient Profiles
GOLDEN_10_PATIENTS = [
    {
        "id": 1,
        "name": "Patient 1 - High Risk Cardiac",
        "kaggle": {"time_in_hospital": 8, "n_procedures": 3, "n_lab_procedures": 70, "n_medications": 25, "n_outpatient": 2, "n_inpatient": 4, "n_emergency": 3, "medical_specialty": "Cardiology", "diag_1": "Circulatory", "diag_2": "Respiratory", "diag_3": "Diabetes", "age": "[80-90)", "glucose_test": "high", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"},
        "csv": {"time_in_hospital": "8", "n_procedures": "3", "n_lab_procedures": "70", "n_medications": "25", "n_outpatient": "2", "n_inpatient": "4", "n_emergency": "3", "medical_specialty": "cardiology", "diag_1": "circulatory", "diag_2": "respiratory", "diag_3": "diabetes", "age": "80-90", "glucose_test": "HIGH", "A1Ctest": "HIGH", "change": "YES", "diabetes_med": "YES"},
        "manual": {"patient_name": "High Cardiac", "date_of_birth": "01/01/1940", "time_in_hospital": "8", "n_procedures": "3", "n_lab_procedures": "70", "n_medications": "25", "n_outpatient": "2", "n_inpatient": "4", "n_emergency": "3", "medical_specialty": "cardiology", "diag_1": "circulatory", "diag_2": "respiratory", "diag_3": "diabetes", "age": "80-90", "glucose_test": "HIGH", "A1Ctest": "HIGH", "change": "YES", "diabetes_med": "YES"}
    },
    {
        "id": 2,
        "name": "Patient 2 - Low Risk Surgery",
        "kaggle": {"time_in_hospital": 1, "n_procedures": 0, "n_lab_procedures": 10, "n_medications": 3, "n_outpatient": 0, "n_inpatient": 0, "n_emergency": 0, "medical_specialty": "Surgery", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other", "age": "[40-50)", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "csv": {"time_in_hospital": "1", "n_procedures": "0", "n_lab_procedures": "10", "n_medications": "3", "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "0", "medical_specialty": "surgery", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other", "age": "40-50", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "manual": {"patient_name": "Low Surgery", "date_of_birth": "05/11/1982", "time_in_hospital": "1", "n_procedures": "0", "n_lab_procedures": "10", "n_medications": "3", "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "0", "medical_specialty": "surgery", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other", "age": "40-50", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"}
    },
    {
        "id": 3,
        "name": "Patient 3 - Moderate Risk Internal Medicine",
        "kaggle": {"time_in_hospital": 4, "n_procedures": 1, "n_lab_procedures": 40, "n_medications": 12, "n_outpatient": 1, "n_inpatient": 1, "n_emergency": 0, "medical_specialty": "InternalMedicine", "diag_1": "Diabetes", "diag_2": "Other", "diag_3": "Other", "age": "[60-70)", "glucose_test": "normal", "A1Ctest": "normal", "change": "no", "diabetes_med": "yes"},
        "csv": {"time_in_hospital": "4", "n_procedures": "1", "n_lab_procedures": "40", "n_medications": "12", "n_outpatient": "1", "n_inpatient": "1", "n_emergency": "0", "medical_specialty": "InternalMedicine", "diag_1": "Diabetes", "diag_2": "Other", "diag_3": "Other", "age": "60-70", "glucose_test": "normal", "A1Ctest": "normal", "change": "no", "diabetes_med": "yes"},
        "manual": {"patient_name": "Moderate IntMed", "date_of_birth": "20/06/1960", "time_in_hospital": "4", "n_procedures": "1", "n_lab_procedures": "40", "n_medications": "12", "n_outpatient": "1", "n_inpatient": "1", "n_emergency": "0", "medical_specialty": "InternalMedicine", "diag_1": "Diabetes", "diag_2": "Other", "diag_3": "Other", "age": "60-70", "glucose_test": "normal", "A1Ctest": "normal", "change": "no", "diabetes_med": "yes"}
    },
    {
        "id": 4,
        "name": "Patient 4 - Emergency Trauma High Utilization",
        "kaggle": {"time_in_hospital": 10, "n_procedures": 4, "n_lab_procedures": 85, "n_medications": 30, "n_outpatient": 3, "n_inpatient": 5, "n_emergency": 6, "medical_specialty": "Emergency/Trauma", "diag_1": "Injury", "diag_2": "Circulatory", "diag_3": "Other", "age": "[70-80)", "glucose_test": "high", "A1Ctest": "normal", "change": "yes", "diabetes_med": "yes"},
        "csv": {"time_in_hospital": "10", "n_procedures": "4", "n_lab_procedures": "85", "n_medications": "30", "n_outpatient": "3", "n_inpatient": "5", "n_emergency": "6", "medical_specialty": "Emergency/Trauma", "diag_1": "Injury", "diag_2": "Circulatory", "diag_3": "Other", "age": "70-80", "glucose_test": "high", "A1Ctest": "normal", "change": "yes", "diabetes_med": "yes"},
        "manual": {"patient_name": "Emerg Trauma", "date_of_birth": "15/03/1950", "time_in_hospital": "10", "n_procedures": "4", "n_lab_procedures": "85", "n_medications": "30", "n_outpatient": "3", "n_inpatient": "5", "n_emergency": "6", "medical_specialty": "Emergency/Trauma", "diag_1": "Injury", "diag_2": "Circulatory", "diag_3": "Other", "age": "70-80", "glucose_test": "high", "A1Ctest": "normal", "change": "yes", "diabetes_med": "yes"}
    },
    {
        "id": 5,
        "name": "Patient 5 - Young Low Utilization Respiratory",
        "kaggle": {"time_in_hospital": 2, "n_procedures": 0, "n_lab_procedures": 25, "n_medications": 5, "n_outpatient": 0, "n_inpatient": 0, "n_emergency": 1, "medical_specialty": "Family/GeneralPractice", "diag_1": "Respiratory", "diag_2": "Other", "diag_3": "Other", "age": "[30-40)", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "csv": {"time_in_hospital": "2", "n_procedures": "0", "n_lab_procedures": "25", "n_medications": "5", "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "1", "medical_specialty": "Family/GeneralPractice", "diag_1": "Respiratory", "diag_2": "Other", "diag_3": "Other", "age": "30-40", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "manual": {"patient_name": "Young Resp", "date_of_birth": "10/08/1990", "time_in_hospital": "2", "n_procedures": "0", "n_lab_procedures": "25", "n_medications": "5", "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "1", "medical_specialty": "Family/GeneralPractice", "diag_1": "Respiratory", "diag_2": "Other", "diag_3": "Other", "age": "30-40", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"}
    },
    {
        "id": 6,
        "name": "Patient 6 - Geriatric Complex Digestive",
        "kaggle": {"time_in_hospital": 12, "n_procedures": 2, "n_lab_procedures": 60, "n_medications": 22, "n_outpatient": 1, "n_inpatient": 3, "n_emergency": 2, "medical_specialty": "InternalMedicine", "diag_1": "Digestive", "diag_2": "Diabetes", "diag_3": "Circulatory", "age": "[90-100)", "glucose_test": "normal", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"},
        "csv": {"time_in_hospital": "12", "n_procedures": "2", "n_lab_procedures": "60", "n_medications": "22", "n_outpatient": "1", "n_inpatient": "3", "n_emergency": "2", "medical_specialty": "InternalMedicine", "diag_1": "Digestive", "diag_2": "Diabetes", "diag_3": "Circulatory", "age": "90-100", "glucose_test": "normal", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"},
        "manual": {"patient_name": "Geriatric Dig", "date_of_birth": "01/01/1930", "time_in_hospital": "12", "n_procedures": "2", "n_lab_procedures": "60", "n_medications": "22", "n_outpatient": "1", "n_inpatient": "3", "n_emergency": "2", "medical_specialty": "InternalMedicine", "diag_1": "Digestive", "diag_2": "Diabetes", "diag_3": "Circulatory", "age": "90-100", "glucose_test": "normal", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"}
    },
    {
        "id": 7,
        "name": "Patient 7 - Nephrology High Inpatient",
        "kaggle": {"time_in_hospital": 7, "n_procedures": 1, "n_lab_procedures": 50, "n_medications": 18, "n_outpatient": 4, "n_inpatient": 6, "n_emergency": 0, "medical_specialty": "Nephrology", "diag_1": "Circulatory", "diag_2": "Diabetes", "diag_3": "Other", "age": "[60-70)", "glucose_test": "high", "A1Ctest": "no", "change": "no", "diabetes_med": "yes"},
        "csv": {"time_in_hospital": "7", "n_procedures": "1", "n_lab_procedures": "50", "n_medications": "18", "n_outpatient": "4", "n_inpatient": "6", "n_emergency": "0", "medical_specialty": "Nephrology", "diag_1": "Circulatory", "diag_2": "Diabetes", "diag_3": "Other", "age": "60-70", "glucose_test": "high", "A1Ctest": "no", "change": "no", "diabetes_med": "yes"},
        "manual": {"patient_name": "Nephrology Pt", "date_of_birth": "14/02/1962", "time_in_hospital": "7", "n_procedures": "1", "n_lab_procedures": "50", "n_medications": "18", "n_outpatient": "4", "n_inpatient": "6", "n_emergency": "0", "medical_specialty": "Nephrology", "diag_1": "Circulatory", "diag_2": "Diabetes", "diag_3": "Other", "age": "60-70", "glucose_test": "high", "A1Ctest": "no", "change": "no", "diabetes_med": "yes"}
    },
    {
        "id": 8,
        "name": "Patient 8 - Missing Specialty Fallback",
        "kaggle": {"time_in_hospital": 3, "n_procedures": 0, "n_lab_procedures": 30, "n_medications": 8, "n_outpatient": 0, "n_inpatient": 1, "n_emergency": 0, "medical_specialty": "Missing", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other", "age": "[50-60)", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "csv": {"time_in_hospital": "3", "n_procedures": "0", "n_lab_procedures": "30", "n_medications": "8", "n_outpatient": "0", "n_inpatient": "1", "n_emergency": "0", "medical_specialty": "Missing", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other", "age": "50-60", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "manual": {"patient_name": "Missing Spec", "date_of_birth": "30/09/1972", "time_in_hospital": "3", "n_procedures": "0", "n_lab_procedures": "30", "n_medications": "8", "n_outpatient": "0", "n_inpatient": "1", "n_emergency": "0", "medical_specialty": "Missing", "diag_1": "Other", "diag_2": "Other", "diag_3": "Other", "age": "50-60", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"}
    },
    {
        "id": 9,
        "name": "Patient 9 - Musculoskeletal Surgery Low Risk",
        "kaggle": {"time_in_hospital": 2, "n_procedures": 2, "n_lab_procedures": 15, "n_medications": 6, "n_outpatient": 0, "n_inpatient": 0, "n_emergency": 0, "medical_specialty": "Surgery", "diag_1": "Musculoskeletal", "diag_2": "Other", "diag_3": "Other", "age": "[50-60)", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "csv": {"time_in_hospital": "2", "n_procedures": "2", "n_lab_procedures": "15", "n_medications": "6", "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "0", "medical_specialty": "Surgery", "diag_1": "Musculoskeletal", "diag_2": "Other", "diag_3": "Other", "age": "50-60", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"},
        "manual": {"patient_name": "Surg Musculo", "date_of_birth": "22/04/1970", "time_in_hospital": "2", "n_procedures": "2", "n_lab_procedures": "15", "n_medications": "6", "n_outpatient": "0", "n_inpatient": "0", "n_emergency": "0", "medical_specialty": "Surgery", "diag_1": "Musculoskeletal", "diag_2": "Other", "diag_3": "Other", "age": "50-60", "glucose_test": "no", "A1Ctest": "no", "change": "no", "diabetes_med": "no"}
    },
    {
        "id": 10,
        "name": "Patient 10 - High Emergency Utilization",
        "kaggle": {"time_in_hospital": 5, "n_procedures": 1, "n_lab_procedures": 45, "n_medications": 14, "n_outpatient": 2, "n_inpatient": 2, "n_emergency": 8, "medical_specialty": "Emergency/Trauma", "diag_1": "Circulatory", "diag_2": "Respiratory", "diag_3": "Diabetes", "age": "[70-80)", "glucose_test": "high", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"},
        "csv": {"time_in_hospital": "5", "n_procedures": "1", "n_lab_procedures": "45", "n_medications": "14", "n_outpatient": "2", "n_inpatient": "2", "n_emergency": "8", "medical_specialty": "Emergency/Trauma", "diag_1": "Circulatory", "diag_2": "Respiratory", "diag_3": "Diabetes", "age": "70-80", "glucose_test": "high", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"},
        "manual": {"patient_name": "High Emerg Pt", "date_of_birth": "11/11/1952", "time_in_hospital": "5", "n_procedures": "1", "n_lab_procedures": "45", "n_medications": "14", "n_outpatient": "2", "n_inpatient": "2", "n_emergency": "8", "medical_specialty": "Emergency/Trauma", "diag_1": "Circulatory", "diag_2": "Respiratory", "diag_3": "Diabetes", "age": "70-80", "glucose_test": "high", "A1Ctest": "high", "change": "yes", "diabetes_med": "yes"}
    }
]

@pytest.mark.parametrize("gp", GOLDEN_10_PATIENTS, ids=[f"patient_{p['id']}" for p in GOLDEN_10_PATIENTS])
def test_golden_patient_feature_vector_parity(gp):
    """Verifies 100% exact feature vector parity across Kaggle, CSV, and Manual formats."""
    f_kaggle = build_canonical_model_features(gp["kaggle"])
    f_csv = build_canonical_model_features(gp["csv"])
    f_manual = build_canonical_model_features(gp["manual"])
    
    pd.testing.assert_frame_equal(f_kaggle, f_csv, check_dtype=False)
    pd.testing.assert_frame_equal(f_kaggle, f_manual, check_dtype=False)

@pytest.mark.parametrize("gp", GOLDEN_10_PATIENTS, ids=[f"patient_{p['id']}" for p in GOLDEN_10_PATIENTS])
def test_golden_patient_probability_and_risk_tier_parity(gp):
    """Verifies raw probability, calibrated probability, and risk tier parity for each patient."""
    ms = ModelService()
    f_kaggle = build_canonical_model_features(gp["kaggle"])
    f_csv = build_canonical_model_features(gp["csv"])
    f_manual = build_canonical_model_features(gp["manual"])
    
    raw_k = float(ms.pipeline.predict_proba(f_kaggle)[0, 1])
    raw_c = float(ms.pipeline.predict_proba(f_csv)[0, 1])
    raw_m = float(ms.pipeline.predict_proba(f_manual)[0, 1])
    
    # 1. Raw Probability Parity
    assert abs(raw_k - raw_c) < 1e-10, f"{gp['name']}: Kaggle vs CSV raw prob mismatch"
    assert abs(raw_k - raw_m) < 1e-10, f"{gp['name']}: Kaggle vs Manual raw prob mismatch"
    
    calib_k = ms.calibrate_prob(raw_k)
    calib_c = ms.calibrate_prob(raw_c)
    calib_m = ms.calibrate_prob(raw_m)
    
    # 2. Calibrated Probability Parity
    assert abs(calib_k - calib_c) < 1e-10, f"{gp['name']}: Kaggle vs CSV calibrated prob mismatch"
    assert abs(calib_k - calib_m) < 1e-10, f"{gp['name']}: Kaggle vs Manual calibrated prob mismatch"
    
    tier_k = ms.assign_risk_tier(calib_k)
    tier_c = ms.assign_risk_tier(calib_c)
    tier_m = ms.assign_risk_tier(calib_m)
    
    # 3. Risk Tier Parity
    assert tier_k == tier_c, f"{gp['name']}: Kaggle vs CSV risk tier mismatch"
    assert tier_k == tier_m, f"{gp['name']}: Kaggle vs Manual risk tier mismatch"

@pytest.mark.parametrize("gp", GOLDEN_10_PATIENTS, ids=[f"patient_{p['id']}" for p in GOLDEN_10_PATIENTS])
def test_golden_patient_api_parity(gp):
    """Verifies API endpoints (/predict and /predict_batch) parity for each patient."""
    res_man = client.post("/api/v1/predict", json=gp["manual"])
    assert res_man.status_code == 200
    man_data = res_man.json()
    
    res_batch = client.post("/api/v1/predict_batch", json={"patients": [gp["kaggle"]]})
    assert res_batch.status_code == 200
    batch_data = res_batch.json()["predictions"][0]
    
    man_prob = man_data["calibrated_readmission_probability"]
    batch_prob = batch_data["calibrated_readmission_probability"]
    
    assert abs(man_prob - batch_prob) < 1e-4, f"{gp['name']}: API calibrated prob mismatch"
    assert man_data["clinical_risk_tier"] == batch_data["clinical_risk_tier"], f"{gp['name']}: API risk tier mismatch"

def test_target_leakage_prevention():
    """Verifies that readmitted target column is 100% stripped and excluded from feature generation."""
    leaky_input = {
        "readmitted": "yes",
        "risk_tier": "High Risk",
        "time_in_hospital": 5, "n_procedures": 1, "n_lab_procedures": 40, "n_medications": 12,
        "n_outpatient": 1, "n_inpatient": 1, "n_emergency": 0,
        "medical_specialty": "InternalMedicine", "diag_1": "Diabetes", "diag_2": "Other", "diag_3": "Other",
        "age": "60-70", "glucose_test": "normal", "A1Ctest": "normal", "change": "no", "diabetes_med": "yes"
    }
    
    clean_input = {k: v for k, v in leaky_input.items() if k not in ["readmitted", "risk_tier"]}
    
    f_leaky = build_canonical_model_features(leaky_input)
    f_clean = build_canonical_model_features(clean_input)
    
    pd.testing.assert_frame_equal(f_leaky, f_clean, check_dtype=False)
