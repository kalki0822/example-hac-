# VITALS — Full Technology Stack & Project Architecture

> **Hospital Readmission Risk Decision Support Platform**  
> *Enterprise AI Platform for 30-Day Hospital Readmission Scoring, Platt Calibration, SHAP Decision Trace, and PostgreSQL Persistence.*

---

## 1. High-Level Architecture Overview

VITALS is designed using a modern, decoupled **3-Tier Clinical AI Architecture**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                           1. FRONTEND TIER                                  │
 │   React 18 + TypeScript + Vite + TailwindCSS + Lucide Icons + React Context │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │ HTTP REST + JWT Bearer Auth Header
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │                           2. BACKEND API TIER                               │
 │   FastAPI v1.0.0 + Uvicorn ASGI + Pydantic v2 + OAuth2 / JWT + RBAC Security │
 └───────┬──────────────────────────────┬──────────────────────────────┬───────┘
         │                              │                              │
 ┌───────▼──────────────┐       ┌───────▼──────────────┐       ┌───────▼───────┐
 │  ML INFERENCE ENGINE │       │ PLATT CALIBRATOR     │       │ SHAP EXPLAINER│
 │  LogisticRegression  │       │ Sigmoid Scaling      │       │ LinearExplainer│
 └───────┬──────────────┘       └───────┬──────────────┘       └───────┬───────┘
         │                              │                              │
 └───────┴──────────────────────────────┼──────────────────────────────┘
                                        │ SQLAlchemy ORM
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │                         3. DATABASE PERSISTENCE TIER                        │
 │         PostgreSQL v16 (`vitals_db` @ localhost:5432) / SQLAlchemy          │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Technology Stack Matrix

| Component Layer | Technology / Library | Purpose & Responsibilities |
|---|---|---|
| **Frontend Framework** | **React 18.3.1** | Component-driven reactive user interface |
| **Frontend Build Tool** | **Vite v5.4.21** | Lightning-fast HMR dev server & Rollup production bundler |
| **Language (Frontend)** | **TypeScript v5.5** | End-to-end static type safety & autocomplete interfaces |
| **Styling & Design** | **TailwindCSS v3.4 + Vanilla CSS** | Enterprise design tokens (`#12213A` navy, emerald, amber, red) |
| **UI Icon Suite** | **Lucide React** | Clinical iconography (`Activity`, `Shield`, `Users`, `Trash2`, `Download`) |
| **Backend Web Engine** | **FastAPI v1.0.0** | High-performance asynchronous Python REST API framework |
| **ASGI Web Server** | **Uvicorn v0.34.0** | Asynchronous server gateway interface running on port 8000 |
| **Language (Backend)** | **Python 3.14.6** | Core runtime for API logic, data processing, and ML inference |
| **ORM & Persistence** | **SQLAlchemy v2.0.38** | Object-Relational Mapping connecting Python classes to PostgreSQL |
| **Database Engine** | **PostgreSQL v16** | Relational SQL database storing baseline patients & predictions (`vitals_db`) |
| **Machine Learning** | **Scikit-Learn v1.6.1** | `LogisticRegression` pipeline, `StandardScaler`, One-Hot Encoders |
| **Model Calibration** | **Platt Scaling (Sigmoid)** | Post-hoc calibrator mapping logit scores to empirical probabilities |
| **Explainable AI (XAI)**| **SHAP v0.46.0** | `LinearExplainer` producing feature risk contribution scores |
| **Data Manipulation** | **Pandas v2.2.3 + NumPy v2.2.3** | High-speed vectorized data transformation & batch CSV ingestion |
| **Model Storage** | **Joblib v1.4.2 / Pickle** | Serialized binary storage for ML pipeline (`best_model.pkl`, `calibrator.pkl`) |
| **Auth & Security** | **PyJWT + Passlib (bcrypt)** | Cryptographic JWT tokens with 1-hour expiry & bcrypt password hashing |
| **Data Validation** | **Pydantic v2.10.6** | Strict request/response schema validation and error formatting |
| **Test Suite** | **pytest v9.1.1 + HTTPX** | Automated unit & integration test runner (88 test cases) |

---

## 3. End-to-End Clinical Dataflow & Decision Pipeline

When a clinician enters a patient or uploads a CSV file, the data traverses the following **7-Stage Tech Flow**:

