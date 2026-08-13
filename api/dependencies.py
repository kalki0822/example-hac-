import os
import json
import joblib
import math
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.build_features import build_features
from src.explainability.shap_utils import explain_single_prediction
from src.data.load_data import load_raw_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FEATURE_HUMAN_DESCRIPTIONS = {
    "utilization_score": "High health system utilization (weighted prior admissions & ER visits)",
    "care_intensity": "High care intensity (treatments per hospital stay day)",
    "diagnosis_risk_score": "Multiple high-risk diagnostic classifications",
    "diagnosis_risk_bucket_High": "High-risk diagnostic classification (Circulatory/Respiratory/Diabetes)",
    "diagnosis_risk_bucket_Medium": "Medium-risk diagnostic classification",
    "diagnosis_risk_bucket_Low": "Low-risk diagnostic classification",
    "n_emergency": "Emergency room visits in past year",
    "n_inpatient": "Prior inpatient admissions in past year",
    "n_outpatient": "Outpatient clinic visits in past year",
    "n_medications": "Number of prescribed medications during stay",
    "time_in_hospital": "Hospital stay duration (days)",
    "n_lab_procedures": "Number of lab procedures performed",
    "n_procedures": "Number of non-lab procedures performed",
    "age_utilization_interaction": "Combined risk of advanced age and prior health system utilization",
    "diag_1_Circulatory": "Primary diagnosis of Circulatory condition",
    "diag_1_Respiratory": "Primary diagnosis of Respiratory condition",
    "diag_1_Diabetes": "Primary diagnosis of Diabetes",
    "diag_1_Digestive": "Primary diagnosis of Digestive condition",
    "diag_1_Injury": "Primary diagnosis of Injury",
    "diag_2_Circulatory": "Secondary diagnosis of Circulatory condition",
    "diag_2_Respiratory": "Secondary diagnosis of Respiratory condition",
    "diag_2_Diabetes": "Secondary diagnosis of Diabetes",
    "diag_3_Circulatory": "Comorbid diagnosis of Circulatory condition",
    "diag_3_Respiratory": "Comorbid diagnosis of Respiratory condition",
    "diag_3_Diabetes": "Comorbid diagnosis of Diabetes",
    "glucose_test_high": "Elevated serum glucose test result",
    "glucose_test_no": "No serum glucose test ordered",
    "A1Ctest_high": "Elevated HbA1c test result (>8%)",
    "A1Ctest_no": "No HbA1c test ordered",
    "diabetes_med_yes": "Prescribed diabetes medication",
    "change_yes": "Recent adjustment to diabetes medication dosage",
    "medical_specialty_Cardiology": "Admitted under Cardiology specialty",
    "medical_specialty_InternalMedicine": "Admitted under Internal Medicine specialty",
    "medical_specialty_Emergency/Trauma": "Admitted via Emergency/Trauma specialty",
    "medical_specialty_Surgery": "Admitted under Surgical specialty"
}

def translate_to_plain_language(feature_name: str, patient_dict: Dict[str, Any], shap_val: float) -> str:
    """
    Translates raw/transformed feature name and patient attribute into an intuitive,
    plain-language clinical label.
    """
    clean_feature = feature_name.replace("cat__", "").replace("num__", "")
    
    if clean_feature == "n_emergency":
        val = patient_dict.get("n_emergency", "")
        return f"{val} emergency room visit(s) in past year" if val != "" else "Emergency room visits in past year"
    elif clean_feature == "n_inpatient":
        val = patient_dict.get("n_inpatient", "")
        return f"{val} prior inpatient admission(s) in past year" if val != "" else "Prior inpatient admissions in past year"
    elif clean_feature == "n_outpatient":
        val = patient_dict.get("n_outpatient", "")
        return f"{val} outpatient visit(s) in past year" if val != "" else "Outpatient visits in past year"
    elif clean_feature == "n_medications":
        val = patient_dict.get("n_medications", "")
        return f"{val} prescribed medication(s) during stay" if val != "" else "High prescribed medication count"
    elif clean_feature == "time_in_hospital":
        val = patient_dict.get("time_in_hospital", "")
        return f"{val} day(s) hospital stay length" if val != "" else "Hospital stay length"
    elif clean_feature.startswith("age_"):
        val = patient_dict.get("age", clean_feature.replace("age_", ""))
        return f"Patient age bracket {val}"
        
    if clean_feature in FEATURE_HUMAN_DESCRIPTIONS:
        return FEATURE_HUMAN_DESCRIPTIONS[clean_feature]
        
    for key, human_label in FEATURE_HUMAN_DESCRIPTIONS.items():
        if clean_feature.startswith(key):
            return human_label
            
    readable_name = clean_feature.replace("_", " ").title()
    return f"{readable_name} clinical factor"

