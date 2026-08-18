# VITALS — Comprehensive Technical Flow & ML Model Architecture Guide

---

## 1. Executive System Overview

**VITALS** (Enterprise v1.0) is a production-grade hospital readmission risk prediction and clinical decision-support platform designed for diabetic and complex care patient populations. The system ingests raw clinical intake attributes—either via manual clinician forms, API payloads, or batch CSV uploads—processes them through a canonical feature pipeline, executes inference via a frozen calibrated machine learning model, extracts per-patient SHAP risk drivers, generates prioritized preventive interventions, and persists the result in a PostgreSQL database with an immutable audit log.

---

## 2. End-to-End Technical Flow Architecture

```
[ Clinical Intake ]
  ├─ Manual Form (NewAssessment.tsx)
  ├─ Batch CSV Upload (WardOverview.tsx)
  └─ REST API Payload (predict_router.py)
            │
            ▼
[ Preprocessing & Feature Engineering ] (src/features/build_features.py)
  ├─ Canonical 29 Raw Input Features
  └─ One-Hot & StandardScaler Transformation ──► 67 Transformed Binary/Numeric Features
            │
            ▼
[ Frozen Base Model Inference ] (models/best_model.pkl)
  └─ LogisticRegression Pipeline ──► Raw Readmission Probability (P_raw)
            │
            ▼
[ Platt Scaling Calibration ] (models/calibrator.pkl)
  └─ Sigmoid Logit Transformation ──► Calibrated Probability (P_calibrated)
            │
            ▼
[ Dual Risk Logic Engine ]
  ├─ Stratified Risk Band: Calibrated Reference Quartiles (P25 / P50 / P75)
  │    ├─ Minimal Risk  : P < 0.387042
  │    ├─ Moderate Risk : 0.387042 ≤ P < 0.444758
  │    ├─ Elevated Risk : 0.444758 ≤ P < 0.520089
  │    └─ High Risk     : P ≥ 0.520089
  └─ Operational Decision Cutoff: Cost-Sensitive Minimum (P = 0.2562)
            │
            ▼
[ Explainable AI (SHAP) & Recommendation Engine ] (src/recommendations.py)
  ├─ Top 3 Positive Feature Drivers (SHAP Tree/Linear Explainer)
  └─ Plain-Language Clinical Rules ──► 3–4 Prioritized Action Cards
            │
            ▼
[ Persistence & Audit Layer ] (api/database.py & api/models_db.py)
  ├─ PostgreSQL (vitals_db) ORM Storage (patients, predictions, shap, actions)
  └─ Immutable Security Audit Logs (audit_logs)
            │
            ▼
[ Frontend Presentation Layer ] (React + TypeScript + Vite)
  ├─ Ward Overview (Paginated monitoring table & threshold summary cards)
  ├─ Patient Detail (SVG Radial Gauge, SHAP breakdown & Action cards)
  ├─ Model Performance (ROC, Platt Reliability Diagram, Cost Grid, Model Comparison)
  └─ Prediction Audit Log (Enterprise 8-column audit table)
```

---

## 3. Machine Learning Models Architecture

The platform incorporates primary, calibration, and extended benchmark models stored under `models/`:

### 3.1 Primary Production Base Model (`models/best_model.pkl`)
- **Architecture**: `LogisticRegression` pipeline with `StandardScaler` feature scaling.
- **SHA-256 Checksum**: `74BA9C6508BAD62F6378E35679E0BB8C693FDC7B2D33AD51C2C859FCBF9FB3C0`
- **Training Dataset**: 25,000 Kaggle hospital readmission records (100% full dataset training).
- **Validation Protocol**: Stratified 5-Fold Cross-Validation.
- **Raw Performance Metrics**:
  - **ROC-AUC**: `0.6474`
  - **PR-AUC**: `0.6254`
  - **Positive Recall**: `99.88%`
  - **Positive Precision**: `47.20%`
  - **F1-Score**: `0.6408`
  - **Average Cost per Patient**: `$0.5286` (at optimal cost cutoff)

### 3.2 Platt Scaling Probability Calibrator (`models/calibrator.pkl`)
- **Method**: Sigmoid Platt Scaling fitted on out-of-fold calibration predictions.
- **Mathematical Formula**:
  $$P_{\text{calibrated}} = \frac{1}{1 + \exp(A \cdot z + B)}$$
  where $z = \ln\left(\frac{P_{\text{raw}}}{1 - P_{\text{raw}}}\right)$ (logit of raw logistic regression output).
