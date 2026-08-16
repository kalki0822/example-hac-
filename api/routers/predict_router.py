import io
import json
import logging
import hashlib
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from api.database import get_db
from api.models_db import Patient, Prediction, SHAPExplanation, PreventiveActionRecord, AuditLog, CSVUploadRecord
from api.schemas import PatientInput, PredictionResponse, BatchPredictionResponse
from api.dependencies import get_model_service, ModelService, translate_to_plain_language
from api.security import get_current_user_optional as get_optional_current_user
from src.explainability.shap_utils import explain_single_prediction
from src.features.build_features import build_features, build_canonical_model_features

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Inference Engine"])

@router.post("/predict", response_model=PredictionResponse)
def predict_single(
    patient: PatientInput,
    model_service: ModelService = Depends(get_model_service),
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_current_user)
):
    """
    Executes real-time readmission risk evaluation for a single patient record.
    Persists patient, prediction, SHAP drivers, preventive actions, and audit log to DB.
    """
    patient_dict = patient.model_dump()
    
    p_name = patient_dict.get("patient_name") or "Manual Intake Patient"
    p_dob = patient_dict.get("date_of_birth") or "N/A"

    custom_pid = patient_dict.get("patient_id")
    if custom_pid and not db.query(Patient).filter(Patient.patient_id == custom_pid).first():
        p_id = custom_pid
    else:
        max_id = db.query(func.max(Patient.id)).scalar() or 0
        p_id = f"PT-MAN-{(max_id + 1):05d}"

    # Execute ML Inference
    result = model_service.predict_single(patient_dict)
    
    # 1. Create Patient DB Record
    patient_obj = Patient(
        patient_id=p_id,
        patient_name=p_name,
        date_of_birth=p_dob,
        source="MANUAL",
        environment="PRODUCTION",
        age=patient.age,
        medical_specialty=patient.medical_specialty,
        time_in_hospital=patient.time_in_hospital,
        n_inpatient=patient.n_inpatient,
        n_emergency=patient.n_emergency,
        n_outpatient=patient.n_outpatient,
        n_medications=patient.n_medications,
        n_lab_procedures=patient.n_lab_procedures,
        n_procedures=patient.n_procedures,
        diag_1=patient.diag_1,
        diag_2=patient.diag_2,
        diag_3=patient.diag_3,
        glucose_test=patient.glucose_test,
        A1Ctest=patient.A1Ctest,
        change=patient.change,
        diabetes_med=patient.diabetes_med
    )
    db.add(patient_obj)
    db.commit()
    db.refresh(patient_obj)

    # 2. Create Prediction DB Record
    user_id = current_user.id if current_user else None
    pred_obj = Prediction(
        patient_reference=p_id,
        patient_id=patient_obj.id,
        user_id=user_id,
        probability=result["calibrated_readmission_probability"],
        raw_probability=result["raw_readmission_probability"],
        calibrated_probability=result["calibrated_readmission_probability"],
        predicted_class=result["predicted_readmitted"],
        risk_tier=result["clinical_risk_tier"],
        operating_threshold=result["operating_threshold"],
        model_name="LogisticRegression",
        model_version="1.0.0"
    )
    db.add(pred_obj)
    db.commit()
    db.refresh(pred_obj)

    # 3. Create SHAP Driver Records
    for rank_idx, d in enumerate(result["top_3_shap_drivers"], start=1):
        shap_obj = SHAPExplanation(
            prediction_id=pred_obj.id,
            patient_id=p_id,
            feature_name=d["feature"],
            display_label=d.get("feature"),
            feature_value=str(patient_dict.get(d["feature"], "")),
            shap_value=d["shap_value"],
            direction="increases_risk" if d["shap_value"] > 0 else "decreases_risk",
            plain_language_label=d["plain_language_driver"],
            rank=rank_idx
        )
        db.add(shap_obj)

    # 4. Create Preventive Action Records
    for a in result["preventive_actions"]:
        action_obj = PreventiveActionRecord(
            prediction_id=pred_obj.id,
            title=a["title"],
            reason=a["reason"],
            priority=a["priority"]
        )
        db.add(action_obj)

    # 5. Create Audit Log
    user_role = current_user.role if current_user else "CLINICIAN"
    audit_obj = AuditLog(
        user_id=user_id,
        role=user_role,
        action="PREDICTION",
        resource="/api/v1/predict",
        patient_reference=p_id,
        status="SUCCESS"
    )
    db.add(audit_obj)
    db.commit()

    result["prediction_id"] = pred_obj.id
    result["patient_id"] = p_id
    result["patient_name"] = p_name
    result["date_of_birth"] = p_dob
    result["timestamp"] = pred_obj.timestamp.isoformat()
    return result

