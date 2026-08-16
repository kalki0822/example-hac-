import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

logger = logging.getLogger(__name__)

# PostgreSQL is the mandatory runtime database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/vitals_db"
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

logger.info(f"Connecting to PostgreSQL Database at: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_initial_users(db: Session):
    """Seeds default RBAC users into database if empty."""
    from api.models_db import User
    from api.auth import hash_password

    if db.query(User).count() > 0:
        return

    logger.info("Seeding initial RBAC users into database...")
    users = [
        User(
            email="clinician@vitals.health",
            hashed_password=hash_password("Clinician123!"),
            full_name="Dr. Sarah Jenkins",
            role="CLINICIAN"
        ),
        User(
            email="analyst@vitals.health",
            hashed_password=hash_password("Analyst123!"),
            full_name="Marcus Vance, Lead Data Analyst",
            role="ANALYST"
        ),
        User(
            email="admin@vitals.health",
            hashed_password=hash_password("Admin123!"),
            full_name="System Administrator",
            role="ADMIN"
        )
    ]
    for u in users:
        db.add(u)
    db.commit()

def seed_initial_patients(db: Session):
    """
    Idempotently seeds 25,000 Kaggle patient records & real frozen ML predictions into PostgreSQL.
    No demo records seeded.
    """
    from api.models_db import Patient, Prediction, SHAPExplanation, PreventiveActionRecord
    from api.dependencies import ModelService, translate_to_plain_language
    from src.explainability.shap_utils import explain_single_prediction
    from src.recommendations import generate_preventive_actions

    existing_kaggle = db.query(Patient).filter(Patient.source == "KAGGLE").first()
    if existing_kaggle:
        logger.info("Kaggle patient dataset already seeded in PostgreSQL. Skipping.")
        return

    logger.info("Executing ONE-TIME Kaggle dataset seeding (25,000 records) into PostgreSQL...")
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "hospital_readmissions.csv")
    if not os.path.exists(csv_path):
        logger.error(f"Raw dataset CSV not found at {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
        ms = ModelService()

        raw_records = df.to_dict("records")
        batch_res = ms.predict_batch(raw_records)
        predictions_data = batch_res["predictions"]

        patient_objects = []
        for idx, row in df.iterrows():
            p_id = f"PT-{(10000 + idx + 1)}"
            p_obj = Patient(
                patient_id=p_id,
                source="KAGGLE",
                environment="PRODUCTION",
                age=str(row.get("age", "[50-60)")),
                medical_specialty=str(row.get("medical_specialty", "Missing")),
                time_in_hospital=int(row.get("time_in_hospital", 1)),
                n_inpatient=int(row.get("n_inpatient", 0)),
                n_emergency=int(row.get("n_emergency", 0)),
                n_outpatient=int(row.get("n_outpatient", 0)),
                n_medications=int(row.get("n_medications", 1)),
                n_lab_procedures=int(row.get("n_lab_procedures", 1)),
                n_procedures=int(row.get("n_procedures", 0)),
                diag_1=str(row.get("diag_1", "Other")),
                diag_2=str(row.get("diag_2", "Other")),
                diag_3=str(row.get("diag_3", "Other")),
                glucose_test=str(row.get("glucose_test", "no")),
                A1Ctest=str(row.get("A1Ctest", "no")),
                change=str(row.get("change", "no")),
                diabetes_med=str(row.get("diabetes_med", "no"))
            )
            patient_objects.append(p_obj)

        db.bulk_save_objects(patient_objects)
        db.commit()

        # Retrieve created patient IDs map
        db_patients = db.query(Patient).filter(Patient.source == "KAGGLE").all()
        p_map = {p.patient_id: p.id for p in db_patients}

        prediction_objects = []
        for idx, pred_info in enumerate(predictions_data):
            p_id = f"PT-{(10000 + idx + 1)}"
            db_pid = p_map.get(p_id)
            if not db_pid:
                continue

            prob = pred_info["readmission_probability"]
            risk_tier = pred_info["clinical_risk_tier"]
            pred_class = pred_info["predicted_readmitted"]

            pred_obj = Prediction(
                patient_reference=p_id,
                patient_id=db_pid,
                user_id=None,
                probability=prob,
                predicted_class=pred_class,
                risk_tier=risk_tier,
                operating_threshold=ms.threshold,
                model_name="LogisticRegression",
                model_version="1.0.0"
            )
            prediction_objects.append(pred_obj)

        db.bulk_save_objects(prediction_objects)
        db.commit()

        logger.info(f"Successfully seeded {len(patient_objects)} Kaggle patients into PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to seed Kaggle patients into PostgreSQL: {e}")
        db.rollback()

def clean_junk_upload_records(db: Session) -> dict:
    """Purges historical junk test upload records and their dependent patients."""
    from api.models_db import CSVUploadRecord, Patient, Prediction, SHAPExplanation, PreventiveActionRecord
    junk_names = ["manual_batch_upload.csv", "batch_test.csv", "test.csv", "uploaded_clinical_batch.csv"]
    stale_uploads = db.query(CSVUploadRecord).filter(
        (CSVUploadRecord.filename.in_(junk_names)) | (CSVUploadRecord.status != "ACTIVE")
    ).all()
    cleaned_ids = [u.upload_id for u in stale_uploads]
    for u in stale_uploads:
        patients = db.query(Patient).filter(Patient.upload_id == u.upload_id).all()
        p_ids = [p.id for p in patients]
        if p_ids:
            db.query(SHAPExplanation).filter(SHAPExplanation.prediction_id.in_(
                db.query(Prediction.id).filter(Prediction.patient_id.in_(p_ids))
            )).delete(synchronize_session=False)
            db.query(PreventiveActionRecord).filter(PreventiveActionRecord.prediction_id.in_(
                db.query(Prediction.id).filter(Prediction.patient_id.in_(p_ids))
            )).delete(synchronize_session=False)
            db.query(Prediction).filter(Prediction.patient_id.in_(p_ids)).delete(synchronize_session=False)
            db.query(Patient).filter(Patient.id.in_(p_ids)).delete(synchronize_session=False)
        db.delete(u)
    if stale_uploads:
        db.commit()
    return {
        "junk_uploads_removed": len(stale_uploads),
        "cleaned_upload_ids": cleaned_ids
    }

def init_db():
    """Initializes PostgreSQL schema and seeds users & Kaggle patients idempotently."""
    import api.models_db
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        seed_initial_users(db)
        seed_initial_patients(db)
    finally:
        db.close()
