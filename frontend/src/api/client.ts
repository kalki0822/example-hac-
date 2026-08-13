/// <reference types="vite/client" />
import {
  PatientRecord,
  PredictionResult,
  BatchPredictionResponse,
  PaginatedPatientsResponse,
  HealthResponse,
  ModelMetricsResponse
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } else if (errJson.errors && Array.isArray(errJson.errors)) {
        errorDetail = errJson.errors.join('; ');
      }
    } catch {
      // Ignore JSON parse failure on error body
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`);
  return handleResponse<HealthResponse>(res);
}

export async function fetchMetrics(): Promise<ModelMetricsResponse> {
  const res = await fetch(`${API_BASE_URL}/model/metrics`);
  return handleResponse<ModelMetricsResponse>(res);
}

export async function fetchPatients(page: number = 1, pageSize: number = 15): Promise<PaginatedPatientsResponse> {
  const res = await fetch(`${API_BASE_URL}/patients?page=${page}&page_size=${pageSize}`);
  return handleResponse<PaginatedPatientsResponse>(res);
}

export async function fetchSamplePatients(n: number = 15): Promise<PatientRecord[]> {
  const res = await fetch(`${API_BASE_URL}/sample-patients?n=${n}`);
  return handleResponse<PatientRecord[]>(res);
}

export async function predictPatient(patient: PatientRecord): Promise<PredictionResult> {
  const res = await fetch(`${API_BASE_URL}/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patient),
  });
  return handleResponse<PredictionResult>(res);
}

export async function predictBatch(patients: PatientRecord[]): Promise<BatchPredictionResponse> {
  const res = await fetch(`${API_BASE_URL}/predict_batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patients),
  });
  return handleResponse<BatchPredictionResponse>(res);
}

export async function predictBatchCsv(file: File): Promise<BatchPredictionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/predict_batch`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<BatchPredictionResponse>(res);
}
