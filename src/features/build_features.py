import re
import logging
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Exact production age midpoint mapping
AGE_MIDPOINT_MAP = {
    "[0-10)": 5.0,
    "[10-20)": 15.0,
    "[20-30)": 25.0,
    "[30-40)": 35.0,
    "[40-50)": 45.0,
    "[50-60)": 55.0,
    "[60-70)": 65.0,
    "[70-80)": 75.0,
    "[80-90)": 85.0,
    "[90-100)": 95.0,
}

HIGH_RISK_DIAGNOSES = {"Circulatory", "Respiratory", "Diabetes"}
MEDIUM_RISK_DIAGNOSES = {"Digestive", "Injury", "Musculoskeletal"}

# Canonical Raw Input Features (Exact Order Required by Preprocessor)
CANONICAL_RAW_FEATURES = [
    "age",
    "time_in_hospital",
    "n_lab_procedures",
    "n_procedures",
    "n_medications",
    "n_outpatient",
    "n_inpatient",
    "n_emergency",
    "medical_specialty",
    "diag_1",
    "diag_2",
    "diag_3",
    "glucose_test",
    "A1Ctest",
    "change",
    "diabetes_med"
]

# Field Name Alias Mapping for Raw CSV / Payload Differences
FIELD_ALIAS_MAP = {
    "number_inpatient": "n_inpatient",
    "inpatient_visits": "n_inpatient",
    "number_emergency": "n_emergency",
    "emergency_visits": "n_emergency",
    "number_outpatient": "n_outpatient",
    "outpatient_visits": "n_outpatient",
    "num_lab_procedures": "n_lab_procedures",
    "lab_procedures": "n_lab_procedures",
    "num_procedures": "n_procedures",
    "procedures": "n_procedures",
    "num_medications": "n_medications",
    "medications": "n_medications",
    "hospital_stay": "time_in_hospital",
    "stay_days": "time_in_hospital",
    "specialty": "medical_specialty",
    "primary_diagnosis": "diag_1",
    "secondary_diagnosis": "diag_2",
    "additional_diagnosis": "diag_3",
    "A1Cresult": "A1Ctest",
    "a1c_test": "A1Ctest",
    "max_glu_serum": "glucose_test",
    "glucose": "glucose_test",
    "diabetesMed": "diabetes_med",
    "change": "change"
}

def normalize_age(val) -> str:
    """Normalizes any age input (numeric, string, unformatted bracket) into exact production age bracket."""
    if val is None or pd.isna(val) or str(val).strip() in ["", "nan", "None", "?", "missing", "Missing"]:
        return "[60-70)"
    s = str(val).strip()
    if s in AGE_MIDPOINT_MAP:
        return s
    numbers = re.findall(r"\d+", s)
    if numbers:
        age_num = float(numbers[0])
        if age_num < 10: return "[0-10)"
        elif age_num < 20: return "[10-20)"
        elif age_num < 30: return "[20-30)"
        elif age_num < 40: return "[30-40)"
        elif age_num < 50: return "[40-50)"
        elif age_num < 60: return "[50-60)"
        elif age_num < 70: return "[60-70)"
        elif age_num < 80: return "[70-80)"
        elif age_num < 90: return "[80-90)"
        else: return "[90-100)"
    return "[60-70)"

def normalize_diagnosis(val) -> str:
    """Normalizes diagnosis text or ICD-9 codes into the 7 training diagnosis categories."""
    if val is None or pd.isna(val) or str(val).strip() in ["", "nan", "None", "?", "missing", "Missing"]:
        return "Missing"
    s = str(val).strip().lower()
    if any(k in s for k in ["circulat", "heart", "cardiac", "vascular", "infarct", "hyperten"]):
        return "Circulatory"
    if any(k in s for k in ["respirat", "lung", "pneumon", "asthma", "copd"]):
        return "Respiratory"
    if any(k in s for k in ["diabet"]):
        return "Diabetes"
    if any(k in s for k in ["digest", "gastro", "stomach", "ulcer", "liver", "bowel"]):
        return "Digestive"
    if any(k in s for k in ["injur", "trauma", "fracture", "poison", "wound"]):
        return "Injury"
    if any(k in s for k in ["muscul", "bone", "joint", "arthr", "spine"]):
        return "Musculoskeletal"
    try:
        code = float(s.split(".")[0])
        if 390 <= code <= 459 or code == 785: return "Circulatory"
        elif 460 <= code <= 519 or code == 786: return "Respiratory"
        elif code == 250: return "Diabetes"
        elif 520 <= code <= 579 or code == 787: return "Digestive"
        elif 800 <= code <= 999: return "Injury"
        elif 710 <= code <= 739: return "Musculoskeletal"
    except (ValueError, TypeError):
        pass
    return "Other"

def normalize_specialty(val) -> str:
    """Normalizes specialty strings into the 7 training specialty categories."""
    if val is None or pd.isna(val) or str(val).strip() in ["", "nan", "None", "?", "missing", "Missing"]:
        return "Missing"
    s = str(val).strip().lower()
    if "cardio" in s: return "Cardiology"
    if "surg" in s: return "Surgery"
    if "emerg" in s or "trauma" in s: return "Emergency/Trauma"
    if "family" in s or "general" in s or "practice" in s: return "Family/GeneralPractice"
    if "internal" in s or "internist" in s: return "InternalMedicine"
    return "Other"

def normalize_glucose(val) -> str:
    if val is None or pd.isna(val) or str(val).strip().lower() in ["", "nan", "none", "?", "no"]:
        return "no"
    s = str(val).strip().lower()
    if "high" in s or ">" in s or "200" in s or "300" in s: return "high"
    if "norm" in s: return "normal"
    return "no"

