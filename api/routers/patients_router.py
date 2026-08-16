from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, func

from api.database import get_db
from api.models_db import Patient, Prediction, SHAPExplanation, CSVUploadRecord
from api.schemas import PaginatedPatientsResponse
from api.dependencies import get_model_service, ModelService

router = APIRouter(prefix="/api/v1/patients", tags=["Patient Data"])

@router.get("", response_model=PaginatedPatientsResponse)
def get_patients(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(15, ge=1, le=500, description="Records per page"),
    search: Optional[str] = Query(None, description="Global search term across ID, Name, DOB, Specialty, Diagnoses, Risk Tier, Source, CSV Filename"),
    source: Optional[str] = Query("ALL", description="Source filter: ALL, KAGGLE, UPLOADED_CSV, MANUAL"),
    upload_id: Optional[str] = Query(None, description="Filter patients by specific CSV upload_id"),
    risk_tier: Optional[str] = Query("ALL", description="Risk filter: ALL, High Risk, Moderate Risk, Low Risk"),
    sort_by: Optional[str] = Query("RISK_DESC", description="RISK_DESC, RISK_ASC, STAY_DESC, STAY_ASC, NEWEST, OLDEST"),
    db: Session = Depends(get_db),
    model_service: ModelService = Depends(get_model_service)
):
    # Base Query joining Patient with Prediction
    query = db.query(Patient, Prediction).join(Prediction, Prediction.patient_id == Patient.id)

    # 1. Source Filter
    if source and source.upper() != "ALL":
        query = query.filter(Patient.source == source.upper())

    # 2. Upload ID Filter
    if upload_id:
        query = query.filter(Patient.upload_id == upload_id)

    # 3. Risk Tier Filter
    if risk_tier and risk_tier.upper() != "ALL":
        r_up = risk_tier.upper()
        if "HIGH" in r_up:
            rt_norm = "High Risk"
        elif "ELEVATED" in r_up:
            rt_norm = "Elevated Risk"
        elif "MODERATE" in r_up:
            rt_norm = "Moderate Risk"
        else:
            rt_norm = "Minimal Risk"
        query = query.filter(Prediction.risk_tier == rt_norm)

    # 4. Global Search Filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.patient_id.ilike(term),
                Patient.patient_name.ilike(term),
                Patient.date_of_birth.ilike(term),
                Patient.medical_specialty.ilike(term),
                Patient.diag_1.ilike(term),
                Patient.diag_2.ilike(term),
                Patient.diag_3.ilike(term),
                Patient.source.ilike(term),
                Patient.source_filename.ilike(term),
                Prediction.risk_tier.ilike(term)
            )
        )

    # 5. Global Risk Aggregates for active filter set
    total_matching = query.count()

    high_cnt = query.filter(Prediction.risk_tier == "High Risk").count()
    elevated_cnt = query.filter(Prediction.risk_tier == "Elevated Risk").count()
    mod_cnt = query.filter(Prediction.risk_tier == "Moderate Risk").count()
    minimal_cnt = query.filter(Prediction.risk_tier == "Minimal Risk").count()
    low_cnt = query.filter(Prediction.risk_tier == "Low Risk").count() + minimal_cnt

    total_pages = max(1, (total_matching + page_size - 1) // page_size)
    req_page = max(1, min(page, total_pages))
    offset = (req_page - 1) * page_size

    # 6. Global Sorting
    sort_upper = sort_by.upper() if sort_by else "ID_ASC"
    if sort_upper == "RISK_DESC":
        query = query.order_by(desc(Prediction.probability), asc(Patient.id))
    elif sort_upper == "RISK_ASC":
        query = query.order_by(asc(Prediction.probability), asc(Patient.id))
    elif sort_upper == "STAY_DESC":
        query = query.order_by(desc(Patient.time_in_hospital), asc(Patient.id))
    elif sort_upper == "STAY_ASC":
        query = query.order_by(asc(Patient.time_in_hospital), asc(Patient.id))
    elif sort_upper == "NEWEST" or sort_upper == "ID_DESC":
        query = query.order_by(desc(Patient.id))
    else:  # ID_ASC / DEFAULT / OLDEST
        query = query.order_by(asc(Patient.id))

    # 7. Apply Offset and Limit
    rows = query.offset(offset).limit(page_size).all()

    patient_records = []
    for p, pred in rows:
        p_dict = {
            "patient_id": p.patient_id,
            "patient_name": p.patient_name or "N/A",
            "date_of_birth": p.date_of_birth or "N/A",
            "source": p.source,
            "upload_id": p.upload_id,
            "source_filename": p.source_filename,
            "environment": p.environment,
            "age": p.age,
            "medical_specialty": p.medical_specialty,
            "time_in_hospital": p.time_in_hospital,
            "n_inpatient": p.n_inpatient,
            "n_emergency": p.n_emergency,
            "n_outpatient": p.n_outpatient,
            "n_medications": p.n_medications,
            "n_lab_procedures": p.n_lab_procedures,
            "n_procedures": p.n_procedures,
            "diag_1": p.diag_1,
            "diag_2": p.diag_2,
            "diag_3": p.diag_3,
            "glucose_test": p.glucose_test,
            "A1Ctest": p.A1Ctest,
            "change": p.change,
            "diabetes_med": p.diabetes_med,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "readmission_probability": pred.probability,
            "predicted_readmitted": pred.predicted_class,
            "clinical_risk_tier": pred.risk_tier,
            "operating_threshold": pred.operating_threshold,
            "latest_prediction": {
                "id": pred.id,
                "readmission_probability": pred.probability,
                "predicted_readmitted": pred.predicted_class,
                "risk_tier": pred.risk_tier,
                "operating_threshold": pred.operating_threshold,
                "model_name": pred.model_name,
                "timestamp": pred.timestamp.isoformat() if pred.timestamp else None
            }
        }
        patient_records.append(p_dict)

    return PaginatedPatientsResponse(
        patients=patient_records,
        total=total_matching,
        page=req_page,
        page_size=page_size,
        total_pages=total_pages,
        minimal_risk_count=minimal_cnt,
        moderate_risk_count=mod_cnt,
        elevated_risk_count=elevated_cnt,
        high_risk_count=high_cnt,
        low_risk_count=low_cnt
    )

@router.get("/{patient_id}")
def get_patient_by_id(
    patient_id: str,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient and patient_id.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(patient_id)).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient record '{patient_id}' not found in database."
        )

    preds = db.query(Prediction).filter(Prediction.patient_reference == patient.patient_id).order_by(desc(Prediction.timestamp)).all()
    
    return {
        "patient_id": patient.patient_id,
        "patient_name": patient.patient_name or "N/A",
        "date_of_birth": patient.date_of_birth or "N/A",
        "source": patient.source,
        "upload_id": patient.upload_id,
        "source_filename": patient.source_filename,
        "environment": patient.environment,
        "age": patient.age,
        "medical_specialty": patient.medical_specialty,
        "time_in_hospital": patient.time_in_hospital,
        "n_inpatient": patient.n_inpatient,
        "n_emergency": patient.n_emergency,
        "n_outpatient": patient.n_outpatient,
        "n_medications": patient.n_medications,
        "n_lab_procedures": patient.n_lab_procedures,
        "n_procedures": patient.n_procedures,
        "diag_1": patient.diag_1,
        "diag_2": patient.diag_2,
        "diag_3": patient.diag_3,
        "glucose_test": patient.glucose_test,
        "A1Ctest": patient.A1Ctest,
        "change": patient.change,
        "diabetes_med": patient.diabetes_med,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "prediction_history": [
            {
                "id": pr.id,
                "probability": pr.probability,
                "risk_tier": pr.risk_tier,
                "predicted_readmitted": pr.predicted_class,
                "operating_threshold": pr.operating_threshold,
                "timestamp": pr.timestamp.isoformat(),
                "explanations": [
                    {
                        "feature": e.feature_name,
                        "shap_value": e.shap_value,
                        "direction": e.direction,
                        "plain_language_label": e.plain_language_label
                    }
                    for e in pr.explanations
                ],
                "preventive_actions": [
                    {
                        "title": a.title,
                        "reason": a.reason,
                        "priority": a.priority
                    }
                    for a in pr.preventive_actions
                ]
            }
            for pr in preds
        ]
    }