class ModelService:
    """
    Singleton model inference service managing model pipeline loading,
    predictions, metadata retrieval, dataset pagination, and SHAP driver translations.
    """
    def __init__(self, model_path: str = "models/best_model.pkl", metadata_path: str = "models/model_metadata.json"):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.pipeline = None
        self.metadata = {}
        self.threshold = 0.5
        self.feature_names = []
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.metadata_path):
            logger.error(f"Model file ({self.model_path}) or metadata ({self.metadata_path}) not found!")
            raise FileNotFoundError("Trained model artifacts missing.")
            
        logger.info(f"Loading trained pipeline from {self.model_path}...")
        self.pipeline = joblib.load(self.model_path)
        
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)
            
        self.threshold = float(self.metadata.get("optimal_threshold", 0.5))
        self.feature_names = self.metadata.get("feature_names_transformed", [])
        logger.info(f"Model service initialized with real-data model. Operating threshold = {self.threshold:.4f}")

    def is_loaded(self) -> bool:
        return self.pipeline is not None and bool(self.metadata)

    def get_metrics(self) -> Dict[str, Any]:
        return self.metadata

    def get_paginated_patients(self, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """
        Reads real patient records from data/raw/hospital_readmissions.csv,
        applies pagination bounds, attaches stable row-based patient IDs (e.g. PT-10001),
        and strips the target 'readmitted' column.
        """
        raw_df = load_raw_data()
        total_records = len(raw_df)
        total_pages = max(1, math.ceil(total_records / page_size))
        
        # Enforce valid 1-indexed page limits
        current_page = max(1, min(page, total_pages))
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_records)
        
        page_df = raw_df.iloc[start_idx:end_idx].copy()
        
        # Strip target column if present
        if "readmitted" in page_df.columns:
            page_df = page_df.drop(columns=["readmitted"])
            
        records = []
        for idx_rel, (idx_abs, row) in enumerate(page_df.iterrows()):
            record_dict = row.to_dict()
            # Attach stable patient ID derived from absolute CSV row index (10001 + idx_abs)
            record_dict["patient_id"] = f"PT-{10001 + idx_abs}"
            record_dict["original_row_index"] = idx_abs
            records.append(record_dict)
            
        return {
            "patients": records,
            "total": total_records,
            "page": current_page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    def assign_risk_tier(self, prob: float) -> str:
        if prob >= 0.60:
            return "High Risk"
        elif prob >= self.threshold:
            return "Moderate Risk"
        else:
            return "Low Risk"

    def predict_single(self, patient_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Strip patient_id or index keys if passed in patient dict before feature engineering
        clean_patient = {k: v for k, v in patient_dict.items() if k not in ["patient_id", "original_row_index", "readmitted"]}
        raw_df = pd.DataFrame([clean_patient])
        
        X_feat = build_features(raw_df)
        
        prob = float(self.pipeline.predict_proba(X_feat)[0, 1])
        is_readmitted = "yes" if prob >= self.threshold else "no"
        risk_tier = self.assign_risk_tier(prob)
        
        shap_drivers_raw = explain_single_prediction(
            self.pipeline, X_feat, feature_names=self.feature_names, top_n=3
        )
        
        top_drivers = []
        for d in shap_drivers_raw:
            fname = d["feature"]
            val = d["shap_value"]
            direction = d["direction"]
            plain_label = translate_to_plain_language(fname, clean_patient, val)
            top_drivers.append({
                "feature": fname,
                "shap_value": val,
                "direction": direction,
                "plain_language_driver": plain_label
            })
            
        return {
            "readmission_probability": round(prob, 4),
            "predicted_readmitted": is_readmitted,
            "operating_threshold": round(self.threshold, 4),
            "clinical_risk_tier": risk_tier,
            "top_3_shap_drivers": top_drivers
        }

    def predict_batch(self, patient_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Clean dict items by dropping auxiliary metadata keys before feature engineering
        cleaned_records = [
            {k: v for k, v in item.items() if k not in ["patient_id", "original_row_index", "readmitted", "id", "target"]}
            for item in patient_records
        ]
        df_raw = pd.DataFrame(cleaned_records)
        
        X_feat = build_features(df_raw)
        
        probs = self.pipeline.predict_proba(X_feat)[:, 1]
        
        results = []
        high_cnt, mod_cnt, low_cnt = 0, 0, 0
        
        for idx, (prob, original_item) in enumerate(zip(probs, patient_records)):
            prob_val = float(prob)
            is_readmitted = "yes" if prob_val >= self.threshold else "no"
            risk_tier = self.assign_risk_tier(prob_val)
            
            if risk_tier == "High Risk":
                high_cnt += 1
            elif risk_tier == "Moderate Risk":
                mod_cnt += 1
            else:
                low_cnt += 1
                
            primary_driver = None
            try:
                single_feat = X_feat.iloc[[idx]]
                shap_raw = explain_single_prediction(self.pipeline, single_feat, feature_names=self.feature_names, top_n=1)
                if shap_raw:
                    top_f = shap_raw[0]["feature"]
                    top_v = shap_raw[0]["shap_value"]
                    primary_driver = translate_to_plain_language(top_f, cleaned_records[idx], top_v)
            except Exception as e:
                logger.warning(f"Batch row {idx} SHAP calculation skipped: {e}")
                
            p_res = {
                "patient_index": idx,
                "readmission_probability": round(prob_val, 4),
                "predicted_readmitted": is_readmitted,
                "clinical_risk_tier": risk_tier,
                "primary_driver": primary_driver
            }
            if "patient_id" in original_item:
                p_res["patient_id"] = original_item["patient_id"]
                
            results.append(p_res)
            
        return {
            "total_patients": len(patient_records),
            "high_risk_count": high_cnt,
            "moderate_risk_count": mod_cnt,
            "low_risk_count": low_cnt,
            "predictions": results
        }

_model_service_instance: Optional[ModelService] = None

def get_model_service() -> ModelService:
    global _model_service_instance
    if _model_service_instance is None:
        _model_service_instance = ModelService()
    return _model_service_instance
