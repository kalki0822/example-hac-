import io
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import List, Union, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.schemas import (
    PatientInput,
    PredictionResponse,
    BatchPredictionResponse,
    PaginatedPatientsResponse,
    RootLandingResponse,
    HealthResponse,
    MetricsResponse
)
from api.dependencies import get_model_service, ModelService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vitals — Hospital Readmission Risk Platform API",
    description="REST API service providing real-time and batch hospital readmission risk scoring, cost-sensitive thresholding, full dataset pagination, and plain-language SHAP explainability drivers.",
    version="1.0.0"
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors into clear, readable HTTP 422 JSON responses."""
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        msg = err.get("msg", "Invalid value")
        errors.append(f"Field '{field}': {msg}")
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request payload or schema validation failure.",
            "errors": errors,
            "raw_errors": exc.errors()
        }
    )

@app.get("/", response_model=RootLandingResponse, tags=["Monitoring"])
def root_landing(model_service: ModelService = Depends(get_model_service)):
    """
    Root API landing endpoint returning operational status, loaded model metadata,
    dataset row count, threshold parameters, and artifact paths.
    """
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model service unavailable or artifacts failed to load."
        )
    meta = model_service.get_metrics()
    cost_params = meta.get("cost_parameters", {})
    return RootLandingResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        model_loaded=True,
        model_name=meta.get("model_name", "LogisticRegression"),
        operating_threshold=float(meta.get("optimal_threshold", 0.5)),
        cost_fn=float(cost_params.get("cost_fn", 5.0)),
        cost_fp=float(cost_params.get("cost_fp", 1.0)),
        dataset_rows=int(meta.get("dataset_rows", 25000)),
        model_path="models/best_model.pkl",
        metadata_path="models/model_metadata.json",
        shap_global_path="reports/figures/shap_summary.png",
        features_count=int(meta.get("num_features_raw", 16)),
        message="Vitals API is running successfully"
    )

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check(model_service: ModelService = Depends(get_model_service)):
    """Returns service operational status and confirms loaded model details."""
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model service unavailable or artifacts failed to load."
        )
        
    metadata = model_service.get_metrics()
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_name=metadata.get("model_name", "Unknown"),
        version=metadata.get("version", "1.0.0"),
        operating_threshold=float(metadata.get("optimal_threshold", 0.5))
    )

@app.get("/model/metrics", response_model=MetricsResponse, tags=["Model Info"])
def get_model_metrics(model_service: ModelService = Depends(get_model_service)):
    """Returns evaluation metrics (ROC-AUC, PR-AUC, F1, Recall, Precision, Confusion Matrix) from model_metadata.json."""
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model metadata is unavailable."
        )
    return model_service.get_metrics()

@app.get("/patients", response_model=PaginatedPatientsResponse, tags=["Data"])
def get_paginated_patients(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(15, ge=1, le=100, description="Number of records per page"),
    model_service: ModelService = Depends(get_model_service)
):
    """
    Returns paginated real patient records from data/raw/hospital_readmissions.csv (25,000 records).
    Features only; target 'readmitted' is stripped and stable patient IDs (PT-10001+) are attached.
    """
    try:
        return model_service.get_paginated_patients(page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Error serving paginated patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve paginated patient records: {str(e)}"
        )

@app.get("/sample-patients", response_model=List[Dict[str, Any]], tags=["Data"])
def get_sample_patients(n: int = 15, model_service: ModelService = Depends(get_model_service)):
    """
    Backwards-compatible sample endpoint returning the first n real patient records
    from data/raw/hospital_readmissions.csv for dashboard demonstration.
    """
    try:
        paginated = model_service.get_paginated_patients(page=1, page_size=n)
        return paginated["patients"]
    except Exception as e:
        logger.error(f"Error loading sample patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load sample patients: {str(e)}"
        )

@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_readmission(
    patient: PatientInput,
    model_service: ModelService = Depends(get_model_service)
):
    """
    Accepts one patient's structured clinical data.
    Returns readmission risk probability, clinical risk tier, and top 3 plain-language SHAP drivers.
    """
    try:
        patient_dict = patient.model_dump()
        result = model_service.predict_single(patient_dict)
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing prediction pipeline: {str(e)}"
        )

@app.post("/predict_batch", response_model=BatchPredictionResponse, tags=["Inference"])
async def predict_batch_readmission(
    request: Request,
    file: Optional[UploadFile] = File(None),
    model_service: ModelService = Depends(get_model_service)
):
    """
    Accepts either a CSV file upload or a JSON list of patient records.
    Automatically strips target ('readmitted') or auxiliary ID columns if present before scoring.
    """
    patient_records = []
    
    # 1. Handle CSV File Upload
    if file is not None and file.filename:
        if not file.filename.endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must be a valid CSV format (.csv)"
            )
        try:
            contents = await file.read()
            df_upload = pd.read_csv(io.BytesIO(contents))
            patient_records = df_upload.to_dict(orient="records")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse uploaded CSV file: {str(e)}"
            )
    else:
        # 2. Handle JSON Body Payload
        try:
            body = await request.json()
            if isinstance(body, list):
                patient_records = body
            elif isinstance(body, dict) and "patients" in body:
                patient_records = body["patients"]
            else:
                raise ValueError("Payload must be a JSON array of patient objects or object with 'patients' key.")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid JSON payload for batch prediction: {str(e)}"
            )
            
    if not patient_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No patient records provided in request."
        )
        
    try:
        batch_result = model_service.predict_batch(patient_records)
        return batch_result
    except Exception as e:
        logger.error(f"Batch prediction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing batch predictions: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