- **Calibration Improvements**:
  - **Expected Calibration Error (ECE)**: Reduced from **3.23%** (raw) to **1.39%** (calibrated) on untouched holdout test set ($N=3,750$).
  - **Max Calibration Error (MCE)**: Reduced from **10.93%** to **7.56%**.
  - **Brier Score**: `0.2320` (improved probability accuracy).
  - **Log Loss**: `0.6581`.
  - **Calibration Slope / Intercept**: `1.0128` / `+0.005` (Target: $1.00$ / $0.00$).

### 3.3 Candidate Benchmark Models
To evaluate model selection rigor, the platform trained and benchmarked candidate gradient boosting and tree-based architectures:

1. **LightGBM / Gradient Boosting Classifier** (`models/lightgbm_readmission_v1.pkl` & `models/lightgbm_readmission_extended_v1.pkl`):
   - **ROC-AUC**: `0.6512`
   - **PR-AUC**: `0.6261`
   - **Recall**: `99.85%`
   - **Optimal Cost Cutoff**: `18.45%`
   - **Average Cost**: `$0.5291`

2. **Random Forest Classifier**:
   - **ROC-AUC**: `0.6381`
   - **PR-AUC**: `0.6078`
   - **Recall**: `99.92%`
   - **Optimal Cost Cutoff**: `11.34%`
   - **Average Cost**: `$0.5295`

*Selection Rationale*: Logistic Regression was chosen as the primary production winner because it achieved the minimum average patient cost (`$0.5286`), maximum clinical interpretability (direct SHAP coefficient linearity), and robust Platt calibration.

---

## 4. Preprocessing & Feature Engineering Pipeline (`src/features/build_features.py`)

The pipeline standardizes raw clinical attributes into 67 numeric features:

| Feature Category | Raw Features | Transformed Features |
|---|---|---|
| **Demographics** | `age` (age brackets `[0-10)` to `[90-100)`) | One-hot encoded age brackets |
| **Specialty & Diagnosis** | `medical_specialty`, `diag_1`, `diag_2`, `diag_3` | Grouped ICD-9 diagnostic categories & top specialties |
| **Utilization Metrics** | `time_in_hospital`, `n_inpatient`, `n_emergency`, `n_outpatient`, `n_medications`, `n_lab_procedures`, `n_procedures` | Standardized continuous scaling (`StandardScaler`) |
| **Glycemic Control** | `glucose_test`, `A1Ctest`, `change`, `diabetes_med` | Categorical binary & ordinal encoding (`none`, `norm`, `>7`, `>8`, `ch`, `no`) |

---

## 5. Risk Stratification & Cost-Sensitive Analysis

### 5.1 Calibrated Reference Quartile Boundaries
Risk tiers are assigned based on the empirical quartile distribution of the 25,000-patient Kaggle reference cohort evaluated through Platt calibration (`models/calibration_metadata.json`):

$$\begin{aligned}
\text{Minimal Risk}  &: P_{\text{calibrated}} < 0.387042 \quad (< Q_1) \\
\text{Moderate Risk} &: 0.387042 \le P_{\text{calibrated}} < 0.444758 \quad (Q_1 \le P < Q_2) \\
\text{Elevated Risk} &: 0.444758 \le P_{\text{calibrated}} < 0.520089 \quad (Q_2 \le P < Q_3) \\
\text{High Risk}     &: P_{\text{calibrated}} \ge 0.520089 \quad (\ge Q_3)
\end{aligned}$$

### 5.2 Operational Cost-Sensitive Cutoff
- **Cost Parameters**: False Negative (Missed Readmission) = $\$500$ ($5\times$); False Positive (Preventive Intervention) = $\$100$ ($1\times$).
- **Optimal Decision Threshold**: $25.62\%$ ($0.2562$).
- **Operational Purpose**: Determines the binary classification cutoff for trigger alerts, kept strictly distinct from population risk-tier quartile boundaries.

---

## 6. SHAP & Preventive Action Engine (`src/recommendations.py`)

- **SHAP Feature Extraction**: Computes exact linear SHAP contribution values for each feature per patient.
- **Plain-Language Mapping**: Translates raw feature codes into clinical driver statements:
  - `n_inpatient > 0` $\rightarrow$ *"Frequent prior hospital admissions within past 12 months"*
  - `time_in_hospital > 5` $\rightarrow$ *"Extended hospital stay length (>5 days)"*
  - `A1Ctest == '>8'` $\rightarrow$ *"Uncontrolled blood glucose levels (A1C > 8%)"*
