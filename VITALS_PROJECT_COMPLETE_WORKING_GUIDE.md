# VITALS — Hospital Readmission Risk Platform
## Complete End-to-End System & Architecture Working Guide

---

### Executive Overview
**VITALS** is a production-grade enterprise healthcare application designed to predict 30-day hospital readmission risk for diabetic and complex clinical patients. The platform provides real-time clinical decision support, calibrated risk scoring, SHAP (SHapley Additive exPlanations) risk driver analysis, actionable preventive intervention recommendations, batch CSV processing, and an immutable audit trail.

---

## 1. Core ML & Calibration Architecture

### 1.1 Frozen Base Model
- **Algorithm**: `LogisticRegression` pipeline with `StandardScaler` preprocessor.
- **Artifact Path**: `models/best_model.pkl`
- **SHA-256 Hash**: `74BA9C6508BAD62F6378E35679E0BB8C693FDC7B2D33AD51C2C859FCBF9FB3C0`
- **Feature Space**: 29 input features mapped to 67 transformed one-hot encoded binary features.
- **Classes**: `0` = Not Readmitted within 30 days, `1` = Readmitted within 30 days.

### 1.2 Platt Scaling Calibration Pipeline
Raw logistic regression probabilities $P_{\text{raw}}$ are non-linearly mapped to true empirical readmission probabilities $P_{\text{calibrated}}$ using a trained Sigmoid Platt Scaling calibrator (`models/calibrator.pkl`):

$$P_{\text{calibrated}} = \frac{1}{1 + \exp(A \cdot z + B)}$$

where $z = \ln\left(\frac{P_{\text{raw}}}{1 - P_{\text{raw}}}\right)$ (logit transformation of raw model output).

- **Expected Calibration Error (ECE)**: Reduced from **3.23%** (raw) to **1.39%** (calibrated) on untouched holdout test set ($N=3,750$).
- **Max Calibration Error (MCE)**: Reduced from **10.93%** to **7.56%**.
- **Brier Score**: `0.2320`
- **Calibration Slope / Intercept**: `1.0128` / `+0.005`

### 1.3 Reference Cohort Risk-Tier Thresholds
Risk tiers are assigned based on the empirical quartile distribution of the 25,000-patient Kaggle reference cohort evaluated through Platt calibration:

| Risk Tier | Calibrated Probability Range ($P$) | Cohort Percentile |
|---|---|---|
| **Minimal Risk** | $P < 0.387042$ ($38.7042\%$) | Bottom 25% ($< Q_1$) |
| **Moderate Risk** | $0.387042 \le P < 0.444758$ | 25th to 50th Percentile ($Q_1 \le P < Q_2$) |
| **Elevated Risk** | $0.444758 \le P < 0.520089$ | 50th to 75th Percentile ($Q_2 \le P < Q_3$) |
| **High Risk** | $P \ge 0.520089$ ($52.0089\%$) | Top 25% ($\ge Q_3$) |

*Note: All backend comparison operations use full 6-decimal floating-point precision stored in `models/calibration_metadata.json`.*

### 1.4 Operational Cost-Sensitive Threshold vs Risk-Tier Thresholds
- **Cost-Sensitive Decision Cutoff**: $25.62\%$ ($0.2562$).
- **Cost Matrix**: Missed Readmission (False Negative) = $\$500$ ($5\times$); Unnecessary Intervention (False Positive) = $\$100$ ($1\times$).
- **Distinction**: The $25.62\%$ cutoff is an operational decision threshold for binary action triggers, whereas $38.7042\%$, $44.4758\%$, and $52.0089\%$ are population quartile risk-stratification boundaries.

---

## 2. Backend Architecture (FastAPI & Python)

The backend is built with **FastAPI**, structured modularly under `api/`:

