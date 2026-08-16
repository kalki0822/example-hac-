import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from api.database import engine, get_db, SessionLocal, seed_initial_patients, clean_junk_upload_records
from api.models_db import Patient, Prediction, SHAPExplanation, CSVUploadRecord

client = TestClient(app)

def test_postgresql_engine_active():
    db_url = str(engine.url)
    assert "postgresql" in db_url, f"Expected PostgreSQL database engine, got: {db_url}"
    assert "sqlite" not in db_url, "SQLite must not be used as runtime database!"

def test_model_and_dataset_hashes():
    model_path = "models/best_model.pkl"
    dataset_path = "data/raw/hospital_readmissions.csv"
    
    assert os.path.exists(model_path), "Model artifact missing!"
    assert os.path.exists(dataset_path), "Raw Kaggle dataset missing!"

    m_hash = hashlib.sha256(open(model_path, "rb").read()).hexdigest().upper()
    d_hash = hashlib.sha256(open(dataset_path, "rb").read()).hexdigest().upper()

    expected_m_hash = "74BA9C6508BAD62F6378E35679E0BB8C693FDC7B2D33AD51C2C859FCBF9FB3C0"
    expected_d_hash = "AC59A074708D90F9C0F80478E51D13D9E092085AE40FC35468CEB2C4016211B4"

    assert m_hash == expected_m_hash, f"Model SHA-256 hash changed! Got {m_hash}"
    assert d_hash == expected_d_hash, f"Dataset SHA-256 hash changed! Got {d_hash}"

def test_kaggle_idempotent_seeding():
    db: Session = SessionLocal()
    try:
        initial_kaggle_cnt = db.query(Patient).filter(Patient.source == "KAGGLE").count()
        assert initial_kaggle_cnt == 25000, f"Expected 25,000 Kaggle records in PostgreSQL, found {initial_kaggle_cnt}"
        
        # Run seed_initial_patients again
        seed_initial_patients(db)
        
        after_cnt = db.query(Patient).filter(Patient.source == "KAGGLE").count()
        assert after_cnt == 25000, f"Kaggle seeding duplicate prevention failed! Count became {after_cnt}"
    finally:
        db.close()

def test_junk_csv_upload_cleanup_and_registry():
    db = SessionLocal()
    clean_junk_upload_records(db)
    db.close()
    res = client.get("/api/v1/uploads")
    assert res.status_code == 200
    uploads = res.json()
    
    junk_names = ["manual_batch_upload.csv", "batch_test.csv", "test.csv"]
    for u in uploads:
        assert u["filename"] not in junk_names, f"Junk upload record '{u['filename']}' present in registry!"
        assert u["upload_id"].startswith("UP-"), f"Upload ID format invalid: {u['upload_id']}"

def test_demo_records_zero():
    db: Session = SessionLocal()
    try:
        demo_cnt = db.query(Patient).filter(Patient.patient_id.like("%DEMO%")).count()
        assert demo_cnt == 0, f"Expected 0 DEMO records in production database, found {demo_cnt}"
    finally:
        db.close()

def test_shap_endpoint_execution_and_persistence():
    # Pick a Kaggle patient ID
    patient_id = "PT-10001"
    res = client.get(f"/api/v1/patients/{patient_id}/shap")
    assert res.status_code == 200, f"SHAP endpoint failed: {res.text}"
    data = res.json()
    
    assert data["patient_id"] == patient_id
    assert "drivers" in data
    assert len(data["drivers"]) > 0, "SHAP drivers should be returned"
    
    first_driver = data["drivers"][0]
    assert "feature" in first_driver
    assert "label" in first_driver
    assert "value" in first_driver
    assert "shap_value" in first_driver
    assert first_driver["impact"] in ["increases_risk", "decreases_risk"]

    # Verify SHAP explanations persist in PostgreSQL
    db: Session = SessionLocal()
    try:
        shap_records = db.query(SHAPExplanation).filter(SHAPExplanation.patient_id == patient_id).all()
        assert len(shap_records) > 0, f"SHAP records not persisted in PostgreSQL for {patient_id}"
    finally:
        db.close()

def test_csv_upload_isolation():
    import uuid
    u_tag = uuid.uuid4().hex[:6]
    csv_content = f"""patient_name,age,time_in_hospital,n_procedures,n_lab_procedures,n_medications,n_outpatient,n_inpatient,n_emergency,medical_specialty,diag_1,diag_2,diag_3,glucose_test,A1Ctest,change,diabetes_med
IsoPatient A {u_tag},[70-80),5,2,45,18,1,2,1,InternalMedicine,Circulatory,Respiratory,Diabetes,high,high,yes,yes
IsoPatient B {u_tag},[40-50),2,1,20,5,0,0,0,Surgery,Digestive,Other,Other,no,no,no,no
"""
    unique_fn = f"clinical_cohort_{u_tag}.csv"
    files = {"file": (unique_fn, csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/v1/predict_batch", files=files)
    assert res.status_code == 200
    b_data = res.json()
    upload_id = b_data["upload_id"]
    assert upload_id.startswith("UP-")

    # Fetch patients by upload_id
    res_pts = client.get(f"/api/v1/patients?upload_id={upload_id}&source=ALL")
    assert res_pts.status_code == 200
    pts_data = res_pts.json()
    assert pts_data["total"] == 2
    for p in pts_data["patients"]:
        assert p["upload_id"] == upload_id
        assert p["source"] == "UPLOADED_CSV"

def test_patient_specific_shap_and_actions():
    high_cardiac = {
        "patient_name": "High Cardiac Patient",
        "date_of_birth": "12/04/1945",
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
        "patient_name": "Low Surgery Patient",
        "date_of_birth": "05/11/1982",
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

    assert r1["readmission_probability"] > r2["readmission_probability"]
    assert r1["clinical_risk_tier"] in ["High Risk", "Elevated Risk"]
    assert r2["clinical_risk_tier"] in ["Minimal Risk", "Moderate Risk", "Low Risk"]

    # Verify SHAP values differ based on patient clinical parameters
    s1_vals = [d["shap_value"] for d in r1["top_3_shap_drivers"]]
    s2_vals = [d["shap_value"] for d in r2["top_3_shap_drivers"]]
    assert s1_vals != s2_vals, "SHAP values must reflect patient clinical parameters"

    # Verify preventive actions are patient-specific
    act1_titles = [a["title"] for a in r1["preventive_actions"]]
    act2_titles = [a["title"] for a in r2["preventive_actions"]]
    assert act1_titles != act2_titles, "Preventive actions must be patient-specific"