@router.get("/{patient_id}/shap")
def get_patient_shap(
    patient_id: str,
    db: Session = Depends(get_db),
    model_service: ModelService = Depends(get_model_service)
):
    """
    Returns real, patient-specific SHAP drivers mapped back to clinical features.
    Persists SHAP driver records to PostgreSQL.
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient and patient_id.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(patient_id)).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient record '{patient_id}' not found in PostgreSQL database."
        )

    pred = db.query(Prediction).filter(Prediction.patient_reference == patient.patient_id).order_by(desc(Prediction.timestamp)).first()
    
    drivers = []
    if pred and pred.explanations and len(pred.explanations) >= 3:
        for ex in pred.explanations:
            drivers.append({
                "feature": ex.feature_name,
                "label": ex.plain_language_label or ex.display_label or ex.feature_name,
                "value": ex.feature_value or getattr(patient, ex.feature_name, "Confirmed"),
                "shap_value": ex.shap_value,
                "impact": ex.direction if ex.direction in ["increases_risk", "decreases_risk"] else ("increases_risk" if ex.shap_value > 0 else "decreases_risk")
            })

    if not drivers:
        if pred and pred.explanations:
            db.query(SHAPExplanation).filter(SHAPExplanation.prediction_id == pred.id).delete(synchronize_session=False)
            db.commit()

        p_dict = {
            "age": patient.age,
            "medical_specialty": patient.medical_specialty,
            "time_in_hospital": patient.time_in_hospital,
            "n_inpatient": patient.n_inpatient,
            "n_emergency": patient.n_emergency,
            "n_outpatient": patient.n_outpatient,
            "n_medications": patient.n_medications,
            "n_lab_procedures": patient.n_lab_procedures,
            "n_procedures": patient.n_procedures,
            "diag_1": patient.diag_1,
            "diag_2": patient.diag_2,
            "diag_3": patient.diag_3,
            "glucose_test": patient.glucose_test,
            "A1Ctest": patient.A1Ctest,
            "change": patient.change,
            "diabetes_med": patient.diabetes_med
        }
        res = model_service.predict_single(p_dict)
        for rank_idx, d in enumerate(res["top_3_shap_drivers"], start=1):
            val_str = str(p_dict.get(d["feature"], "Confirmed"))
            drivers.append({
                "feature": d["feature"],
                "label": d["plain_language_driver"],
                "value": val_str if val_str else "Confirmed",
                "shap_value": d["shap_value"],
                "impact": "increases_risk" if d["shap_value"] > 0 else "decreases_risk"
            })
            if pred:
                shap_obj = SHAPExplanation(
                    prediction_id=pred.id,
                    patient_id=patient.patient_id,
                    feature_name=d["feature"],
                    display_label=d["feature"],
                    feature_value=val_str,
                    shap_value=d["shap_value"],
                    direction="increases_risk" if d["shap_value"] > 0 else "decreases_risk",
                    plain_language_label=d["plain_language_driver"],
                    rank=rank_idx
                )
                db.add(shap_obj)
        if pred:
            db.commit()

    return {
        "patient_id": patient.patient_id,
        "drivers": drivers
    }