```
api/
├── main.py               # Application entry point, CORS, router mounting
├── dependencies.py       # ModelService singleton loader, database session injection
├── database.py           # SQLAlchemy database initialization (SQLite / PostgreSQL)
├── models_db.py          # ORM models (Patient, Prediction, AuditLog, CSVUpload, User)
├── schemas.py             # Pydantic schemas for API request/response validation
├── security.py            # Password hashing (bcrypt) & JWT token generation
├── auth.py                # OAuth2 scheme & current user dependency
└── routers/
    ├── predict_router.py   # POST /predict, POST /predict_batch (JSON & CSV)
    ├── patients_router.py  # GET /patients, GET /patients/{id}, GET /patients/{id}/shap
    ├── audit_router.py     # GET /audit/predictions
    ├── auth_router.py      # POST /auth/login, GET /auth/me
    ├── model_router.py     # GET /model/metrics, GET /model/calibration, GET /model/threshold-analysis
    ├── dashboard_router.py # GET /dashboard/summary
    └── uploads_router.py   # GET /uploads
```

### 2.1 Preprocessing Engine (`src/features/build_features.py`)
Standardizes raw intake or CSV row data into the exact canonical 29-feature structure required by `best_model.pkl`:
- Categorical encoding: `age` brackets (`[0-10)` to `[90-100)`), `medical_specialty`, `diag_1`, `diag_2`, `diag_3`, `glucose_test`, `A1Ctest`, `change`, `diabetes_med`.
- Numeric scaling: `time_in_hospital`, `n_procedures`, `n_lab_procedures`, `n_medications`, `n_outpatient`, `n_inpatient`, `n_emergency`.

### 2.2 Explainable AI (SHAP) & Recommendation Engine (`src/recommendations.py`)
- Calculates exact SHAP values for top positive risk contributors per patient.
- Maps top features to plain-language clinical risk drivers (e.g., `n_inpatient` $\rightarrow$ *"Frequent prior hospital admissions within past 12 months"*).
- Generates 3–4 tailored, prioritized preventive clinical actions (e.g., *"Schedule follow-up appointment within 7 days of discharge"*, *"Pharmacist medication reconciliation"*, *"Home health nurse check-in"*).

---

## 3. Frontend Architecture (React + TypeScript + Vite)

The frontend is a single-page application built with React 18, TypeScript, Vite, and Tailwind CSS under `frontend/src/`:

```
frontend/src/
├── App.tsx               # Main layout, sidebar navigation, client router
├── main.tsx              # Application mount point
├── index.css             # Base styles, typography, custom scrollbars
├── api/
│   └── client.ts         # Centralized API client with JWT bearer authentication
├── context/
│   └── AuthContext.tsx   # React Auth context (login, logout, user session state)
├── components/
│   ├── Nav.tsx           # Top header navigation bar & user profile
│   ├── RoleGuard.tsx     # Route protection component
│   ├── ScoreGauge.tsx    # SVG radial score gauge for calibrated probability
│   ├── PatientRow.tsx    # Table row component for Ward Overview
│   └── RiskDriverBar.tsx # Bar visualization for SHAP feature contributions
├── pages/
│   ├── WardOverview.tsx  # Patient list table, search, filters, risk cards, CSV upload
│   ├── PatientDetail.tsx # Deep-dive patient profile, SHAP drivers, preventive actions
│   ├── NewAssessment.tsx # Manual intake form with 17 clinical fields
│   ├── ModelPerformance.tsx # Analytics dashboard (ROC, Calibration, Cost Curve, Models)
│   ├── AuditView.tsx     # Enterprise 8-column prediction audit log table
│   ├── Login.tsx         # User authentication page
│   └── AdminDashboard.tsx# Platform health & system usage metrics
├── tokens/
│   ├── colors.ts         # Color design system tokens (Minimal, Moderate, Elevated, High)
│   └── typography.ts     # Font family & sizing specifications
└── types/
    └── index.ts          # TypeScript interfaces for API models
```

### 3.1 Key Pages & Components

1. **Ward Overview (`WardOverview.tsx`)**:
   - Displays total active patients and 4 summary cards with exact calibrated risk boundaries (`< 38.7%`, `38.7%–44.4%`, `44.5%–52.0%`, `≥ 52.0%`).
   - Paginated table (15 patients/page) supporting instant text search, risk tier filtering, source filtering (Kaggle vs. Manual vs. CSV Upload), and sorting.
   - Integrated CSV Drag-and-Drop Batch Upload modal with real-time prediction processing.

2. **Patient Detail (`PatientDetail.tsx`)**:
   - Comprehensive profile header with patient demographics and risk badge.
   - Custom SVG radial gauge displaying calibrated readmission probability.
   - Top 3 SHAP Risk Drivers with directional impact indicators.
   - Prioritized Preventive Action Cards with clinical rationale and priority tags.

