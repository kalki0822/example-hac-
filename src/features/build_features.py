import logging
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
        
        # 1. Utilization Score
        n_inp = df.get("n_inpatient", 0).astype(float)
        n_emerg = df.get("n_emergency", 0).astype(float)
        n_outp = df.get("n_outpatient", 0).astype(float)
        df["utilization_score"] = 3.0 * n_inp + 2.0 * n_emerg + 1.0 * n_outp
        
        # 2. Care Intensity
        n_proc = df.get("n_procedures", 0).astype(float)
        n_lab = df.get("n_lab_procedures", 0).astype(float)
        n_med = df.get("n_medications", 0).astype(float)
        time_stay = np.maximum(df.get("time_in_hospital", 1).astype(float), 1.0)
        df["care_intensity"] = (n_proc + n_lab + n_med) / time_stay
        
        # 3. Diagnosis Risk Tiers
        diag_cols = ["diag_1", "diag_2", "diag_3"]
        available_diag_cols = [col for col in diag_cols if col in df.columns]
        
        def compute_diag_risk(row):
            high_count = 0
            med_count = 0
            for col in available_diag_cols:
                val = str(row[col])
                if any(hr in val for hr in HIGH_RISK_DIAGNOSES):
                    high_count += 1
                elif any(mr in val for mr in MEDIUM_RISK_DIAGNOSES):
                    med_count += 1
            return high_count, med_count

        diag_counts = df.apply(compute_diag_risk, axis=1)
        high_counts = [c[0] for c in diag_counts]
        med_counts = [c[1] for c in diag_counts]
        
        df["diagnosis_risk_score"] = np.array(high_counts) * 2.0 + np.array(med_counts) * 1.0
        
        def assign_risk_bucket(score):
            if score >= 3.0:
                return "High"
            elif score >= 1.0:
                return "Medium"
            else:
                return "Low"
                
        df["diagnosis_risk_bucket"] = df["diagnosis_risk_score"].apply(assign_risk_bucket)
        
        # 4. Age x Utilization Interaction
        if "age" in df.columns:
            age_numeric = df["age"].map(lambda x: AGE_MIDPOINT_MAP.get(str(x), 65.0)).astype(float)
        else:
            age_numeric = 65.0
            
        df["age_utilization_interaction"] = age_numeric * df["utilization_score"]
        
        return df

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience wrapper for feature engineering."""
    fe = FeatureEngineer()
    return fe.transform(df)
