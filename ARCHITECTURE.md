# System Architecture & Technical Design Blueprint
**Vitals — Hospital Readmission Risk Decision Support Platform**

## 1. High-Level Architecture

Vitals is an enterprise-oriented clinical decision-support application built with a decoupled FastAPI REST backend and React 18 + TypeScript frontend.

```
+-----------------------------------------------------------------------------------+
|                        REACT 18 + TYPESCRIPT FRONTEND (Vite)                      |
|  - Authentication: Login View, Session State, Bearer JWT Auth Context             |
|  - Role Access: Clinician (Ward Overview, Intake), Analyst (Metrics), Admin       |
|  - Visual Identity: Preserved Medical Slate (#F8FAFC), Deep Navy (#12213A), Gauges|
+-----------------------------------------------------------------------------------+
                                         |
                            API Requests (Bearer JWT)
                                         v
+-----------------------------------------------------------------------------------+
|                           FASTAPI ENTERPRISE BACKEND                              |
|  - Versioned API: /api/v1/auth, /api/v1/patients, /api/v1/predict, /api/v1/model   |
|  - Auth & RBAC: JWT Access/Refresh, Passlib/PBKDF2 Hashing, Role Guards          |
|  - Persistence: SQLAlchemy ORM (SQLite for dev, PostgreSQL ready)                 |
|  - Observability: /live, /ready, /health, Audit Trail Logging                     |
+-----------------------------------------------------------------------------------+
                                         |
                    Persistence, Inference & Explainability
                                         v
+-----------------------------------------------------------------------------------+
|                        DATABASE & SERIALIZED ARTIFACTS                            |
|  - Tables: users, roles, patients, predictions, explanations, actions, audit_logs  |
|  - ML Model: models/best_model.pkl (Scikit-Learn Logistic Regression)              |
|  - Metadata: models/model_metadata.json (5-Fold Metrics, Calibration, ROC)        |
|  - Dataset: data/raw/hospital_readmissions.csv (25,000 Kaggle Records)            |
+-----------------------------------------------------------------------------------+
```

## 2. Data Flow & Subsystems

1. **Data Ingestion**: Raw dataset containing 25,000 Kaggle hospital readmission records loaded via `src/data/load_data.py`.
2. **Domain Feature Engineering**: Generates `utilization_score`, `care_intensity`, `diagnosis_risk_score`, `diagnosis_risk_bucket`, `age_utilization_interaction`.
3. **Model Scoring Pipeline**: ColumnTransformer preprocessing + Logistic Regression scoring producing probability `prob \in [0, 1]`.
4. **Cost-Sensitive Thresholding**: Evaluates probability against operating threshold `0.2562` (derived from $C_{FN}=5.0$ vs $C_{FP}=1.0$).
5. **Plain-Language Explainability**: Local SHAP value extraction translated into intuitive clinical statements.
6. **Preventive Recommendations**: Deterministic rule engine converting clinical risk drivers into prioritized actions for clinician consideration.
7. **Audit Trail Persistence**: Operational prediction metadata, SHAP explanations, preventive actions, and user IDs logged to database.

## 3. Database Schema

- `users`: User identity, password hash, role (`ADMIN`, `CLINICIAN`, `ANALYST`).
- `patients`: Patient demographic & clinical history records.
- `predictions`: Logged readmission predictions, operating threshold, risk tier, model version.
- `shap_explanations`: Local feature contributions and plain-language labels.
- `preventive_action_records`: Suggested preventive actions, rationale, priority (`High`, `Medium`, `Routine`).
- `audit_logs`: User activity, requests, actions, resources, status.
- `model_versions`: Model metadata, version strings, training dataset attributes.