3. **New Assessment (`NewAssessment.tsx`)**:
   - Interactive manual clinical intake form containing 17 input controls.
   - Pre-filled defaults with realistic clinical values.
   - Form validation triggering instant POST `/api/v1/predict` upon submission, immediately navigating to the generated patient detail view.

4. **Model Performance (`ModelPerformance.tsx`)**:
   - 6 metric cards: ROC-AUC (`0.6474`), PR-AUC (`0.6254`), Recall (`99.9%`), Precision (`47.2%`), F1-Score (`0.6408`), Avg Cost (`$0.53`).
   - Side-by-side charts: Out-of-fold ROC Curve and 10-bin Platt Calibration Reliability Diagram.
   - 7 calibration metric cards: Status (`GOOD`), ECE (`1.39%`), MCE (`7.56%`), Brier (`0.2320`), Log Loss (`0.6581`), Slope (`1.0128`), Intercept (`+0.005`).
   - Full Cost-Sensitive Threshold Analysis table evaluating thresholds $0.05$ to $0.90$.
   - Out-of-fold Confusion Matrix grid ($TN=6,561$, $FP=10,676$, $FN=13$, $TP=7,750$).
   - Candidate Model Comparison table (Logistic Regression vs. Gradient Boosting vs. Random Forest).

5. **Prediction Audit Log (`AuditView.tsx`)**:
   - Enterprise 8-column table: `Prediction ID`, `Patient ID`, `Probability`, `Risk Tier`, `Threshold`, `Model Version`, `Drivers / Actions`, `Timestamp`.
   - Handles 4 explicit state UI rendering paths: `Loading`, `401 Unauthorized Session Expired`, `Error / Retry`, and `Zero Records Empty State`.

---

## 4. Database Schema & Persistence

The platform supports both **SQLite** (`vitals.db`) for local development and **PostgreSQL** for enterprise deployment:

- `patients`: Stores patient demographic & clinical intake attributes (`patient_id`, `age`, `time_in_hospital`, `n_procedures`, etc.).
- `predictions`: Stores historical inference results (`id`, `patient_id`, `raw_probability`, `calibrated_probability`, `clinical_risk_tier`, `operating_threshold`, `model_version`, `created_at`).
- `audit_logs`: Immutable security and operation audit trail.
- `csv_uploads`: File metadata tracking uploaded CSV batches (`upload_id`, `filename`, `total_patients`, `high_risk_count`, `uploaded_at`).
- `users`: User authentication credentials & roles (`id`, `email`, `hashed_password`, `role`).

---

## 5. Verification & Parity Guarantee

### 5.1 Golden 10-Patient Parity Test
Ran 10 deterministic reference patients end-to-end through raw CSV $\rightarrow$ feature builder $\rightarrow$ model $\rightarrow$ Platt calibrator $\rightarrow$ DB $\rightarrow$ API $\rightarrow$ Frontend UI.
- **Result**: `10/10` Feature Parity, `10/10` Raw Prob Parity, `10/10` Calibrated Prob Parity, `10/10` Risk Tier Parity (`0.000000000000` delta).

### 5.2 Precision Boundary Test
Verified boundary assignment at $\epsilon = 0.000001$ floating-point offsets around $P_{25} = 0.387042$, $P_{50} = 0.444758$, and $P_{75} = 0.520089$.
- **Result**: `6/6` boundary test cases passed.

### 5.3 Automated Test Suite
- `pytest tests/`: **88 passed, 0 failed** in 5.83s.
- `npx tsc --noEmit`: **0 errors**.
- `npx vite build`: **Built cleanly in 8.38s**.

---

## 6. How to Run the Project Locally

### Prerequisites
- Python 3.10+
- Node.js 18+

### Step 1: Start Backend API
```bash
# Navigate to project root
cd hospital-readmission-prediction

# Activate virtual environment if configured, or install requirements
pip install -r requirements.txt

# Launch FastAPI uvicorn server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Step 2: Start Frontend App
```bash
# Navigate to frontend directory
cd frontend

# Install node packages if needed
npm install

# Launch Vite dev server
npx vite --host --port 5173
```

Access the application in your browser at `http://localhost:5173`.
