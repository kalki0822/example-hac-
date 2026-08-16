from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Dict, Any, Optional

# Patient Input & Prediction Schemas
class PatientInput(BaseModel):
    patient_name: Optional[str] = Field(None, description="Patient full name e.g. Arun Kumar", json_schema_extra={"example": "Arun Kumar"})
    date_of_birth: Optional[str] = Field(None, description="Date of birth DD/MM/YYYY", json_schema_extra={"example": "01/01/1990"})
    patient_id: Optional[str] = Field(None, description="Hospital patient ID or blank for auto-generated PT-MAN-XXXXX")
    
    age: str = Field(..., description="Age bracket, e.g., '[70-80)'", json_schema_extra={"example": "[70-80)"})
    time_in_hospital: int = Field(..., ge=1, le=30, description="Hospital stay duration in days (1-30)", json_schema_extra={"example": 5})
    n_procedures: int = Field(..., ge=0, le=20, description="Number of non-lab procedures during stay", json_schema_extra={"example": 2})
    n_lab_procedures: int = Field(..., ge=0, le=200, description="Number of lab tests performed", json_schema_extra={"example": 45})
    n_medications: int = Field(..., ge=0, le=150, description="Number of medications administered", json_schema_extra={"example": 18})
    n_outpatient: int = Field(..., ge=0, le=100, description="Number of outpatient visits in past year", json_schema_extra={"example": 1})
    n_inpatient: int = Field(..., ge=0, le=100, description="Number of prior inpatient admissions in past year", json_schema_extra={"example": 2})
    n_emergency: int = Field(..., ge=0, le=100, description="Number of emergency room visits in past year", json_schema_extra={"example": 1})
    medical_specialty: str = Field(..., description="Admitting medical specialty", json_schema_extra={"example": "InternalMedicine"})
    diag_1: str = Field(..., description="Primary diagnosis category/code", json_schema_extra={"example": "Circulatory"})
    diag_2: str = Field(..., description="Secondary diagnosis category/code", json_schema_extra={"example": "Respiratory"})
    diag_3: str = Field(..., description="Additional diagnosis category/code", json_schema_extra={"example": "Diabetes"})
    glucose_test: str = Field(..., description="Glucose test result: 'no', 'normal', or 'high'", json_schema_extra={"example": "high"})
    A1Ctest: str = Field(..., description="HbA1c test result: 'no', 'normal', or 'high'", json_schema_extra={"example": "high"})
    change: str = Field(..., description="Medication change indicator: 'yes' or 'no'", json_schema_extra={"example": "yes"})
    diabetes_med: str = Field(..., description="Prescribed diabetes medication: 'yes' or 'no'", json_schema_extra={"example": "yes"})

    model_config = ConfigDict(extra="ignore")

class SHAPDriver(BaseModel):
    feature: str = Field(..., description="Raw or transformed feature key")
    shap_value: float = Field(..., description="SHAP numerical contribution value")
    direction: str = Field(..., description="Direction of risk impact")
    plain_language_driver: str = Field(..., description="Human-readable clinical driver label")

class PreventiveAction(BaseModel):
    title: str = Field(..., description="Action title for clinician consideration")
    reason: str = Field(..., description="Patient-specific rationale")
    priority: str = Field(..., description="Action priority tier: 'High', 'Medium', or 'Routine'")

class PredictionResponse(BaseModel):
    prediction_id: Optional[int] = Field(None, description="Database persistent prediction ID")
    patient_id: Optional[str] = Field(None, description="Stable patient identifier")
    patient_name: Optional[str] = Field(None, description="Patient full name")
    date_of_birth: Optional[str] = Field(None, description="Patient date of birth")
    readmission_probability: float = Field(..., description="Predicted 30-day readmission probability [0, 1]")
    raw_readmission_probability: Optional[float] = Field(None, description="Raw base model readmission probability")
    calibrated_readmission_probability: Optional[float] = Field(None, description="Platt Scaling calibrated readmission probability")
    reference_cohort_rank: Optional[str] = Field(None, description="Relative reference cohort rank (e.g. Q4 · High Risk Band)")
    reference_q4_boundary: Optional[str] = Field(None, description="Reference cohort Q4 cutoff boundary")
    predicted_readmitted: str = Field(..., description="'yes' if probability >= threshold, else 'no'")
    operating_threshold: float = Field(..., description="Cost-sensitive decision threshold")
    clinical_risk_tier: str = Field(..., description="Risk tier: 'Low Risk', 'Moderate Risk', or 'High Risk'")
    top_3_shap_drivers: List[SHAPDriver] = Field(..., description="Top 3 SHAP explainability risk drivers")
    preventive_actions: List[PreventiveAction] = Field(..., description="Suggested preventive actions for clinician consideration")
    model_version: Optional[str] = Field("1.0.0", description="Version of prediction model used")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of prediction")

class BatchPatientPrediction(BaseModel):
    patient_index: int = Field(..., description="Row index in batch payload")
    readmission_probability: float = Field(..., description="Predicted readmission probability")
    raw_readmission_probability: Optional[float] = Field(None, description="Raw base model readmission probability")
    calibrated_readmission_probability: Optional[float] = Field(None, description="Platt Scaling calibrated readmission probability")
    reference_cohort_rank: Optional[str] = Field(None, description="Relative reference cohort rank")
    predicted_readmitted: str = Field(..., description="'yes' or 'no'")
    clinical_risk_tier: str = Field(..., description="'Low Risk', 'Moderate Risk', or 'High Risk'")
    primary_driver: Optional[str] = Field(None, description="Top plain-language SHAP driver")
    patient_id: Optional[str] = Field(None, description="Stable patient identifier")
    patient_name: Optional[str] = Field(None, description="Patient full name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth")
    preventive_actions: Optional[List[PreventiveAction]] = Field(None, description="Patient-specific preventive action recommendations")

