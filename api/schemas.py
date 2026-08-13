from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional

class PatientInput(BaseModel):
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

class PredictionResponse(BaseModel):
    readmission_probability: float = Field(..., description="Predicted 30-day readmission probability [0, 1]")
    predicted_readmitted: str = Field(..., description="'yes' if probability >= threshold, else 'no'")
    operating_threshold: float = Field(..., description="Cost-sensitive decision threshold")
    clinical_risk_tier: str = Field(..., description="Risk tier: 'Low Risk', 'Moderate Risk', or 'High Risk'")
    top_3_shap_drivers: List[SHAPDriver] = Field(..., description="Top 3 SHAP explainability risk drivers")

class BatchPatientPrediction(BaseModel):
    patient_index: int = Field(..., description="Row index in batch payload")
    readmission_probability: float = Field(..., description="Predicted readmission probability")
    predicted_readmitted: str = Field(..., description="'yes' or 'no'")
    clinical_risk_tier: str = Field(..., description="'Low Risk', 'Moderate Risk', or 'High Risk'")
    primary_driver: Optional[str] = Field(None, description="Top plain-language SHAP driver")

class BatchPredictionResponse(BaseModel):
    total_patients: int = Field(..., description="Total patient records processed")
    high_risk_count: int = Field(..., description="Number of patients categorized as High Risk")
    moderate_risk_count: int = Field(..., description="Number of patients categorized as Moderate Risk")
    low_risk_count: int = Field(..., description="Number of patients categorized as Low Risk")
    predictions: List[BatchPatientPrediction] = Field(..., description="Per-patient prediction list for ward view")

class PaginatedPatientsResponse(BaseModel):
    patients: List[Dict[str, Any]] = Field(..., description="Page slice of patient records")
    total: int = Field(..., description="Total dataset row count (25,000)")
    page: int = Field(..., description="Current requested page number (1-indexed)")
    page_size: int = Field(..., description="Number of records per page (default 15)")
    total_pages: int = Field(..., description="Total number of available pages")

class RootLandingResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    timestamp: str = Field(..., json_schema_extra={"example": "2026-08-14T01:45:00Z"})
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
    model_loaded: bool = Field(..., json_schema_extra={"example": True})
    model_name: str = Field(..., json_schema_extra={"example": "LogisticRegression"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    operating_threshold: float = Field(..., json_schema_extra={"example": 0.2562})

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
