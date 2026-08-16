from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from api.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="CLINICIAN", nullable=False)  # ADMIN, CLINICIAN, ANALYST
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    predictions = relationship("Prediction", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    uploads = relationship("CSVUploadRecord", back_populates="user")

class CSVUploadRecord(Base):
    __tablename__ = "csv_uploads"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, unique=True, index=True, nullable=False)  # e.g. UP-000001
    filename = Column(String, nullable=False)  # e.g. hospital_august.csv
    total_patients = Column(Integer, default=0, nullable=False)
    high_risk_count = Column(Integer, default=0, nullable=False)
    moderate_risk_count = Column(Integer, default=0, nullable=False)
    low_risk_count = Column(Integer, default=0, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by = Column(String, nullable=True, default="System User")
    status = Column(String, default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, CLEANED
    source_type = Column(String, default="UPLOADED_CSV", nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    user = relationship("User", back_populates="uploads")
    patients = relationship("Patient", back_populates="upload_record")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, unique=True, index=True, nullable=False)  # e.g. PT-10001, PT-UP-00001, PT-MAN-00001
    patient_name = Column(String, nullable=True, index=True)               # Patient Name e.g. Arun Kumar
    date_of_birth = Column(String, nullable=True, index=True)              # DOB e.g. 01/01/1990
    source = Column(String, default="KAGGLE", index=True, nullable=False)   # KAGGLE, UPLOADED_CSV, MANUAL
    environment = Column(String, default="PRODUCTION", nullable=False)      # PRODUCTION
    upload_id = Column(String, ForeignKey("csv_uploads.upload_id"), nullable=True, index=True) # References CSVUploadRecord.upload_id
    source_filename = Column(String, nullable=True)

    age = Column(String, nullable=False)
    medical_specialty = Column(String, nullable=False)
    time_in_hospital = Column(Integer, nullable=False)
    n_inpatient = Column(Integer, nullable=False)
    n_emergency = Column(Integer, nullable=False)
    n_outpatient = Column(Integer, nullable=False)
    n_medications = Column(Integer, nullable=False)
    n_lab_procedures = Column(Integer, nullable=False)
    n_procedures = Column(Integer, nullable=False)
    diag_1 = Column(String, nullable=False)
    diag_2 = Column(String, nullable=False)
    diag_3 = Column(String, nullable=False)
    glucose_test = Column(String, default="no", nullable=False)
    A1Ctest = Column(String, default="no", nullable=False)
    change = Column(String, default="no", nullable=False)
    diabetes_med = Column(String, default="no", nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    predictions = relationship("Prediction", back_populates="patient", cascade="all, delete-orphan")
    upload_record = relationship("CSVUploadRecord", back_populates="patients")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    patient_reference = Column(String, index=True, nullable=False)  # Stable patient_id string (e.g. PT-UP-00001)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    probability = Column(Float, nullable=False)
    raw_probability = Column(Float, nullable=True)
    calibrated_probability = Column(Float, nullable=True)
    predicted_class = Column(String, nullable=False)  # "yes" or "no"
    risk_tier = Column(String, nullable=False)       # High Risk, Elevated Risk, Moderate Risk, Minimal Risk
    operating_threshold = Column(Float, nullable=False)
    model_name = Column(String, default="LogisticRegression", nullable=False)
    model_version = Column(String, default="1.0.0", nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    user = relationship("User", back_populates="predictions")
    patient = relationship("Patient", back_populates="predictions")
    explanations = relationship("SHAPExplanation", back_populates="prediction", cascade="all, delete-orphan")
    preventive_actions = relationship("PreventiveActionRecord", back_populates="prediction", cascade="all, delete-orphan")

class SHAPExplanation(Base):
    __tablename__ = "shap_explanations"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    patient_id = Column(String, index=True, nullable=True) # Stable patient_id e.g. PT-10001
    feature_name = Column(String, nullable=False)
    display_label = Column(String, nullable=True)
    feature_value = Column(String, nullable=True)
    shap_value = Column(Float, nullable=False)
    direction = Column(String, nullable=False) # "increases_risk" or "decreases_risk"
    plain_language_label = Column(String, nullable=False)
    rank = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    prediction = relationship("Prediction", back_populates="explanations")

class PreventiveActionRecord(Base):
    __tablename__ = "preventive_action_records"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    title = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    priority = Column(String, nullable=False)  # High, Medium, Routine
    category = Column(String, default="GENERAL", nullable=False)

    prediction = relationship("Prediction", back_populates="preventive_actions")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String, nullable=False)
    action = Column(String, nullable=False)  # LOGIN, PREDICTION, BATCH_PREDICTION, PATIENT_VIEW, MODEL_VIEW, CSV_UPLOAD
    resource = Column(String, nullable=False)
    patient_reference = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    model_version = Column(String, default="1.0.0", nullable=True)
    status = Column(String, default="SUCCESS", nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    user = relationship("User", back_populates="audit_logs")

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    version = Column(String, unique=True, nullable=False)
    training_dataset = Column(String, nullable=False)
    dataset_version = Column(String, default="1.0", nullable=False)
    dataset_rows = Column(Integer, nullable=False)
    operating_threshold = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
