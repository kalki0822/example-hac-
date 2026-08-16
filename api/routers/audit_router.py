from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_db import Prediction, AuditLog
from api.security import require_role

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Trail"])

@router.get("/predictions")
def get_prediction_audit_history(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["ADMIN", "CLINICIAN", "ANALYST"]))
):
    preds = db.query(Prediction).order_by(Prediction.timestamp.desc()).limit(limit).all()
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
