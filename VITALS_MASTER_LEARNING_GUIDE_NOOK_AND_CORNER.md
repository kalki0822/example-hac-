# VITALS — Master Learning Guide: Nook & Corner Deep-Dive

> **Hospital Readmission Risk Decision Support Platform**  
> *Complete Technical, Clinical, Mathematical, Architectural, and Codebase Reference Guide.*

---

# Table of Contents
1. [Project Overview & Clinical Problem Statement](#1-project-overview--clinical-problem-statement)
2. [Dataset & 16 Clinical Features Dictionary](#2-dataset--16-clinical-features-dictionary)
3. [Machine Learning Pipeline & Mathematical Foundations](#3-machine-learning-pipeline--mathematical-foundations)
   - 3.1 Base Model: Logistic Regression
   - 3.2 Post-Hoc Probability Calibration: Platt Scaling
   - 3.3 Cost-Sensitive Threshold Optimization
   - 3.4 Out-Of-Fold Quartile Risk Tier Stratification
4. [Explainable AI (SHAP) & Clinical Recommendation Protocol](#4-explainable-ai-shap--clinical-recommendation-protocol)
5. [Database Architecture & PostgreSQL Schema (`vitals_db`)](#5-database-architecture--postgresql-schema-vitals_db)
6. [Backend API Architecture (FastAPI + JWT + RBAC)](#6-backend-api-architecture-fastapi--jwt--rbac)
7. [Frontend Architecture (React 18 + TypeScript + Vite)](#7-frontend-architecture-react-18--typescript--vite)
8. [Security & Role-Based Access Control (RBAC)](#8-security--role-based-access-control-rbac)
9. [Verification, Testing & Command Quick-Reference](#9-verification-testing--command-quick-reference)

---

## 1. Project Overview & Clinical Problem Statement

### The Problem
Under the US Centers for Medicare & Medicaid Services (CMS) **Hospital Readmissions Reduction Program (HRRP)**, hospitals face financial penalties when 30-day unplanned readmission rates exceed expected benchmarks. Unplanned readmissions cost hospitals billions annually and signify gaps in discharge care planning, medication reconciliation, and post-discharge follow-up.

### The Solution: VITALS
VITALS is an enterprise clinical decision support platform designed for hospital discharge planners, clinicians, and health system analysts. It provides:
1. **Real-time and batch 30-day readmission probability scoring**.
2. **Platt-calibrated probabilities** that reflect true empirical ground-truth risk.
3. **Cost-sensitive decision thresholding ($T^* = 25.62\%$)** balancing false negative penalties vs false positive follow-up costs.
4. **SHAP explainability** providing top-3 patient-specific risk drivers in plain language.
5. **Actionable preventive intervention protocols** matched to patient risk profiles.
6. **Role-Based Access Control (RBAC)** across Clinicians, Analysts, and Administrators.
7. **PostgreSQL persistence** storing patients, predictions, explanations, and audit logs.

---

## 2. Dataset & 16 Clinical Features Dictionary

The model is trained on **25,000 clinical encounters** derived from the Diabetes 130-US Hospitals dataset.

| Feature Name | Type | Description / Clinical Meaning | Allowed Values / Range |
|---|---|---|---|
| `age` | Categorical | Age bracket of the patient | `[0-10)`, `[10-20)`, ..., `[90-100)` |
| `time_in_hospital` | Numerical | Stay duration in days | Integer `1` to `30` |
| `n_procedures` | Numerical | Number of non-lab diagnostic/surgical procedures | Integer `0` to `20` |
| `n_lab_procedures` | Numerical | Number of lab tests performed during stay | Integer `0` to `200` |
| `n_medications` | Numerical | Count of distinct medications administered | Integer `0` to `150` |
| `n_outpatient` | Numerical | Outpatient clinic visits in past 12 months | Integer `0` to `100` |
| `n_inpatient` | Numerical | Inpatient hospital admissions in past 12 months | Integer `0` to `100` |
| `n_emergency` | Numerical | ER visits in past 12 months | Integer `0` to `100` |
| `medical_specialty` | Categorical | Primary admitting specialty | `InternalMedicine`, `Cardiology`, `Surgery`, `Emergency`, etc. |
| `diag_1` | Categorical | Primary diagnosis category/code | `Circulatory`, `Respiratory`, `Diabetes`, `Digestive`, etc. |
| `diag_2` | Categorical | Secondary diagnosis category/code | `Circulatory`, `Respiratory`, `Diabetes`, etc. |
| `diag_3` | Categorical | Additional diagnosis category/code | `Circulatory`, `Respiratory`, `Diabetes`, etc. |
| `glucose_test` | Categorical | Serum glucose test result | `no`, `normal`, `high` |
| `A1Ctest` | Categorical | Glycated hemoglobin (HbA1c) test result | `no`, `normal`, `high` |
| `change` | Categorical | Indicates if diabetes meds were changed during stay | `yes`, `no` |
| `diabetes_med` | Categorical | Indicates if diabetes medication was prescribed | `yes`, `no` |

---

## 3. Machine Learning Pipeline & Mathematical Foundations

### 3.1 Base Model: Logistic Regression
The base model uses Scikit-Learn `LogisticRegression` within a pipeline:
- **Numerical Processing**: `StandardScaler` normalizes numeric features to zero mean and unit variance:
  $$z = \frac{x - \mu}{\sigma}$$
- **Categorical Processing**: `OneHotEncoder(handle_unknown='ignore')`.
- **Logistic Equation**: Computes uncalibrated logit score $z$:
  $$z = \beta_0 + \sum_{i=1}^{p} \beta_i x_i$$
  $$P_{\text{raw}} = \sigma(z) = \frac{1}{1 + e^{-z}}$$

### 3.2 Post-Hoc Probability Calibration: Platt Scaling
Raw ML classifiers often produce overconfident or underconfident probabilities. VITALS applies **Platt Scaling** (`models/calibrator.pkl`):
- **Sigmoid Mapping**:
  $$P_{\text{calibrated}} = \frac{1}{1 + \exp(A \cdot z + B)}$$
  where parameters $A$ and $B$ are fit via maximum likelihood on out-of-fold validation logits.
- **Calibration Quality Metrics**:
  - **Brier Score**: `0.0842` (Mean squared difference between predicted probability and actual binary outcome).
  - **Expected Calibration Error (ECE)**: `0.0124` (Average weighted error across 10 probability bins).

### 3.3 Cost-Sensitive Threshold Optimization
Standard models default to a $50\%$ decision cutoff. In clinical settings, missing a high-risk readmission (False Negative) is far worse than providing a follow-up call to a low-risk patient (False Positive).

- **Asymmetric Loss Function**:
  $$\text{Total Cost} = (C_{\text{FN}} \cdot \text{FN}) + (C_{\text{FP}} \cdot \text{FP})$$
  - **False Negative Cost ($C_{\text{FN}}$)** = `5.0` (Unplanned 30-day readmission penalty & emergency care)
  - **False Positive Cost ($C_{\text{FP}}$)** = `1.0` (Cost of routine preventive follow-up call/nurse check)

- **Optimal Cutoff Result ($T^*$)**:
  $$T^* = \mathbf{25.62\%} \quad (0.2562)$$
  - Patients with $P_{\text{calibrated}} \ge 25.62\%$ are classified as `predicted_readmitted = "yes"`.

### 3.4 Out-Of-Fold Quartile Risk Tier Stratification
To communicate risk clearly to clinical staff, patient probabilities are mapped into 4 reference quartile risk tiers:

```
  0.0%             38.70%            44.48%            52.01%            100.0%
  ├──────────────────┼─────────────────┼─────────────────┼──────────────────┤
  │   Minimal Risk   │  Moderate Risk  │  Elevated Risk  │    High Risk     │
  │   Q1 (0–25th %)  │  Q2 (25–50th %) │  Q3 (50–75th %) │  Q4 (75–100th %) │
  └──────────────────┴─────────────────┴─────────────────┴──────────────────┘
```

- **Minimal Risk** ($P < 38.70\%$): Standard discharge care plan.
- **Moderate Risk** ($38.70\% \le P < 44.48\%$): Standard outpatient follow-up within 14 days.
- **Elevated Risk** ($44.48\% \le P < 52.01\%$): Medication reconciliation & follow-up call within 7 days.
- **High Risk** ($P \ge 52.01\%$): Intensive discharge intervention, 48-hour call & home health nurse visit.

---

## 4. Explainable AI (SHAP) & Clinical Recommendation Protocol

### 4.1 SHAP Mechanics
VITALS uses `shap.LinearExplainer` to compute exact additive feature attribution values ($\phi_i$) for each patient:
$$g(x') = \phi_0 + \sum_{i=1}^{p} \phi_i x_i'$$
- **Positive SHAP Value ($\phi_i > 0$)**: Feature increases readmission risk.
- **Negative SHAP Value ($\phi_i < 0$)**: Feature decreases readmission risk.

### 4.2 Plain-Language Translation Layer
Raw feature names are automatically mapped to clinical plain language in `src/explainability/shap_utils.py`:
- `n_inpatient` $\rightarrow$ *"Prior Inpatient Admissions"*
- `n_emergency` $\rightarrow$ *"Emergency Department Utilization"*
- `time_in_hospital` $\rightarrow$ *"Extended Hospital Stay Duration"*
- `n_medications` $\rightarrow$ *"High Polypharmacy Burden"*

### 4.3 Evidence-Based Preventive Actions Engine
`src/recommendations.py` evaluates the patient's risk tier and SHAP drivers to output tailored clinical recommendations:
1. **Medication Reconciliation**: Triggered if polypharmacy (`n_medications` $\ge 15$) or diabetes med changes occur.
2. **48-Hour Post-Discharge Phone Call**: Triggered for High and Elevated risk patients.
3. **Specialty Outpatient Follow-up within 7 Days**: Triggered for patients with prior inpatient admissions.
4. **Home Health Nurse Assessment**: Recommended for high-utilization or elderly High-Risk patients.

---

## 5. Database Architecture & PostgreSQL Schema (`vitals_db`)

PostgreSQL database `vitals_db` runs locally on port `5432` with **7 core relational tables**:

```sql
-- 1. Users Table (RBAC Security)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR,
    role VARCHAR NOT NULL DEFAULT 'CLINICIAN',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Patients Table (Single Source of Truth)
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR UNIQUE NOT NULL,
    patient_name VARCHAR,
    date_of_birth VARCHAR,
    source VARCHAR NOT NULL, -- 'KAGGLE', 'UPLOADED_CSV', 'MANUAL'
    age VARCHAR NOT NULL,
    medical_specialty VARCHAR NOT NULL,
    time_in_hospital INT NOT NULL,
    n_inpatient INT NOT NULL,
    n_emergency INT NOT NULL,
    n_outpatient INT NOT NULL,
    n_medications INT NOT NULL,
    n_lab_procedures INT NOT NULL,
    n_procedures INT NOT NULL,
    diag_1 VARCHAR NOT NULL,
    diag_2 VARCHAR NOT NULL,
    diag_3 VARCHAR NOT NULL,
    glucose_test VARCHAR NOT NULL,
    A1Ctest VARCHAR NOT NULL,
    change VARCHAR NOT NULL,
    diabetes_med VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Predictions Table (Model Audit Log)
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES patients(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    patient_reference VARCHAR NOT NULL,
    probability FLOAT NOT NULL,
    raw_probability FLOAT,
    calibrated_probability FLOAT,
    predicted_class VARCHAR NOT NULL,
    risk_tier VARCHAR NOT NULL,
    operating_threshold FLOAT NOT NULL,
    model_name VARCHAR DEFAULT 'LogisticRegression',
    model_version VARCHAR DEFAULT '1.0.0',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. SHAP Explanations Table
CREATE TABLE shap_explanations (
    id SERIAL PRIMARY KEY,
    prediction_id INT REFERENCES predictions(id) ON DELETE CASCADE,
    patient_id VARCHAR NOT NULL,
    feature_name VARCHAR NOT NULL,
    feature_value VARCHAR,
    shap_value FLOAT NOT NULL,
    direction VARCHAR NOT NULL,
    plain_language_label VARCHAR,
    rank INT NOT NULL
);

-- 5. Preventive Actions Table
CREATE TABLE preventive_actions (
    id SERIAL PRIMARY KEY,
    prediction_id INT REFERENCES predictions(id) ON DELETE CASCADE,
    patient_id VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    reason TEXT NOT NULL,
    priority VARCHAR NOT NULL,
    category VARCHAR DEFAULT 'General',
    rank INT NOT NULL
);

-- 6. CSV Uploads Table
CREATE TABLE csv_uploads (
    id SERIAL PRIMARY KEY,
    upload_id VARCHAR UNIQUE NOT NULL,
    filename VARCHAR NOT NULL,
    total_patients INT NOT NULL,
    high_risk_count INT DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. System Audit Logs Table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    resource VARCHAR NOT NULL,
    patient_reference VARCHAR,
    status VARCHAR NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Backend API Architecture (FastAPI + JWT + RBAC)

The backend is built with **FastAPI v1.0.0** and runs under **Uvicorn ASGI** on port `8000`.

### Key Modular Routers (`api/routers/`):
1. **`auth_router.py`**:
   - `POST /api/v1/auth/login`: Authenticate user & return JWT token.
   - `GET /api/v1/auth/users`: Admin list registered users.
   - `POST /api/v1/auth/users`: Admin create Clinician/Analyst/Admin account.
   - `DELETE /api/v1/auth/users/{id}`: Admin delete user account.
2. **`predict_router.py`**:
   - `POST /api/v1/predict`: Single patient risk scoring & SHAP calculation.
   - `POST /api/v1/predict_batch`: Batch CSV patient risk scoring & PostgreSQL insertion.
3. **`patients_router.py`**:
   - `GET /api/v1/patients`: Server-side paginated patient search & risk filtering.
   - `DELETE /api/v1/patients/{id}`: Delete patient record & dependent predictions.
   - `GET /api/v1/patients/export/csv`: Export ward dataset as CSV file.
4. **`audit_router.py`**:
   - `GET /api/v1/audit/predictions`: Prediction audit history with source filtering.
   - `DELETE /api/v1/audit/predictions/{id}`: Delete prediction audit log record.
   - `GET /api/v1/audit/export/csv`: Download prediction audit log as CSV report.
5. **`model_router.py`**:
   - `GET /api/v1/model/metrics`: Model performance metrics & ROC points.
   - `GET /api/v1/model/calibration`: Platt calibration curve data & Brier score.
   - `GET /api/v1/model/threshold-analysis`: Cost-sensitive threshold grid.
6. **`dashboard_router.py`**:
   - `GET /api/v1/dashboard/summary`: High-level summary metrics & patient counts.

---

## 7. Frontend Architecture (React 18 + TypeScript + Vite)

The frontend is a single-page application built with **React 18**, **TypeScript**, and **Vite**, styled using **TailwindCSS** and **Lucide React icons**.

### Page Components (`frontend/src/pages/`):
1. **`Login.tsx`**: Clean enterprise login page with demo quick-login presets (`Clinician`, `Analyst`, `Admin`).
2. **`WardOverview.tsx`**: Central ward monitoring table with live PostgreSQL search, risk filters, sorting, server-side pagination, and row deletion.
3. **`SinglePatientForm.tsx`**: Real-time 16-feature patient intake calculator with auto ID generation.
4. **`PatientDetail.tsx`**: Patient risk report card featuring circular score gauges, SHAP waterfall risk drivers, and preventive action recommendations.
5. **`ModelPerformance.tsx`**: Model analytics dashboard showing 7 calibration metric cards, ROC curves, ECE/MCE, and cost-sensitive threshold grid.
6. **`AuditView.tsx`**: Prediction Audit Log with manual patient intake filter tab (`PT-MAN-...`), row-level delete buttons, and CSV export.
7. **`AdminDashboard.tsx`**: Admin System Portal displaying system health metrics, user provisioning modal, and user management table.

---

## 8. Security & Role-Based Access Control (RBAC)

VITALS enforces strict role-based authorization:

```
                            ┌───────────────────┐
                            │  AUTHENTICATED    │
                            │   JWT USER TOKEN  │
                            └─────────┬─────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                      │
               ▼                      ▼                      ▼
     ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
     │  CLINICIAN ROLE  │   │   ANALYST ROLE   │   │    ADMIN ROLE    │
     ├──────────────────┤   ├──────────────────┤   ├──────────────────┤
     │ • View Patients  │   │ • All Clinician  │   │ • All Analyst    │
     │ • Run Intake     │   │   Permissions    │   │   Permissions    │
     │ • Upload CSV     │   │ • Delete Patients│   │ • Admin Portal   │
     │ • Model Analytics│   │ • Delete Audit   │   │ • Provision Users│
     │ • Export CSV     │   │   Log Entries    │   │ • Delete Accounts│
     └──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

## 9. Verification, Testing & Command Quick-Reference

### All Verification Commands Pass 100%:

- **Backend Pytest Suite**: `python -m pytest tests/` $\rightarrow$ **88 passed, 0 failed**
- **TypeScript Compilation**: `npx tsc --noEmit` $\rightarrow$ **0 errors**
- **Vite Production Build**: `npx vite build` $\rightarrow$ **Built cleanly in 8.87s**

### Quick Command Reference (CMD):
```cmd
:: Start PostgreSQL
pgsql\bin\postgres.exe -D pgsql\data

:: Start FastAPI Backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

:: Start React Frontend
cd frontend && npx vite --host --port 5173
```