def normalize_a1c(val) -> str:
    if val is None or pd.isna(val) or str(val).strip().lower() in ["", "nan", "none", "?", "no"]:
        return "no"
    s = str(val).strip().lower()
    if "high" in s or ">" in s or "7" in s or "8" in s: return "high"
    if "norm" in s: return "normal"
    return "no"

def normalize_yes_no(val) -> str:
    if val is None or pd.isna(val): return "no"
    s = str(val).strip().lower()
    if s in ["yes", "true", "1", "ch", "y"]: return "yes"
    return "no"

def safe_int(val, default=0) -> int:
    if val is None or pd.isna(val): return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default

class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Domain-specific feature engineering transformer:
    1. utilization_score: Weighted sum of prior inpatient, emergency, and outpatient visits.
    2. care_intensity: Ratio of procedures, lab tests, and medications to hospital stay duration.
    3. diagnosis_risk_bucket & diagnosis_risk_score: Risk tier categorization from primary/secondary diagnoses.
    4. age_utilization_interaction: Interaction feature between numerical age midpoint and utilization score.
    """
    def __init__(self):
        pass

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        
        n_inp = df["n_inpatient"].astype(float)
        n_emerg = df["n_emergency"].astype(float)
        n_outp = df["n_outpatient"].astype(float)
        df["utilization_score"] = 3.0 * n_inp + 2.0 * n_emerg + 1.0 * n_outp
        
        n_proc = df["n_procedures"].astype(float)
        n_lab = df["n_lab_procedures"].astype(float)
        n_med = df["n_medications"].astype(float)
        time_stay = np.maximum(df["time_in_hospital"].astype(float), 1.0)
        df["care_intensity"] = (n_proc + n_lab + n_med) / time_stay
        
        diag_cols = ["diag_1", "diag_2", "diag_3"]
        def compute_diag_risk(row):
            h, m = 0, 0
            for col in diag_cols:
                val = str(row[col])
                if any(hr in val for hr in HIGH_RISK_DIAGNOSES): h += 1
                elif any(mr in val for mr in MEDIUM_RISK_DIAGNOSES): m += 1
            return h, m

        diag_counts = df.apply(compute_diag_risk, axis=1)
        high_counts = [c[0] for c in diag_counts]
        med_counts = [c[1] for c in diag_counts]
        
        df["diagnosis_risk_score"] = np.array(high_counts) * 2.0 + np.array(med_counts) * 1.0
        df["diagnosis_risk_bucket"] = df["diagnosis_risk_score"].apply(lambda s: "High" if s >= 3.0 else ("Medium" if s >= 1.0 else "Low"))
        
        age_numeric = df["age"].map(lambda x: AGE_MIDPOINT_MAP.get(str(x), 65.0)).astype(float)
        df["age_utilization_interaction"] = age_numeric * df["utilization_score"]
        
        return df

def build_canonical_model_features(raw_input) -> pd.DataFrame:
    """
    CANONICAL FEATURE BUILDER.
    Transforms raw patient input (Kaggle, CSV upload, or Manual intake) into model-ready features.
    Enforces identical field normalization, category mapping, leakage removal, and column ordering across all sources.
    """
    if isinstance(raw_input, pd.DataFrame):
        records = raw_input.to_dict("records")
    elif isinstance(raw_input, list):
        records = raw_input
    elif isinstance(raw_input, dict):
        records = [raw_input]
    else:
        raise ValueError(f"Unsupported raw input type: {type(raw_input)}")

    cleaned_rows = []
    for rec in records:
        # 1. Normalize field names using FIELD_ALIAS_MAP
        norm_rec = {}
        for k, v in rec.items():
            clean_k = FIELD_ALIAS_MAP.get(k, k)
            norm_rec[clean_k] = v

        # 2. Strip target / identifier leakage
        for leak_col in ["readmitted", "target", "outcome", "label", "id", "patient_id", "original_row_index", "upload_id", "source_filename", "risk", "risk_score", "risk_tier", "prediction"]:
            norm_rec.pop(leak_col, None)

        # 3. Canonical feature construction
        row = {
            "age": normalize_age(norm_rec.get("age")),
            "time_in_hospital": max(1, safe_int(norm_rec.get("time_in_hospital"), 1)),
            "n_lab_procedures": max(0, safe_int(norm_rec.get("n_lab_procedures"), 1)),
            "n_procedures": max(0, safe_int(norm_rec.get("n_procedures"), 0)),
            "n_medications": max(0, safe_int(norm_rec.get("n_medications"), 1)),
            "n_outpatient": max(0, safe_int(norm_rec.get("n_outpatient"), 0)),
            "n_inpatient": max(0, safe_int(norm_rec.get("n_inpatient"), 0)),
            "n_emergency": max(0, safe_int(norm_rec.get("n_emergency"), 0)),
            "medical_specialty": normalize_specialty(norm_rec.get("medical_specialty")),
            "diag_1": normalize_diagnosis(norm_rec.get("diag_1")),
            "diag_2": normalize_diagnosis(norm_rec.get("diag_2")),
            "diag_3": normalize_diagnosis(norm_rec.get("diag_3")),
            "glucose_test": normalize_glucose(norm_rec.get("glucose_test")),
            "A1Ctest": normalize_a1c(norm_rec.get("A1Ctest")),
            "change": normalize_yes_no(norm_rec.get("change")),
            "diabetes_med": normalize_yes_no(norm_rec.get("diabetes_med"))
        }
        cleaned_rows.append(row)

    df_raw = pd.DataFrame(cleaned_rows)[CANONICAL_RAW_FEATURES]
    fe = FeatureEngineer()
    return fe.transform(df_raw)

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience wrapper delegating to canonical feature builder."""
    return build_canonical_model_features(df)
