from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.database import get_db
from api.models_db import Prediction, AuditLog
from api.security import require_role

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Trail"])

@router.get("/predictions")
def get_prediction_audit_history(
    limit: int = Query(100, ge=1, le=500),
    source: Optional[str] = Query("ALL", description="ALL, MANUAL, UPLOADED_CSV, KAGGLE"),
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["ADMIN", "CLINICIAN", "ANALYST"]))
):
    from api.models_db import Patient
    query = db.query(Prediction).order_by(Prediction.timestamp.desc())

    if source and source.upper() == "MANUAL":
        query = query.join(Patient, Prediction.patient_id == Patient.id).filter(
            or_(
                Patient.source == "MANUAL",
                Prediction.patient_reference.ilike("PT-MAN-%")
            )
        )
    elif source and source.upper() != "ALL":
        query = query.join(Patient, Prediction.patient_id == Patient.id).filter(Patient.source == source.upper())

    preds = query.limit(limit).all()
    results = []
    for p in preds:
        prob_val = p.calibrated_probability if p.calibrated_probability is not None else p.probability
        results.append({
            "id": p.id,
            "patient_reference": p.patient_reference,
            "user_id": p.user_id,
            "user_email": p.user.email if p.user else "Clinician / System",
            "probability": round(prob_val, 4) if prob_val is not None else 0.0,
            "predicted_class": p.predicted_class,
            "risk_tier": p.risk_tier,
            "operating_threshold": round(p.operating_threshold, 4) if p.operating_threshold else 0.2562,
            "model_name": p.model_name or "LogisticRegression",
            "model_version": p.model_version or "1.0.0",
            "timestamp": p.timestamp.isoformat() if p.timestamp else "",
            "explanation_count": len(p.explanations),
            "action_count": len(p.preventive_actions)
        })
    return results

@router.delete("/predictions/{prediction_id}")
def delete_prediction_audit_record(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["ADMIN", "CLINICIAN", "ANALYST"]))
):
    """Deletes a prediction audit log record and associated patient if manual intake."""
    from api.models_db import Patient, SHAPExplanation, PreventiveActionRecord

    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prediction record #{prediction_id} not found.")

    patient_db_id = pred.patient_id
    patient_ref = pred.patient_reference

    db.query(SHAPExplanation).filter(SHAPExplanation.prediction_id == prediction_id).delete(synchronize_session=False)
    db.query(PreventiveActionRecord).filter(PreventiveActionRecord.prediction_id == prediction_id).delete(synchronize_session=False)
    db.delete(pred)

    if patient_db_id:
        patient = db.query(Patient).filter(Patient.id == patient_db_id).first()
        if patient and patient.source in ["MANUAL", "UPLOADED_CSV"]:
            other_preds = db.query(Prediction).filter(Prediction.patient_id == patient_db_id).count()
            if other_preds == 0:
                db.delete(patient)

    audit_entry = AuditLog(
        user_id=current_user.id,
        role=current_user.role,
        action="PREDICTION_DELETE",
        resource=f"/api/v1/audit/predictions/{prediction_id}",
        patient_reference=patient_ref,
        status="SUCCESS"
    )
    db.add(audit_entry)
    db.commit()

    return {"message": f"Prediction audit record #{prediction_id} successfully deleted.", "id": prediction_id}

@router.get("/export/csv")
def export_audit_log_csv(
    source: Optional[str] = Query("ALL"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["ADMIN", "CLINICIAN", "ANALYST"]))
):
    """Exports prediction audit log history as downloadable CSV."""
    from fastapi.responses import Response
    from api.models_db import Patient

    query = db.query(Prediction).order_by(Prediction.timestamp.desc())

    if source and source.upper() == "MANUAL":
        query = query.join(Patient, Prediction.patient_id == Patient.id).filter(
            or_(
                Patient.source == "MANUAL",
                Prediction.patient_reference.ilike("PT-MAN-%")
            )
        )
    elif source and source.upper() != "ALL":
        query = query.join(Patient, Prediction.patient_id == Patient.id).filter(Patient.source == source.upper())

    preds = query.limit(limit).all()

    csv_lines = [
        "Prediction ID,Patient Reference,User Email,Calibrated Probability,Risk Tier,Operating Threshold,Model Version,Drivers Count,Actions Count,Timestamp"
    ]

    for p in preds:
        prob_val = p.calibrated_probability if p.calibrated_probability is not None else p.probability
        prob_str = f"{(prob_val * 100):.1f}%"
        user_email = p.user.email if p.user else "Clinician / System"
        thresh_str = f"{(p.operating_threshold * 100):.1f}%"
        time_str = p.timestamp.isoformat() if p.timestamp else ""
        line = f'"{p.id}","{p.patient_reference}","{user_email}","{prob_str}","{p.risk_tier}","{thresh_str}","{p.model_name} v{p.model_version}",{len(p.explanations)},{len(p.preventive_actions)},"{time_str}"'
        csv_lines.append(line)

    csv_content = "\n".join(csv_lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vitals_prediction_audit_log.csv"}
    )


@router.get("/logs")
def get_system_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["ADMIN"]))
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "user_email": l.user.email if l.user else "System",
            "role": l.role,
            "action": l.action,
            "resource": l.resource,
            "patient_reference": l.patient_reference,
            "model_version": l.model_version,
            "status": l.status,
            "timestamp": l.timestamp.isoformat()
        }
        for l in logs
    ]

@router.get("/{prediction_id}")
def get_prediction_audit_detail(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["ADMIN", "CLINICIAN", "ANALYST"]))
):
    p = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction audit record not found.")

    return {
        "id": p.id,
        "patient_reference": p.patient_reference,
        "user": p.user.email if p.user else "Clinician / System",
        "probability": p.probability,
        "predicted_class": p.predicted_class,
        "risk_tier": p.risk_tier,
        "operating_threshold": p.operating_threshold,
        "model_name": p.model_name,
        "model_version": p.model_version,
        "timestamp": p.timestamp.isoformat(),
        "explanations": [
            {
                "feature": e.feature_name,
                "shap_value": e.shap_value,
                "direction": e.direction,
                "plain_language_label": e.plain_language_label
            }
            for e in p.explanations
        ],
        "preventive_actions": [
            {
                "title": a.title,
                "reason": a.reason,
                "priority": a.priority,
                "category": a.category
            }
            for a in p.preventive_actions
        ]
    }
