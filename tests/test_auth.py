import pytest
from api.auth import hash_password, verify_password, create_access_token, decode_token
import jwt

def test_password_hashing_and_verification():
    raw_pass = "Clinician123!"
    hashed = hash_password(raw_pass)
    
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_jwt_access_token():
    payload = {"sub": "1", "email": "clinician@vitals.health", "role": "CLINICIAN"}
    token = create_access_token(payload)
    
    assert isinstance(token, str)
    decoded = decode_token(token)
    assert decoded["sub"] == "1"
    assert decoded["email"] == "clinician@vitals.health"
    assert decoded["role"] == "CLINICIAN"
    assert decoded["type"] == "access"
