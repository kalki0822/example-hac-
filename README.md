# Vitals — Hospital Readmission Risk Platform

Vitals is an end-to-end clinical decision-support machine learning platform that predicts 30-day hospital patient readmissions using clinical demographics, prior health system utilization, diagnoses, and inpatient treatment intensity. Trained on the official 25,000-row Kaggle Hospital Readmissions dataset, the system combines cost-sensitive decision threshold optimization with plain-language SHAP explainability drivers, a production FastAPI backend, and an authoritative clinical UI designed for rapid clinician comprehension under time pressure.

---

> [!IMPORTANT]
> **Dataset Provenance & Priority Rule**
> 
> The primary model is trained on the real **Kaggle Hospital Readmissions dataset** (25,000 patient records) supplied by the problem statement and stored at `data/raw/hospital_readmissions.csv`. Synthetic data generation is retained only as a development fallback when the real dataset is unavailable.
> 
> **Kaggle Dataset Source**: [https://www.kaggle.com/datasets/dubradave/hospital-readmissions](https://www.kaggle.com/datasets/dubradave/hospital-readmissions)

> [!WARNING]
> **Clinical Disclaimer**
> 
> This platform is a clinical decision-support prototype designed for risk triage and explainable decision assistance. It does not provide medical diagnoses or replace professional clinical judgment.

---

## 📊 Retrained Model Evaluation Metrics (Stratified 5-Fold CV on 25,000 Real Rows)

| Model Architecture | Out-of-Fold ROC-AUC | Out-of-Fold PR-AUC | F1-Score | Recall (Positive Class) | Operating Cutoff | Avg Cost / Patient |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** *(Winner)* | **0.6474** | **0.6254** | **0.6408** | **99.88%** | **25.62%** | **$0.5286** |
| LightGBM | 0.6532 | 0.6273 | 0.6399 | 99.97% | 12.82% | $0.5295 |
| Random Forest | 0.6395 | 0.6093 | 0.6397 | 100.00% | 6.42% | $0.5296 |

*Note: Operating threshold is selected via cost-sensitive analysis where a missed readmission (False Negative) is parameterized as 5x more costly than an unnecessary intervention ($C_{FN}=5.0, C_{FP}=1.0$).*

---

## 🏗️ System Architecture

```
+-----------------------------------------------------------------------+
|                       CLINICAL USER INTERFACE                         |
|                   React 18 + TypeScript + Vite (:5173)                |
|  - Ward Discharge Overview (Seeded dynamically via /sample-patients)  |
|  - Signature SVG Score Arc Gauge (Compact & Full variants)            |
|  - Patient Detail Drilldown & Plain-Language SHAP Risk Driver Bar     |
|  - Interactive New Patient Intake Assessment Form                     |
|  - Live Model Performance Dashboard (Recharts OOF ROC & Confusion Matrix)|
+-----------------------------------------------------------------------+
                                   |
                             REST API (JSON)
                                   v
+-----------------------------------------------------------------------+
|                          FASTAPI BACKEND SERVICE                      |
|                        Python 3.11 / Uvicorn (:8000)                  |
|  - GET  /health          : Status & model load confirmation            |
|  - GET  /model/metrics   : OOF metrics, ROC points, confusion matrix  |
|  - GET  /sample-patients : Serves real patient rows for Ward Overview |
|  - POST /predict         : Single patient probability & SHAP drivers   |
|  - POST /predict_batch   : Ward JSON & CSV upload scoring             |
+-----------------------------------------------------------------------+
                                   |
                         Inference & Pipelines
                                   v
+-----------------------------------------------------------------------+
|                       SERIALIZED ML ARTIFACTS                         |
|  - models/best_model.pkl (Scikit-Learn ColumnTransformer + Classifier) |
|  - models/model_metadata.json (Metrics, threshold, feature manifest)  |
|  - reports/figures/shap_summary.png (Global SHAP plot)                |
+-----------------------------------------------------------------------+
```

---

## ⚡ Single-Command Execution

Run the complete platform via Docker Compose:

```bash
docker-compose up --build
```

Access the application:
- **Clinical Frontend**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 💡 Key Machine Learning & Architectural Decisions

1. **25,000-Row Real Dataset Training**: All models are trained directly on `data/raw/hospital_readmissions.csv` using Stratified 5-Fold Cross Validation.
2. **Plain-Language SHAP Driver Translation**: Feature codes (e.g. `n_emergency = 2`) are dynamically translated by `api/dependencies.py` into intuitive explanations (*"2 emergency room visit(s) in past year"*).
3. **Cost-Sensitive Decision Threshold Tuning**: Missed readmissions (False Negatives) carry $5\times$ higher cost penalty than unnecessary interventions (False Positives). Optimal cutoff ($25.62\%$) is selected from out-of-fold predictions.
4. **Target Column Safety**: Batch CSV upload (`POST /predict_batch`) automatically detects and drops `readmitted` or ID columns if present before inference.
