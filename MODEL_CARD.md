# Model Card: Hospital Readmission Risk Estimator v1.0

## Model Details
- **Model Architecture**: Logistic Regression with `ColumnTransformer` (StandardScaler + OneHotEncoder)
- **Model Version**: `1.0.0`
- **Output**: Calibrated 30-day readmission probability $p \in [0, 1]$
- **Operating Threshold**: `0.2562` (25.62%)
- **Cost Parameters**: False Negative cost = 5.0, False Positive cost = 1.0

## Intended Use
- **Primary Objective**: Clinical decision support for identifying high-risk hospital readmission patients prior to discharge.
- **Intended Users**: Healthcare providers, care coordinators, and clinical analysts.
- **Out of Scope**: Autonomous prescribing, automated treatment ordering, or standalone medical diagnosis.

## Training & Evaluation Data
- **Dataset**: Kaggle Hospital Readmissions Dataset (`data/raw/hospital_readmissions.csv`)
- **Dataset Size**: 25,000 records × 17 features
- **Class Distribution**: 52.98% non-readmitted (`0`), 47.02% readmitted (`1`)
- **Validation Method**: Stratified 5-Fold Cross Validation

## Evaluation Metrics (Out-of-Fold)
- **ROC-AUC**: `0.6474`
- **PR-AUC**: `0.6254`
- **Positive Recall**: `99.88%`
- **Positive Precision**: `47.18%`
- **F1-Score**: `0.6408`
- **Brier Score**: `0.2485`
- **Average Cost per Patient**: `$0.5286`
- **Confusion Matrix**: TN = 100, FP = 13,146, FN = 14, TP = 11,740

## Clinical Limitations & Safety
- Model outputs are decision-support suggestions for clinician consideration and are not medical diagnoses.
- Prototype uses de-identified research data and is not connected to live Electronic Health Record (EHR) systems.