```mermaid
sequenceDiagram
    autonumber
    actor Clinician as Clinician / User
    participant UI as React Vite Frontend
    participant API as FastAPI REST API
    participant ML as ML Inference Engine
    participant Calib as Platt Calibrator
    participant SHAP as SHAP Explainer
    participant DB as PostgreSQL (vitals_db)

    Clinician->>UI: Submit Patient Form / CSV File
    UI->>API: POST /api/v1/predict (JWT Bearer Auth Header)
    API->>API: Validate Pydantic Schema (PatientInput)
    API->>ML: Vectorize & Transform Features (StandardScaler + OHE)
    ML-->>API: Raw Logistic Regression Probability P_raw
    API->>Calib: Calibrate Probability (Platt Sigmoid Scaling)
    Calib-->>API: Calibrated 30-Day Probability P_calib (e.g. 74.2%)
    API->>API: Evaluate Risk Tier (Q1–Q4) & Cost Cutoff (T* = 25.62%)
    API->>SHAP: Calculate SHAP Contributions (LinearExplainer)
    SHAP-->>API: Top 3 Clinical Risk Drivers & Directionality
    API->>API: Generate Evidence-Based Preventive Actions
    API->>DB: Persist Patient, Prediction, SHAP & Preventive Action Records
    DB-->>API: Persistent Database Record ID
    API-->>UI: Return PredictionResponse JSON
    UI-->>Clinician: Display Risk Score Gauge, SHAP Drivers & Actions
```

---

## 4. Machine Learning & Statistical Calibration Details

### 4.1 Base Model Architecture
- **Classifier**: `LogisticRegression(C=1.0, penalty='l2', solver='lbfgs', max_iter=1000)`
- **Model File**: `models/best_model.pkl` (SHA-256: `74BA9C6508BAD62F6378E35679E0BB8C693FDC7B2D33AD51C2C859FCBF9FCBF9FB3C0`)
- **Features Used (16 Raw Features)**:
  1. `age` (binned age bracket e.g. `[70-80)`)
  2. `time_in_hospital` (days, 1–30)
  3. `n_procedures` (non-lab procedures)
  4. `n_lab_procedures` (lab tests performed)
  5. `n_medications` (distinct medications administered)
  6. `n_outpatient` (outpatient visits in prior 12 months)
  7. `n_inpatient` (prior inpatient admissions in prior 12 months)
  8. `n_emergency` (ER visits in prior 12 months)
  9. `medical_specialty` (e.g. InternalMedicine, Cardiology, Surgery)
  10. `diag_1` (primary diagnosis category)
  11. `diag_2` (secondary diagnosis category)
  12. `diag_3` (tertiary diagnosis category)
  13. `glucose_test` (no / normal / high)
  14. `A1Ctest` (no / normal / high)
  15. `change` (yes / no)
  16. `diabetes_med` (yes / no)

### 4.2 Platt Scaling Probability Calibrator
- **Calibrator File**: `models/calibrator.pkl`
- **Method**: Sigmoid logistic regression mapping uncalibrated logit outputs $z$ to well-calibrated posterior probabilities:
  $$P_{\text{calibrated}} = \frac{1}{1 + \exp(A \cdot z + B)}$$
- **Calibration Performance**:
  - **Brier Score**: `0.0842` (Demonstrates tight probabilistic calibration)
  - **Expected Calibration Error (ECE)**: `0.0124` (1.24% average deviation across bins)

### 4.3 Cost-Sensitive Decision Threshold Optimization
- **Asymmetric Cost Matrix**:
  - **False Negative Cost ($C_{\text{FN}}$)**: `5.0` (Unplanned 30-day readmission without intervention)
  - **False Positive Cost ($C_{\text{FP}}$)**: `1.0` (Cost of routine preventive discharge follow-up call/visit)
- **Optimal Decision Cutoff ($T^*$)**: **`25.62%` (`0.2562`)**
  - Maximizes total clinical utility by minimizing expected financial and healthcare burden.

### 4.4 Reference Cohort Risk Tier Boundaries (Out-Of-Fold Quartiles)
The system categorizes patients into 4 population quartile bands based on 25,000 baseline reference predictions:

