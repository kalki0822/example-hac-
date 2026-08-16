import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.database import Base
from api.models_db import User, Patient, Prediction, SHAPExplanation, PreventiveActionRecord, AuditLog, ModelVersion

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_database_user_creation(db_session):
    user = User(email="test@vitals.health", hashed_password="hashedpassword123", full_name="Dr. Test", role="CLINICIAN")
    db_session.add(user)
    db_session.commit()
    
    saved_user = db_session.query(User).filter_by(email="test@vitals.health").first()
    assert saved_user is not None
    assert saved_user.role == "CLINICIAN"

def test_database_prediction_and_associations(db_session):
    patient = Patient(
        patient_id="PT-99999",
        age="[70-80)",
        medical_specialty="Cardiology",
        time_in_hospital=5,
        n_inpatient=2,
        n_emergency=1,
        n_outpatient=1,
        n_medications=15,
        n_lab_procedures=50,
        n_procedures=2,
        diag_1="Circulatory",
        diag_2="Respiratory",
        diag_3="Diabetes"
    )
    db_session.add(patient)
    db_session.commit()

    prediction = Prediction(
        patient_reference="PT-99999",
        patient_id=patient.id,
        probability=0.65,
        predicted_class="yes",
        risk_tier="High Risk",
        operating_threshold=0.2562,
        model_name="LogisticRegression",
        model_version="1.0.0"
    )
    db_session.add(prediction)
    db_session.commit()

    shap_exp = SHAPExplanation(
        prediction_id=prediction.id,
        feature_name="n_inpatient",
        shap_value=0.45,
        direction="Increases Readmission Risk",
        plain_language_label="2 prior inpatient admission(s) in past year"
    )
    db_session.add(shap_exp)

    action_rec = PreventiveActionRecord(
        prediction_id=prediction.id,
        title="Consider early follow-up",
        reason="High inpatient utilization",
        priority="High",
        category="FOLLOW_UP"
    )
    db_session.add(action_rec)
    db_session.commit()

    saved_pred = db_session.query(Prediction).filter_by(patient_reference="PT-99999").first()
    assert saved_pred is not None
    assert saved_pred.probability == 0.65
    assert len(saved_pred.explanations) == 1
    assert len(saved_pred.preventive_actions) == 1

def test_database_audit_log(db_session):
    log = AuditLog(
        role="ADMIN",
        action="MODEL_VIEW",
        resource="/api/v1/model/metrics",
        request_id="req-12345",
        status="SUCCESS"
    )
    db_session.add(log)
    db_session.commit()

    saved_log = db_session.query(AuditLog).filter_by(action="MODEL_VIEW").first()
    assert saved_log is not None
    assert saved_log.role == "ADMIN"
