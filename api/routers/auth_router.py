from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_db import User, AuditLog
from api.schemas import LoginRequest, TokenResponse, UserRegisterRequest, UserResponse
from api.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from api.security import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive.")

    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Log audit event
    audit_entry = AuditLog(
        user_id=user.id,
        role=user.role,
        action="LOGIN",
        resource="/api/v1/auth/login",
        status="SUCCESS"
    )
    db.add(audit_entry)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    )

@router.post("/register", response_model=UserResponse)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role.upper(),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/refresh")
def refresh_token(token_str: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(token_str)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type.")
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

        new_access = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
        return {"access_token": new_access, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token refresh failed: {str(e)}")

@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to retrieve all registered platform users."""
    if current_user.role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access user registry."
        )
    return db.query(User).order_by(User.id.asc()).all()

@router.post("/users", response_model=UserResponse)
def admin_create_user(
    payload: UserRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to create Clinician, Analyst, or Admin user accounts."""
    if current_user.role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to create user accounts."
        )

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists."
        )

    role_str = payload.role.upper()
    if role_str not in ["CLINICIAN", "ANALYST", "ADMIN"]:
        role_str = "CLINICIAN"

    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=role_str,
        is_active=True
    )
    db.add(new_user)

    audit_entry = AuditLog(
        user_id=current_user.id,
        role=current_user.role,
        action="USER_CREATE",
        resource=f"/api/v1/auth/users/{payload.email}",
        status="SUCCESS"
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to delete user account."""
    if current_user.role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to delete user accounts."
        )

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own active account."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User account #{user_id} not found."
        )

    user_email = target_user.email
    db.delete(target_user)

    audit_entry = AuditLog(
        user_id=current_user.id,
        role=current_user.role,
        action="USER_DELETE",
        resource=f"/api/v1/auth/users/{user_email}",
        status="SUCCESS"
    )
    db.add(audit_entry)
    db.commit()
    return {"message": f"User account '{user_email}' successfully deleted."}

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit_entry = AuditLog(
        user_id=current_user.id,
        role=current_user.role,
        action="LOGOUT",
        resource="/api/v1/auth/logout",
        status="SUCCESS"
    )
    db.add(audit_entry)
    db.commit()
    return {"message": "Successfully logged out."}