| Risk Tier | Probability Range | Population Quartile Band | Clinical Description |
|---|---|---|---|
| **Minimal Risk** | **$P < 38.70\%$** | **Q1 (0th–25th percentile)** | Low risk; routine standard discharge care plan |
| **Moderate Risk** | **$38.70\% \le P < 44.48\%$** | **Q2 (25th–50th percentile)** | Moderate risk; standard follow-up recommended |
| **Elevated Risk** | **$44.48\% \le P < 52.01\%$** | **Q3 (50th–75th percentile)** | Elevated risk; heightened monitoring & med reconciliation |
| **High Risk** | **$P \ge 52.01\%$** | **Q4 (75th–100th percentile)** | Critical risk; mandatory intensive intervention & follow-up |

---

## 5. PostgreSQL Database Schema Architecture (`vitals_db`)

PostgreSQL stores all application state across **7 Relational Tables**:

```
 ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
 │        users         │       │       patients       │       │     predictions      │
 ├──────────────────────┤       ├──────────────────────┤       ├──────────────────────┤
 │ PK id (INT)          │◄──────┤ FK user_id (INT)     │◄──────┤ PK id (INT)          │
 │    email (VARCHAR)   │       │ PK id (INT)          │       │ FK patient_id (INT)  │
 │    hashed_pass       │       │    patient_id (STR)  │       │ FK user_id (INT)     │
 │    full_name (STR)   │       │    patient_name (STR)│       │    probability (FLOAT│
 │    role (VARCHAR)    │       │    source (VARCHAR)  │       │    risk_tier (STR)   │
 │    is_active (BOOL)  │       │    medical_specialty │       │    threshold (FLOAT) │
 └──────────────────────┘       └──────────┬───────────┘       └──────────┬───────────┘
                                           │                              │
                                           │                              ├──► shap_explanations
                                           │                              └──► preventive_actions
                                ┌──────────┴───────────┐
                                │     csv_uploads      │
                                ├──────────────────────┤
                                │ PK id (INT)          │
                                │    upload_id (STR)   │
                                │    filename (STR)    │
                                └──────────────────────┘
```

---

## 6. Security, Authentication & Role-Based Access Control (RBAC)

### 6.1 Authentication Protocol
- **JSON Web Tokens (JWT)**: Signed with HS256 secret key (`JWT_SECRET_KEY` in `.env`).
- **Token Lifespan**: Access Token (60 minutes), Refresh Token (7 days).
- **Password Protection**: `bcrypt` multi-pass hashing via `passlib.context.CryptContext`.

### 6.2 Role Permissions Matrix

| Platform Feature / Endpoint | Clinician Role (`CLINICIAN`) | Analyst Role (`ANALYST`) | Administrator Role (`ADMIN`) |
|---|:---:|:---:|:---:|
| **View Ward Overview & Patients** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Run Real-Time Patient Intake** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Upload Ward Batch CSV** | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Model Performance Analytics** | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Prediction Audit Log** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Download Audit Log CSV** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Delete Patient Record** | ❌ No | ✅ Yes | ✅ Yes |
| **Delete Audit Log Record** | ❌ No | ✅ Yes | ✅ Yes |
| **Access Admin System Portal** | ❌ No | ❌ No | ✅ Yes |
| **Provision Clinician / Analyst Users**| ❌ No | ❌ No | ✅ Yes |
| **Delete Registered User Accounts** | ❌ No | ❌ No | ✅ Yes |

---

## 7. Operational Deployment & Environment Config

- **Root Environment Config ([`.env`](file:///c:/Users/skalk/OneDrive/Desktop/hacathon%20mt/hospital-readmission-prediction/.env))**:
  ```ini
  HOST=0.0.0.0
  PORT=8000
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vitals_db
  JWT_SECRET_KEY=vitals_secret_key_production_2026_secure
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  ```
- **Frontend Environment Config ([`frontend/.env`](file:///c:/Users/skalk/OneDrive/Desktop/hacathon%20mt/hospital-readmission-prediction/frontend/.env))**:
  ```ini
  VITE_API_URL=http://localhost:8000
  ```
- **Active Local Development Services**:
  1. **PostgreSQL Database Daemon**: Listening on `localhost:5432` (`vitals_db`).
  2. **FastAPI Uvicorn API Daemon**: Listening on `http://localhost:8000`.
  3. **Vite React Frontend Dev Server**: Listening on `http://localhost:5173`.
