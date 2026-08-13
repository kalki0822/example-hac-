import os
import json
import joblib
import argparse
import logging
import pandas as pd
from typing import Dict, Any

# Imports from src package
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.features.build_features import build_features
from src.explainability.shap_utils import explain_single_prediction

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ReadmissionPredictor:
    """
    Inference interface for loading trained Vitals readmission pipeline
    and predicting readmission risk with top SHAP explainability drivers.
    """
    
    def __init__(self, model_path: str = "models/best_model.pkl", metadata_path: str = "models/model_metadata.json"):
        if not os.path.exists(model_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError(
                f"Model artifact ({model_path}) or metadata ({metadata_path}) missing. "
                f"Please run 'python src/models/train.py' first."
            )
            
        logger.info(f"Loading model pipeline from {model_path}...")
        self.pipeline = joblib.load(model_path)
        
        with open(metadata_path, "r") as f:
            self.metadata = json.load(f)
            
        self.threshold = float(self.metadata.get("optimal_threshold", 0.5))
        self.feature_names = self.metadata.get("feature_names_transformed", None)
        logger.info(f"Predictor initialized with optimal cost-sensitive threshold = {self.threshold:.4f}")

    def predict_patient(self, patient_dict: Dict[str, Any], top_n_shap: int = 3) -> Dict[str, Any]:
        """
        Runs prediction for a single patient dictionary.
        Returns probability, binary decision, risk tier, and top N SHAP drivers.
        """
        raw_df = pd.DataFrame([patient_dict])
        
        # 1. Feature Engineering
        X_feat = build_features(raw_df)
        
        # 2. Probability Prediction
        readmission_prob = float(self.pipeline.predict_proba(X_feat)[0, 1])
        is_readmitted = bool(readmission_prob >= self.threshold)
        
        # Risk tier assignment
        if readmission_prob >= 0.70:
            risk_tier = "High Risk"
        elif readmission_prob >= 0.40:
            risk_tier = "Moderate Risk"
        else:
            risk_tier = "Low Risk"
            
        # 3. SHAP Feature Driver Explanation
        try:
            top_drivers = explain_single_prediction(
                self.pipeline,
                X_feat,
                feature_names=self.feature_names,
                top_n=top_n_shap
            )
        except Exception as e:
            logger.warning(f"Failed to generate SHAP drivers: {e}")
            top_drivers = []
            
        return {
            "readmission_probability": round(readmission_prob, 4),
            "predicted_readmitted": "yes" if is_readmitted else "no",
            "operating_threshold": self.threshold,
            "clinical_risk_tier": risk_tier,
            "top_3_shap_drivers": top_drivers
        }

def get_sample_patient() -> Dict[str, Any]:
    """Provides a realistic sample patient record for verification testing."""
    return {
        "age": "[70-80)",
        "time_in_hospital": 6,
        "n_procedures": 2,
        "n_lab_procedures": 55,
        "n_medications": 22,
        "n_outpatient": 1,
        "n_inpatient": 3,
        "n_emergency": 2,
        "medical_specialty": "InternalMedicine",
        "diag_1": "Circulatory",
        "diag_2": "Respiratory",
        "diag_3": "Diabetes",
        "glucose_test": "high",
        "A1Ctest": "high",
        "change": "yes",
        "diabetes_med": "yes"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict hospital readmission risk for a patient.")
    parser.add_argument("--sample", action="store_true", help="Run prediction on a sample patient record.")
    args = parser.parse_args()
    
    predictor = ReadmissionPredictor()
    sample = get_sample_patient()
    
    print("\n" + "="*60)
    print(" PATIENT READMISSION PREDICTION TEST")
    print("="*60)
    print("Sample Input Record:")
    print(json.dumps(sample, indent=2))
    
    result = predictor.predict_patient(sample, top_n_shap=3)
    
    print("\n" + "-"*60)
    print(" PREDICTION OUTPUT & SHAP EXPLANABILITY")
    print("-"*60)
    print(json.dumps(result, indent=2))
    print("="*60 + "\n")
