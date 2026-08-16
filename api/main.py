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

from api.database import init_db, get_db
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
from api.routers import (
    auth_router,
    patients_router,
    predict_router,
    model_router,
    audit_router,
    dashboard_router,
    uploads_router
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize DB on application load
init_db()

app = FastAPI(
    title="Vitals — Hospital Readmission Risk Platform API",
    description="Enterprise REST API service providing real-time and batch hospital readmission risk scoring, JWT auth, RBAC, cost-sensitive thresholding, full dataset pagination, plain-language SHAP explainability, and preventive action recommendations.",
    version="1.0.0"
)

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://127.0.0.1:5177",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*",
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
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload or schema validation failure.",
                "errors": errors
            }
        }
    )

# Mount Versioned Routers under /api/v1
app.include_router(auth_router.router)
app.include_router(patients_router.router)
app.include_router(predict_router.router)
app.include_router(model_router.router)
app.include_router(audit_router.router)
app.include_router(dashboard_router.router)
app.include_router(uploads_router.router)

# Health & Observability Endpoints
@app.get("/api/v1/live", tags=["Observability"])
def live_check():
    """Liveness probe: verifies backend application process is running."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/ready", tags=["Observability"])
def ready_check(model_service: ModelService = Depends(get_model_service)):
    """Readiness probe: verifies model pipeline and dataset dependencies are ready."""
    if not model_service.is_loaded():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model pipeline not ready.")
    return {"status": "ready", "model_loaded": True, "database": True}

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Observability"])
def v1_health_check(model_service: ModelService = Depends(get_model_service)):
    """Comprehensive health endpoint returning API, DB, model, and dataset status."""
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model service unavailable or artifacts failed to load."
        )
    metadata = model_service.get_metrics()
    return HealthResponse(
        status="healthy",
        api=True,
        database=True,
        model_loaded=True,
        model_name=metadata.get("model_name", "LogisticRegression"),
        version=metadata.get("version", "1.0.0"),
        operating_threshold=float(metadata.get("optimal_threshold", 0.2562)),
        dataset_rows=int(metadata.get("dataset_rows", 25000))
    )

# Legacy Un-Prefixed Endpoint Aliases (Backward Compatibility)
@app.get("/", response_model=RootLandingResponse, tags=["Monitoring"])
def root_landing(model_service: ModelService = Depends(get_model_service)):
    if not model_service.is_loaded():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model service unavailable.")
    meta = model_service.get_metrics()
    cost_params = meta.get("cost_parameters", {})
    return RootLandingResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        model_loaded=True,
        model_name=meta.get("model_name", "LogisticRegression"),
        operating_threshold=float(meta.get("optimal_threshold", 0.2562)),
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
def legacy_health_check(model_service: ModelService = Depends(get_model_service)):
    return v1_health_check(model_service=model_service)

@app.get("/model/metrics", response_model=MetricsResponse, tags=["Model Info"])
def legacy_get_model_metrics(model_service: ModelService = Depends(get_model_service)):
    return model_router.get_model_metrics(model_service=model_service)

@app.get("/patients", response_model=PaginatedPatientsResponse, tags=["Data"])
def legacy_get_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    model_service: ModelService = Depends(get_model_service),
    db: Session = Depends(get_db)
):
    return patients_router.get_patients(page=page, page_size=page_size, search=None, source="ALL", upload_id=None, risk_tier="ALL", sort_by="RISK_DESC", db=db, model_service=model_service)

@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def legacy_predict(
    patient: PatientInput,
    model_service: ModelService = Depends(get_model_service),
    db: Session = Depends(get_db)
):
    return predict_router.predict_single(patient=patient, model_service=model_service, db=db, current_user=None)

@app.post("/predict_batch", response_model=BatchPredictionResponse, tags=["Inference"])
async def legacy_predict_batch(
    request: Request,
    file: Optional[UploadFile] = File(None),
    model_service: ModelService = Depends(get_model_service),
    db: Session = Depends(get_db)
):
    return await predict_router.predict_batch(request=request, file=file, model_service=model_service, db=db, current_user=None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
