from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_db import User, Patient, Prediction

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard Aggregates"])

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_patients = db.query(Patient).count()
    kaggle_cnt = db.query(Patient).filter(Patient.source == "KAGGLE").count()
    uploaded_cnt = db.query(Patient).filter(Patient.source == "UPLOADED_CSV").count()
    manual_cnt = db.query(Patient).filter(Patient.source == "MANUAL").count()

    total_preds = db.query(Prediction).count()
    high_cnt = db.query(Prediction).filter(Prediction.risk_tier == "High Risk").count()
    mod_cnt = db.query(Prediction).filter(Prediction.risk_tier == "Moderate Risk").count()
    low_cnt = db.query(Prediction).filter(Prediction.risk_tier == "Low Risk").count()
    users_cnt = db.query(User).filter(User.is_active == True).count()

    return {
        "total_patients_dataset": 25000,
        "total_patients_db": total_patients,
        "kaggle_patients_count": kaggle_cnt,
        "uploaded_csv_count": uploaded_cnt,
        "manual_patients_count": manual_cnt,
        "total_predictions_logged": total_preds,
        "high_risk_count": high_cnt,
        "moderate_risk_count": mod_cnt,
        "low_risk_count": low_cnt,
        "active_users_count": users_cnt,
        "model_name": "LogisticRegression",
        "model_version": "1.0.0"
    }

@router.get("/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    high_cnt = db.query(Prediction).filter(Prediction.risk_tier == "High Risk").count()
    mod_cnt = db.query(Prediction).filter(Prediction.risk_tier == "Moderate Risk").count()
    low_cnt = db.query(Prediction).filter(Prediction.risk_tier == "Low Risk").count()
    total = max(1, high_cnt + mod_cnt + low_cnt)

    return {
        "high_risk": {"count": high_cnt, "percentage": round((high_cnt / total) * 100, 1)},
        "moderate_risk": {"count": mod_cnt, "percentage": round((mod_cnt / total) * 100, 1)},
        "low_risk": {"count": low_cnt, "percentage": round((low_cnt / total) * 100, 1)}
    }
