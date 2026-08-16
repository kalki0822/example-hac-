import {
  PatientRecord,
  PredictionResult,
  BatchPredictionResponse,
  PaginatedPatientsResponse,
  HealthResponse,
  ModelMetricsResponse
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('vitals_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/health`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const legacy = await fetch(`${API_BASE_URL}/health`);
    if (!legacy.ok) throw new Error('Failed to fetch API health status.');
    return legacy.json();
  }
  return res.json();
}

export async function fetchMetrics(): Promise<ModelMetricsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/model/metrics`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const legacy = await fetch(`${API_BASE_URL}/model/metrics`);
    if (!legacy.ok) throw new Error('Failed to fetch model metrics metadata.');
    return legacy.json();
  }
  return res.json();
}

export async function fetchPatients(
  page: number = 1,
  pageSize: number = 15,
  search?: string,
  source: string = 'ALL',
  uploadId?: string,
  riskTier: string = 'ALL',
  sortBy: string = 'RISK_DESC'
): Promise<PaginatedPatientsResponse> {
  let url = `${API_BASE_URL}/api/v1/patients?page=${page}&page_size=${pageSize}&source=${encodeURIComponent(source)}&risk_tier=${encodeURIComponent(riskTier)}&sort_by=${encodeURIComponent(sortBy)}`;
  
  if (search && search.trim()) {
    url += `&search=${encodeURIComponent(search.trim())}`;
  }
  if (uploadId) {
    url += `&upload_id=${encodeURIComponent(uploadId)}`;
  }

  const res = await fetch(url, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    throw new Error('Failed to fetch paginated patient records.');
  }
  return res.json();
}

export async function fetchUploads(): Promise<any[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/uploads`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchPatientShap(patientId: string): Promise<{ patient_id: string; drivers: any[] }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/patients/${encodeURIComponent(patientId)}/shap`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch SHAP driver analysis for patient ${patientId}`);
  }
  return res.json();
}

export async function predictPatient(patient: PatientRecord & { patient_name?: string; date_of_birth?: string; patient_id?: string }): Promise<PredictionResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify(patient)
  });
  if (!res.ok) {
    throw new Error('Failed to execute single patient readmission prediction.');
  }
  return res.json();
}

export async function predictBatchJSON(patients: PatientRecord[]): Promise<BatchPredictionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/predict_batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify(patients)
  });
  if (!res.ok) {
    throw new Error('Failed to execute JSON batch predictions.');
  }
  return res.json();
}

export async function predictBatchCSV(file: File): Promise<BatchPredictionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/v1/predict_batch`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
    body: formData
  });
  if (!res.ok) {
    throw new Error('Failed to process CSV file batch prediction.');
  }
  return res.json();
}

export const predictBatch = predictBatchJSON;
export const predictBatchCsv = predictBatchCSV;

export async function fetchCalibration(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/model/calibration`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchThresholdAnalysis(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/model/threshold-analysis`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchAuditLogs(limit: number = 100): Promise<any[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/audit/predictions?limit=${limit}`, {
    headers: { ...getAuthHeaders() }
  });
  if (res.status === 401) {
    const err = new Error('UNAUTHORIZED');
    (err as any).status = 401;
    throw err;
  }
  if (!res.ok) {
    const err = new Error(`Failed to fetch audit logs (HTTP ${res.status})`);
    (err as any).status = res.status;
    throw err;
  }
  return res.json();
}

export async function fetchDashboardSummary(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/dashboard/summary`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) return null;
  return res.json();
}
