from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from api.database import get_db
from api.models_db import CSVUploadRecord
from api.schemas import CSVUploadResponse

router = APIRouter(prefix="/api/v1/uploads", tags=["CSV Uploads"])

@router.get("", response_model=List[CSVUploadResponse])
def get_uploaded_files(db: Session = Depends(get_db)):
    """Returns registry of all active user-uploaded CSV datasets dynamically from database."""
    uploads = db.query(CSVUploadRecord).filter(
        CSVUploadRecord.status == "ACTIVE"
    ).order_by(desc(CSVUploadRecord.uploaded_at)).all()

    results = []
    for u in uploads:
        results.append(CSVUploadResponse(
            upload_id=u.upload_id,
            filename=u.filename,
            total_patients=u.total_patients,
            high_risk_count=u.high_risk_count,
            moderate_risk_count=u.moderate_risk_count,
            low_risk_count=u.low_risk_count,
            uploaded_at=u.uploaded_at.isoformat(),
            user_email=u.user.email if u.user else (u.uploaded_by or "Clinician")
        ))
    return results

@router.get("/{upload_id}", response_model=CSVUploadResponse)
def get_upload_by_id(upload_id: str, db: Session = Depends(get_db)):
    u = db.query(CSVUploadRecord).filter(
        CSVUploadRecord.upload_id == upload_id,
        CSVUploadRecord.status == "ACTIVE"
    ).first()
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload record '{upload_id}' not found."
        )
    return CSVUploadResponse(
        upload_id=u.upload_id,
        filename=u.filename,
        total_patients=u.total_patients,
        high_risk_count=u.high_risk_count,
        moderate_risk_count=u.moderate_risk_count,
        low_risk_count=u.low_risk_count,
        uploaded_at=u.uploaded_at.isoformat(),
        user_email=u.user.email if u.user else (u.uploaded_by or "Clinician")
    )
