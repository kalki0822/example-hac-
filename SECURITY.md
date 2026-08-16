# Security Policy & Hardening Guidelines
**Vitals — Hospital Readmission Risk Decision Support Platform**

## 1. Security Principles
- **No Hardcoded Secrets**: Secrets and JWT keys managed exclusively via environment variables (`JWT_SECRET`, `DATABASE_URL`). `.env` is strictly git-ignored.
- **Password Hashing**: PBKDF2-HMAC-SHA256 with 16-byte random salt per user.
- **Stateless JWT Tokens**: Signed HS256 JWT access tokens with 120-minute expiration.
- **Backend Role Enforcement**: Role-Based Access Control (`require_role(["ADMIN", "CLINICIAN", "ANALYST"])`) enforced at the API dependency layer.
- **SQL Injection Prevention**: All queries routed through SQLAlchemy ORM parameter binding.
- **CORS Protection**: Restricted origins (`http://localhost:5173`, `http://localhost:3000`).
- **File Upload Protection**: CSV size limits and strict extension/schema validation.
- **Audit Trails**: Non-repudiable audit logging for predictions, logins, and system configuration.