class BatchPredictionResponse(BaseModel):
    upload_id: Optional[str] = Field(None, description="Unique upload identifier")
    source_filename: Optional[str] = Field(None, description="Original uploaded CSV filename")
    total_patients: int = Field(..., description="Total patient records processed")
    high_risk_count: int = Field(..., description="Number of patients categorized as High Risk")
    moderate_risk_count: int = Field(..., description="Number of patients categorized as Moderate Risk")
    low_risk_count: int = Field(..., description="Number of patients categorized as Low Risk")
    predictions: List[BatchPatientPrediction] = Field(..., description="Per-patient prediction list for ward view")

class PaginatedPatientsResponse(BaseModel):
    patients: List[Dict[str, Any]] = Field(..., description="Page slice of patient records")
    total: int = Field(..., description="Total matching dataset row count")
    page: int = Field(..., description="Current requested page number (1-indexed)")
    page_size: int = Field(..., description="Number of records per page (default 15)")
    total_pages: int = Field(..., description="Total number of available pages")
    minimal_risk_count: int = Field(0, description="Matching Minimal Risk count")
    moderate_risk_count: int = Field(0, description="Matching Moderate Risk count")
    elevated_risk_count: int = Field(0, description="Matching Elevated Risk count")
    high_risk_count: int = Field(0, description="Matching High Risk count")
    low_risk_count: int = Field(0, description="Matching Low Risk count")

# CSV Upload Metadata Schema
class CSVUploadResponse(BaseModel):
    upload_id: str
    filename: str
    total_patients: int
    minimal_risk_count: int = 0
    moderate_risk_count: int = 0
    elevated_risk_count: int = 0
    high_risk_count: int = 0
    low_risk_count: int = 0
    uploaded_at: str
    user_email: Optional[str] = None

# Auth Schemas
class LoginRequest(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "clinician@vitals.health"})
    password: str = Field(..., json_schema_extra={"example": "Clinician123!"})

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserRegisterRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(...)
    full_name: str = Field(...)
    role: str = Field("CLINICIAN", description="CLINICIAN, ANALYST, or ADMIN")

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool

# Audit & Monitoring Schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    role: str
    action: str
    resource: str
    request_id: Optional[str]
    model_version: Optional[str]
    status: str
    timestamp: str

class CalibrationPoint(BaseModel):
    prob_pred: float
    prob_true: float

class CalibrationResponse(BaseModel):
    brier_score: float
    calibration_curve: List[CalibrationPoint]
    n_bins: int
    note: str = "Probability calibration monitoring only; production model prediction probabilities are untouched."

class ThresholdGridRow(BaseModel):
    threshold: float
    recall: float
    precision: float
    specificity: float
    f1_score: float
    tn: int
    fp: int
    fn: int
    tp: int
    total_cost: float
    avg_cost_per_patient: float
    is_selected: bool

class ThresholdAnalysisResponse(BaseModel):
    cost_fn: float = 5.0
    cost_fp: float = 1.0
    operating_threshold: float = 0.2562
    selected_avg_cost: float = 0.5286
    threshold_grid: List[ThresholdGridRow]

class DashboardSummaryResponse(BaseModel):
    total_patients_dataset: int = 25000
    total_patients_db: int = 25000
    kaggle_patients_count: int = 25000
    uploaded_csv_count: int = 0
    manual_patients_count: int = 0
    total_predictions_logged: int = 0
    high_risk_count: int = 0
    moderate_risk_count: int = 0
    low_risk_count: int = 0
    active_users_count: int = 3
    model_name: str = "LogisticRegression"
    model_version: str = "1.0.0"

class RootLandingResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    timestamp: str = Field(..., json_schema_extra={"example": "2026-08-15T17:46:00Z"})
    model_loaded: bool = Field(..., json_schema_extra={"example": True})
    model_name: str = Field(..., json_schema_extra={"example": "LogisticRegression"})
    operating_threshold: float = Field(..., json_schema_extra={"example": 0.2562})
    cost_fn: float = Field(..., json_schema_extra={"example": 5.0})
    cost_fp: float = Field(..., json_schema_extra={"example": 1.0})
    dataset_rows: int = Field(..., json_schema_extra={"example": 25000})
    model_path: str = Field(..., json_schema_extra={"example": "models/best_model.pkl"})
    metadata_path: str = Field(..., json_schema_extra={"example": "models/model_metadata.json"})
    shap_global_path: str = Field(..., json_schema_extra={"example": "reports/figures/shap_summary.png"})
    features_count: int = Field(..., json_schema_extra={"example": 16})
    message: str = Field(..., json_schema_extra={"example": "Vitals API is running successfully"})

class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    api: bool = True
    database: bool = True
    model_loaded: bool = Field(..., json_schema_extra={"example": True})
    model_name: str = Field(..., json_schema_extra={"example": "LogisticRegression"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    operating_threshold: float = Field(..., json_schema_extra={"example": 0.2562})
    dataset_rows: int = 25000

class MetricsResponse(BaseModel):
    model_name: str
    version: str
    timestamp: str
    dataset_rows: int
    optimal_threshold: float
    cost_parameters: Dict[str, float]
    evaluation_metrics_oof: Dict[str, Any]
    roc_curve_points: List[Dict[str, float]]
    all_model_results_oof: Dict[str, Any]
    num_transformed_features: int