@router.post("/predict_batch", response_model=BatchPredictionResponse)
async def predict_batch(
    request: Request,
    file: Optional[UploadFile] = File(None),
    model_service: ModelService = Depends(get_model_service),
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_current_user)
):
    """
    Executes batch readmission predictions for CSV upload or JSON list.
    Calculates SHA-256 file hash, deduplicates uploads, and bulk persists Patient, Prediction, SHAP, and Actions in DB.
    """
    patient_records = []
    filename = "vitals_clinical_batch.csv"
    file_bytes = b""

    if file:
        filename = file.filename or "uploaded_patients.csv"
        file_bytes = await file.read()
        df = pd.read_csv(io.BytesIO(file_bytes))
        patient_records = df.to_dict("records")
    else:
        body = await request.json()
        if isinstance(body, list):
            patient_records = body
            file_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, dict) and "patients" in body:
            patient_records = body["patients"]
            file_bytes = json.dumps(body["patients"]).encode("utf-8")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch payload must be a CSV file or JSON array."
            )

    if not patient_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty batch payload provided."
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest() if file_bytes else None
    
    # Deduplication Check: Return existing upload record if exact SHA-256 matches
    if file_hash:
        existing_upload = db.query(CSVUploadRecord).filter(
            CSVUploadRecord.filename == filename,
            CSVUploadRecord.status == "ACTIVE"
        ).first()
        if existing_upload:
            upload_id = existing_upload.upload_id
        else:
            last_upl = db.query(CSVUploadRecord).order_by(desc(CSVUploadRecord.id)).first()
            next_upl_idx = (last_upl.id + 1) if last_upl else 1
            upload_id = f"UP-{next_upl_idx:06d}"
    else:
        last_upl = db.query(CSVUploadRecord).order_by(desc(CSVUploadRecord.id)).first()
        next_upl_idx = (last_upl.id + 1) if last_upl else 1
        upload_id = f"UP-{next_upl_idx:06d}"

    # Execute ML Inference
    result = model_service.predict_batch(patient_records)

    user_id = current_user.id if current_user else None
    user_email = current_user.email if current_user else "Clinician"

    # Save Upload Record if new
    upload_rec = db.query(CSVUploadRecord).filter(CSVUploadRecord.upload_id == upload_id).first()
    if not upload_rec:
        upload_rec = CSVUploadRecord(
            upload_id=upload_id,
            filename=filename,
            total_patients=result["total_patients"],
            high_risk_count=result["high_risk_count"],
            moderate_risk_count=result["moderate_risk_count"],
            low_risk_count=result["low_risk_count"],
            user_id=user_id,
            uploaded_by=user_email,
            status="ACTIVE",
            source_type="UPLOADED_CSV"
        )
        db.add(upload_rec)
        db.commit()

    # Bulk Persist Patients, Predictions, SHAP Explanations, & Preventive Actions
    for idx, (rec, pred_res) in enumerate(zip(patient_records, result["predictions"])):
        p_name = str(rec.get("patient_name") or f"Uploaded Patient #{idx+1}")
        p_dob = str(rec.get("date_of_birth") or "N/A")
        
        # Clean patient_id format: PT-UP-000001-00001
        p_id = f"PT-{upload_id}-{(idx + 1):05d}"

        # Check if patient already exists
        patient_obj = db.query(Patient).filter(Patient.patient_id == p_id).first()
        if not patient_obj:
            patient_obj = Patient(
                patient_id=p_id,
                patient_name=p_name,
                date_of_birth=p_dob,
                source="UPLOADED_CSV",
                upload_id=upload_id,
                source_filename=filename,
                environment="PRODUCTION",
                age=str(rec.get("age", "[50-60)")),
                medical_specialty=str(rec.get("medical_specialty", "Missing")),
                time_in_hospital=int(rec.get("time_in_hospital", 1)),
                n_inpatient=int(rec.get("n_inpatient", 0)),
                n_emergency=int(rec.get("n_emergency", 0)),
                n_outpatient=int(rec.get("n_outpatient", 0)),
                n_medications=int(rec.get("n_medications", 1)),
                n_lab_procedures=int(rec.get("n_lab_procedures", 1)),
                n_procedures=int(rec.get("n_procedures", 0)),
                diag_1=str(rec.get("diag_1", "Other")),
                diag_2=str(rec.get("diag_2", "Other")),
                diag_3=str(rec.get("diag_3", "Other")),
                glucose_test=str(rec.get("glucose_test", "no")),
                A1Ctest=str(rec.get("A1Ctest", "no")),
                change=str(rec.get("change", "no")),
                diabetes_med=str(rec.get("diabetes_med", "no"))
            )
            db.add(patient_obj)
            db.commit()
            db.refresh(patient_obj)

        pred_obj = db.query(Prediction).filter(Prediction.patient_reference == p_id).first()
        if not pred_obj:
            pred_obj = Prediction(
                patient_reference=p_id,
                patient_id=patient_obj.id,
                user_id=user_id,
                probability=pred_res["calibrated_readmission_probability"],
                raw_probability=pred_res["raw_readmission_probability"],
                calibrated_probability=pred_res["calibrated_readmission_probability"],
                predicted_class=pred_res["predicted_readmitted"],
                risk_tier=pred_res["clinical_risk_tier"],
                operating_threshold=model_service.threshold,
                model_name="LogisticRegression",
                model_version="1.0.0"
            )
            db.add(pred_obj)
        else:
            pred_obj.probability = pred_res["calibrated_readmission_probability"]
            pred_obj.raw_probability = pred_res["raw_readmission_probability"]
            pred_obj.calibrated_probability = pred_res["calibrated_readmission_probability"]
            pred_obj.predicted_class = pred_res["predicted_readmitted"]
            pred_obj.risk_tier = pred_res["clinical_risk_tier"]
            pred_obj.operating_threshold = model_service.threshold
            
        db.commit()
        db.refresh(pred_obj)

        # Calculate and Store ALL top 3 SHAP Drivers for this patient
        shap_drivers = pred_res.get("top_3_shap_drivers") or []
        if not shap_drivers:
            # Fallback calculate top 3 SHAP drivers if absent
            X_feat = build_canonical_model_features(rec)
            shap_raw = explain_single_prediction(model_service.pipeline, X_feat, feature_names=model_service.feature_names, top_n=3)
            shap_drivers = [
                {
                    "feature": d["feature"],
                    "shap_value": d["shap_value"],
                    "direction": d["direction"],
                    "plain_language_driver": translate_to_plain_language(d["feature"], rec, d["shap_value"])
                }
                for d in shap_raw
            ]

        for rank_idx, d in enumerate(shap_drivers, start=1):
            shap_obj = SHAPExplanation(
                prediction_id=pred_obj.id,
                patient_id=p_id,
                feature_name=d["feature"],
                display_label=d.get("feature"),
                feature_value=str(rec.get(d["feature"], "")),
                shap_value=d["shap_value"],
                direction="increases_risk" if d["shap_value"] > 0 else "decreases_risk",
                plain_language_label=d["plain_language_driver"],
                rank=rank_idx
            )
            db.add(shap_obj)

        if pred_res.get("preventive_actions"):
            for a in pred_res["preventive_actions"]:
                action_obj = PreventiveActionRecord(
                    prediction_id=pred_obj.id,
                    title=a["title"],
                    reason=a["reason"],
                    priority=a["priority"]
                )
                db.add(action_obj)

        pred_res["patient_id"] = p_id
        pred_res["patient_name"] = p_name
        pred_res["date_of_birth"] = p_dob

    db.commit()

    # Create Audit Log
    user_role = current_user.role if current_user else "CLINICIAN"
    audit_obj = AuditLog(
        user_id=user_id,
        role=user_role,
        action="CSV_UPLOAD",
        resource="/api/v1/predict_batch",
        patient_reference=f"Upload {upload_id} ({result['total_patients']} patients)",
        status="SUCCESS"
    )
    db.add(audit_obj)
    db.commit()

    result["upload_id"] = upload_id
    result["source_filename"] = filename
    return result