- **Action Recommendation Cards**: Generates 3–4 prioritized intervention protocols:
  1. *"Schedule post-discharge primary care follow-up within 7 days"* (High Priority)
  2. *"Pharmacist-led medication reconciliation"* (High/Medium Priority)
  3. *"Home health nurse check-in and disease management protocol"* (Medium Priority)

---

## 7. FastAPI Backend Architecture (`api/`)

Built with Python 3.10+ and FastAPI under a clean modular router layout:

```
api/
├── main.py               # Application entry point, CORS, router mounting
├── dependencies.py       # ModelService singleton loader, database session dependency
├── database.py           # SQLAlchemy engine & PostgreSQL auto-seeding
├── models_db.py          # SQLAlchemy ORM models (Patient, Prediction, AuditLog, etc.)
├── schemas.py             # Pydantic validation schemas
├── security.py            # Password hashing (bcrypt) & JWT token handling
├── auth.py                # OAuth2 Bearer token scheme
└── routers/
    ├── predict_router.py   # POST /predict, POST /predict_batch (JSON & CSV)
    ├── patients_router.py  # GET /patients, GET /patients/{id}, GET /patients/{id}/shap
    ├── audit_router.py     # GET /audit/predictions
    ├── auth_router.py      # POST /auth/login, GET /auth/me
    ├── model_router.py     # GET /model/metrics, GET /model/calibration, GET /model/threshold-analysis
    ├── dashboard_router.py # GET /dashboard/summary
    └── uploads_router.py   # GET /uploads
```

---

## 8. Frontend Component Architecture (`frontend/src/`)

Single-page React 18 application built with TypeScript, Vite, and Tailwind CSS:

- **`WardOverview.tsx`**: Hospital ward dashboard featuring active patient count, risk band summary cards with calibrated threshold labels (`< 38.7%`, `38.7%–44.4%`, `44.5%–52.0%`, `≥ 52.0%`), paginated patient table (15/page), instant search, risk tier filter, source filter, and drag-and-drop CSV batch upload modal.
- **`PatientDetail.tsx`**: Deep-dive patient view with custom SVG radial gauge displaying calibrated readmission probability, top 3 SHAP drivers, and prioritized preventive action cards.
- **`NewAssessment.tsx`**: Interactive clinical intake form containing 17 pre-filled input controls with instant prediction execution.
- **`ModelPerformance.tsx`**: Analytics dashboard rendering ROC curve, 10-bin Platt Reliability Diagram, calibration metrics, cost-sensitive threshold grid, confusion matrix, and candidate model comparison table.
- **`AuditView.tsx`**: Enterprise 8-column prediction audit log table with 4 explicit rendering states (`loading`, `authError 401`, `error`, `empty`).

---

## 9. Database Schema & Persistence (`api/models_db.py`)

Primary database is **PostgreSQL** (`vitals_db` on port 5432) managed via SQLAlchemy 2.0 ORM:

- **`patients`**: Clinical intake attributes, demographics, and source tracking (`KAGGLE`, `MANUAL`, `UPLOADED_CSV`).
- **`predictions`**: Historical predictions storing raw probability, calibrated probability, risk tier, operating threshold, and model version.
- **`shap_explanations`**: SHAP feature driver contributions and plain-language descriptions.
- **`preventive_actions`**: Recommended clinical interventions and priority tags.
- **`csv_uploads`**: Batch CSV file upload metadata (`upload_id`, `filename`, `total_patients`, `uploaded_at`).
- **`audit_logs`**: Immutable audit logs of inference events and user operations.
- **`users`**: Password-hashed RBAC user accounts (`clinician@vitals.health`, `analyst@vitals.health`, `admin@vitals.health`).

---

## 10. Verification Suite & Parity Proof

1. **Golden 10-Patient Parity Test**: `10/10` feature, raw probability, calibrated probability, risk-tier, and API parity (`0.000000000000` delta across pipeline stages).
2. **Precision Boundary Test**: `6/6` boundary test cases passed at $\epsilon = 0.000001$ floating-point offsets around $P_{25} = 0.387042$, $P_{50} = 0.444758$, and $P_{75} = 0.520089$.
3. **Backend Test Suite (`pytest tests/`)**: **88 passed, 0 failed** in 5.83s.
4. **Frontend TypeScript (`npx tsc`)**: **0 errors**.
5. **Frontend Build (`npx vite build`)**: **Built cleanly in 8.38s**.
