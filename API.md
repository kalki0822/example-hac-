# REST API Documentation
**Vitals — Hospital Readmission Risk Decision Support Platform**

## Base URLs
- **Versioned API**: `/api/v1/`
- **Legacy Compatibility Aliases**: `/`

## Authentication
Protected endpoints require HTTP Bearer JWT token header:
`Authorization: Bearer <access_token>`

### 1. Authentication Endpoints (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Authenticates credentials (`email`, `password`), returns `access_token`, `refresh_token`, `user`.
- `POST /api/v1/auth/register`: Registers new user account.
- `GET /api/v1/auth/me`: Returns profile of current authenticated user.
- `POST /api/v1/auth/refresh`: Refreshes expired access token.
- `POST /api/v1/auth/logout`: Logs out current session.

### 2. Patient Data Endpoints (`/api/v1/patients`)
- `GET /api/v1/patients?page=1&page_size=15`: Returns 15-record paginated slice of real Kaggle patients (`total: 25000`).
- `GET /api/v1/patients/{patient_id}`: Returns specific patient by ID (`PT-10001`+).

### 3. Inference Endpoints (`/api/v1`)
- `POST /api/v1/predict`: Real-time single patient prediction, SHAP drivers, preventive actions, and database audit logging.
- `POST /api/v1/predict_batch`: JSON payload or CSV file batch prediction.

### 4. Model Analytics Endpoints (`/api/v1/model`)
- `GET /api/v1/model/info`: Model metadata, version, dataset size, threshold.
- `GET /api/v1/model/metrics`: Stratified 5-fold cross-validation metrics & ROC points.
- `GET /api/v1/model/calibration`: Calibration curve points & Brier score (**Monitoring only**).
- `GET /api/v1/model/threshold-analysis`: Grid evaluation $[0.05, \dots, 0.90]$ expected cost curve.

### 5. Audit & Admin Endpoints
- `GET /api/v1/audit/predictions`: Retrieves prediction audit history (`ADMIN`, `CLINICIAN`, `ANALYST`).
- `GET /api/v1/dashboard/summary`: System dashboard aggregates.

### 6. Observability Endpoints
- `GET /api/v1/live`: Liveness check.
- `GET /api/v1/ready`: Readiness check.
- `GET /api/v1/health`: Full health check.
