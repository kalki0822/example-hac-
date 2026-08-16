export interface PatientRecord {
  age: string;
  time_in_hospital: number;
  n_procedures: number;
  n_lab_procedures: number;
  n_medications: number;
  n_outpatient: number;
  n_inpatient: number;
  n_emergency: number;
  medical_specialty: string;
  diag_1: string;
  diag_2: string;
  diag_3: string;
  glucose_test: string;
  A1Ctest: string;
  change: string;
  diabetes_med: string;
  patient_id?: string;
  patient_name?: string;
  date_of_birth?: string;
  source?: string;
  upload_id?: string;
  source_filename?: string;
  original_row_index?: number;
  [key: string]: any;
}

export interface SHAPDriver {
  feature: string;
  shap_value: number;
  direction: string;
  plain_language_driver: string;
}

export interface PreventiveAction {
  title: string;
  reason: string;
  priority: 'High' | 'Medium' | 'Routine';
}

export interface PredictionResult {
  readmission_probability: number;
  predicted_readmitted: 'yes' | 'no';
  operating_threshold: number;
  clinical_risk_tier: 'Minimal Risk' | 'Moderate Risk' | 'Elevated Risk' | 'High Risk' | 'Low Risk';
  top_3_shap_drivers: SHAPDriver[];
  preventive_actions: PreventiveAction[];
  patient_id?: string;
  patient_name?: string;
  date_of_birth?: string;
}

export interface BatchPatientResult {
  patient_index: number;
  readmission_probability: number;
  predicted_readmitted: 'yes' | 'no';
  clinical_risk_tier: 'Minimal Risk' | 'Moderate Risk' | 'Elevated Risk' | 'High Risk' | 'Low Risk';
  primary_driver?: string;
  patient_id?: string;
  patient_name?: string;
  date_of_birth?: string;
  source?: string;
  source_filename?: string;
  patient_data?: PatientRecord;
  preventive_actions?: PreventiveAction[];
}

export interface BatchPredictionResponse {
  total_patients: number;
  high_risk_count: number;
  moderate_risk_count: number;
  low_risk_count: number;
  upload_id?: string;
  source_filename?: string;
  predictions: BatchPatientResult[];
}

export interface PaginatedPatientsResponse {
  patients: PatientRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  high_risk_count?: number;
  elevated_risk_count?: number;
  moderate_risk_count?: number;
  minimal_risk_count?: number;
  low_risk_count?: number;
}

export interface CSVUploadRecord {
  upload_id: string;
  filename: string;
  total_patients: number;
  high_risk_count: number;
  elevated_risk_count?: number;
  moderate_risk_count: number;
  minimal_risk_count?: number;
  low_risk_count: number;
  uploaded_at: string;
  user_email?: string;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  model_name: string;
  version: string;
  operating_threshold: number;
}

export interface ModelMetricsResponse {
  model_name: string;
  version: string;
  timestamp: string;
  dataset_rows?: number;
  optimal_threshold: number;
  cost_parameters: {
    cost_fn: number;
    cost_fp: number;
  };
  evaluation_metrics_oof: {
    threshold: number;
    roc_auc: number;
    pr_auc: number;
    f1_score: number;
    recall_positive: number;
    precision_positive: number;
    confusion_matrix: {
      tn: number;
      fp: number;
      fn: number;
      tp: number;
    };
    total_cost: number;
    avg_cost_per_patient: number;
  };
  roc_curve_points?: Array<{ fpr: number; tpr: number }>;
  all_model_results_oof: Record<string, any>;
  num_transformed_features: number;
}
