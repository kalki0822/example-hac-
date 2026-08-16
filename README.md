# Vitals — Hospital Readmission Risk Platform
### Cognizant Hackathon — Use Case 2: Predicting Hospital Readmissions

**Vitals** is an enterprise-oriented clinical decision-support platform designed to identify high-risk hospital readmission patients prior to discharge, explain prediction factors via plain-language SHAP drivers, provide patient-specific preventive action recommendations, and maintain complete prediction audit trails.

---

## 🚀 Key Features

1. **25,000-Record Kaggle Dataset Pipeline**: Evaluated on 25,000 real Kaggle hospital readmission records (`data/raw/hospital_readmissions.csv`).
2. **Cost-Sensitive Threshold Optimization**: Tuning operating cutoff at `25.62%` based on clinical cost parameters ($C_{FN}=\$5.0$ vs $C_{FP}=\$1.0$), catching **99.88%** of true readmissions ($0.5286/patient).
3. **Plain-Language SHAP Explainability**: Local feature impacts translated into intuitive clinical statements.
4. **Deterministic Preventive Recommendation Engine**: Rule engine providing prioritized action items for clinician consideration.
5. **Full Dataset Pagination Architecture**: `GET /api/v1/patients?page=1&page_size=15` serving all 25,000 records across 1,667 pages.
6. **Enterprise Authentication & RBAC**: JWT Bearer auth with PBKDF2-HMAC-SHA256 password hashing and role-based permissions (`CLINICIAN`, `ANALYST`, `ADMIN`).
7. **Operational Database Persistence**: SQLAlchemy ORM backing predictions, SHAP explanations, preventive actions, audit logs, and users (SQLite / PostgreSQL).
8. **Probability Calibration & Threshold Analysis**: Monitoring endpoints for Brier score (`0.2485`), calibration curve, and threshold grid analysis ($[0.05, \dots, 0.90]$).
9. **Observability & Health Probes**: `/api/v1/live`, `/api/v1/ready`, `/api/v1/health` probes.

---

## 🛠️ Quickstart

### 1. Run Local Backend & Frontend
```bash
# Terminal 1: Backend API
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Clinical UI
cd frontend
npm install
npx vite --host --port 5173
```

### 2. Hackathon Demo Accounts
- **Clinician**: `clinician@vitals.health` / `Clinician123!` (Ward Overview, Intake, Patient Details)
- **Analyst**: `analyst@vitals.health` / `Analyst123!` (Model Analytics, ROC, PR, Calibration, Threshold Analysis)
- **Admin**: `admin@vitals.health` / `Admin123!` (Admin Portal, System Health, Audit Logs)

---

## 📊 Model Performance Summary (Stratified 5-Fold CV)

| Metric | Out-of-Fold Score |
| :--- | :--- |
| **Model Architecture** | Logistic Regression (`best_model.pkl`) |
| **ROC-AUC Score** | `0.6474` |
| **PR-AUC Score** | `0.6254` |
| **Positive Recall** | `99.88%` (11,740 / 11,754 readmissions caught) |
| **Positive Precision** | `47.18%` |
| **F1-Score** | `0.6408` |
| **Operating Cutoff** | `25.62%` (`0.2562`) |
| **Avg Cost / Patient** | `$0.5286` |
| **Brier Score** | `0.2485` |

---

## 📜 Clinical Disclaimer
*Vitals is a clinical decision-support prototype using de-identified research data. Predictions and recommendations are decision-support suggestions for clinician consideration and are not medical diagnoses or treatment instructions.*
