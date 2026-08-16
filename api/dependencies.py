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

from src.features.build_features import build_features, build_canonical_model_features
from src.explainability.shap_utils import explain_single_prediction
from src.data.load_data import load_raw_data
from src.recommendations import generate_preventive_actions

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
    Platt Scaling calibration, predictions, metadata retrieval, dataset pagination,
    SHAP explainability, and preventive action recommendations.
    """
    def __init__(
        self,
        model_path: str = "models/best_model.pkl",
        metadata_path: str = "models/model_metadata.json",
        calibrator_path: str = "models/calibrator.pkl",
        calibration_metadata_path: str = "models/calibration_metadata.json"
    ):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.calibrator_path = calibrator_path
        self.calibration_metadata_path = calibration_metadata_path
        self.pipeline = None
        self.calibrator = None
        self.metadata = {}
        self.calibration_metadata = {}
        self.threshold = 0.5
        self.feature_names = []
        
        # Calibrated reference cohort quartile boundaries (Full 6-Decimal Precision)
        self.ref_p25 = 0.387042
        self.ref_p50 = 0.444758
        self.ref_p75 = 0.520089
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.metadata_path):
            logger.error(f"Model file ({self.model_path}) or metadata ({self.metadata_path}) not found!")
            raise FileNotFoundError("Trained model artifacts missing.")
            
        logger.info(f"Loading trained pipeline from {self.model_path}...")
        self.pipeline = joblib.load(self.model_path)
        
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)
            
        if os.path.exists(self.calibrator_path):
            logger.info(f"Loading Platt Scaling calibrator from {self.calibrator_path}...")
            self.calibrator = joblib.load(self.calibrator_path)
            
        if os.path.exists(self.calibration_metadata_path):
            with open(self.calibration_metadata_path, "r") as f:
                self.calibration_metadata = json.load(f)
            ref_b = self.calibration_metadata.get("reference_boundaries", {})
            self.ref_p25 = float(ref_b.get("p25", 0.387042))
            self.ref_p50 = float(ref_b.get("p50", 0.444758))
            self.ref_p75 = float(ref_b.get("p75", 0.520089))
            
        self.threshold = float(self.metadata.get("optimal_threshold", 0.5))
        self.feature_names = self.metadata.get("feature_names_transformed", [])
        logger.info(f"Model service initialized. Operating threshold = {self.threshold:.4f} | Calibrated Boundaries: P25={self.ref_p25}, P50={self.ref_p50}, P75={self.ref_p75}")

    def is_loaded(self) -> bool:
        return self.pipeline is not None and bool(self.metadata)

    def get_metrics(self) -> Dict[str, Any]:
        combined = dict(self.metadata)
        if self.calibration_metadata:
            combined["calibration"] = self.calibration_metadata
        return combined

    def calibrate_prob(self, raw_prob: float) -> float:
        """Applies Platt Scaling (Sigmoid) calibration mapping: raw_prob -> calibrated_prob."""
        if self.calibrator is None:
            return float(raw_prob)
        epsilon = 1e-15
        raw_clipped = np.clip(raw_prob, epsilon, 1 - epsilon)
        logit_val = np.log(raw_clipped / (1 - raw_clipped)).reshape(-1, 1)
        calib_p = float(self.calibrator.predict_proba(logit_val)[0, 1])
        return calib_p

    def calibrate_probs_batch(self, raw_probs: np.ndarray) -> np.ndarray:
        """Applies Platt Scaling calibration mapping to array of raw probabilities."""
        if self.calibrator is None:
            return raw_probs.astype(float)
        epsilon = 1e-15
        raw_clipped = np.clip(raw_probs, epsilon, 1 - epsilon)
        logits = np.log(raw_clipped / (1 - raw_clipped)).reshape(-1, 1)
        calib_ps = self.calibrator.predict_proba(logits)[:, 1]
        return calib_ps.astype(float)

    def get_paginated_patients(self, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """
        Reads real patient records from data/raw/hospital_readmissions.csv,
        applies pagination bounds, attaches stable row-based patient IDs (e.g. PT-10001),
        and strips the target 'readmitted' column.
        """
        raw_df = load_raw_data()
        total_records = len(raw_df)
        total_pages = max(1, math.ceil(total_records / page_size))
        
        current_page = max(1, min(page, total_pages))
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_records)
        
        page_df = raw_df.iloc[start_idx:end_idx].copy()
        
        if "readmitted" in page_df.columns:
            page_df = page_df.drop(columns=["readmitted"])
            
        records = []
        for idx_rel, (idx_abs, row) in enumerate(page_df.iterrows()):
            record_dict = row.to_dict()
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
        """
        Assigns relative reference quartile risk tier derived from 25,000 reference cohort calibrated probabilities:
          Q1: Minimal Risk  (prob < P25)   [0th - 25th percentile]
          Q2: Moderate Risk (P25 <= prob < P50) [25th - 50th percentile]
          Q3: Elevated Risk (P50 <= prob < P75) [50th - 75th percentile]
          Q4: High Risk     (prob >= P75)  [75th - 100th percentile]
        """
        if prob >= self.ref_p75:
            return "High Risk"
        elif prob >= self.ref_p50:
            return "Elevated Risk"
        elif prob >= self.ref_p25:
            return "Moderate Risk"
        else:
            return "Minimal Risk"

    def predict_single(self, patient_dict: Dict[str, Any]) -> Dict[str, Any]:
        X_feat = build_canonical_model_features(patient_dict)
        
        raw_prob = float(self.pipeline.predict_proba(X_feat)[0, 1])
        calibrated_prob = float(self.calibrate_prob(raw_prob))
        
        is_readmitted = "yes" if calibrated_prob >= self.threshold else "no"
        risk_tier = self.assign_risk_tier(calibrated_prob)
        
        shap_drivers_raw = explain_single_prediction(
            self.pipeline, X_feat, feature_names=self.feature_names, top_n=3
        )
        
        top_drivers = []
        for d in shap_drivers_raw:
            fname = d["feature"]
            val = d["shap_value"]
            direction = d["direction"]
            plain_label = translate_to_plain_language(fname, patient_dict, val)
            top_drivers.append({
                "feature": fname,
                "shap_value": val,
                "direction": direction,
                "plain_language_driver": plain_label
            })
            
        # Generate patient-specific preventive action recommendations
        preventive_actions = generate_preventive_actions(
            patient_data=patient_dict,
            risk_tier=risk_tier,
            shap_drivers=top_drivers
        )
            
        return {
            "raw_readmission_probability": round(raw_prob, 4),
            "calibrated_readmission_probability": round(calibrated_prob, 4),
            "readmission_probability": round(calibrated_prob, 4),
            "predicted_readmitted": is_readmitted,
            "operating_threshold": round(self.threshold, 4),
            "clinical_risk_tier": risk_tier,
            "reference_cohort_rank": f"Q{1 if risk_tier=='Minimal Risk' else (2 if risk_tier=='Moderate Risk' else (3 if risk_tier=='Elevated Risk' else 4))} · {risk_tier} Band",
            "reference_q4_boundary": f"≥ {self.ref_p75:.2%}",
            "top_3_shap_drivers": top_drivers,
            "preventive_actions": preventive_actions
        }

    def predict_batch(self, patient_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        X_feat = build_canonical_model_features(patient_records)
        raw_probs = self.pipeline.predict_proba(X_feat)[:, 1]
        calib_probs = self.calibrate_probs_batch(raw_probs)
        
        results = []
        minimal_cnt, mod_cnt, elevated_cnt, high_cnt = 0, 0, 0, 0
        
        for idx, (raw_p, calib_p, original_item) in enumerate(zip(raw_probs, calib_probs, patient_records)):
            raw_val = float(raw_p)
            calib_val = float(calib_p)
            is_readmitted = "yes" if calib_val >= self.threshold else "no"
            risk_tier = self.assign_risk_tier(calib_val)
            
            if risk_tier == "High Risk":
                high_cnt += 1
            elif risk_tier == "Elevated Risk":
                elevated_cnt += 1
            elif risk_tier == "Moderate Risk":
                mod_cnt += 1
            else:
                minimal_cnt += 1
                
            primary_driver = None
            try:
                single_feat = X_feat.iloc[[idx]]
                shap_raw = explain_single_prediction(self.pipeline, single_feat, feature_names=self.feature_names, top_n=1)
                if shap_raw:
                    top_f = shap_raw[0]["feature"]
                    top_v = shap_raw[0]["shap_value"]
                    primary_driver = translate_to_plain_language(top_f, original_item, top_v)
            except Exception as e:
                logger.warning(f"Batch row {idx} SHAP calculation skipped: {e}")
                
            preventive_actions = generate_preventive_actions(
                patient_data=original_item,
                risk_tier=risk_tier
            )

            p_res = {
                "patient_index": idx,
                "raw_readmission_probability": round(raw_val, 4),
                "calibrated_readmission_probability": round(calib_val, 4),
                "readmission_probability": round(calib_val, 4),
                "predicted_readmitted": is_readmitted,
                "clinical_risk_tier": risk_tier,
                "reference_cohort_rank": f"Q{1 if risk_tier=='Minimal Risk' else (2 if risk_tier=='Moderate Risk' else (3 if risk_tier=='Elevated Risk' else 4))} · {risk_tier} Band",
                "primary_driver": primary_driver,
                "preventive_actions": preventive_actions
            }
            if "patient_id" in original_item:
                p_res["patient_id"] = original_item["patient_id"]
                
            results.append(p_res)
            
        # Distribution stats & shift detection
        med_p = float(np.median(calib_probs))
        ref_med = self.ref_p50
        shift_detected = bool(med_p > 0.58 or abs(med_p - ref_med) > 0.12)
        
        shift_warning = None
        if shift_detected:
            shift_warning = "DISTRIBUTION SHIFT DETECTED: This uploaded population exhibits substantially higher clinical utilization/predicted risk than the reference hospital cohort."

        return {
            "total_patients": len(patient_records),
            "minimal_risk_count": minimal_cnt,
            "moderate_risk_count": mod_cnt,
            "elevated_risk_count": elevated_cnt,
            "high_risk_count": high_cnt,
            "low_risk_count": minimal_cnt,
            "distribution_shift_detected": shift_detected,
            "distribution_warning": shift_warning,
            "distribution_stats": {
                "mean": round(float(np.mean(calib_probs)), 4),
                "median": round(med_p, 4),
                "std": round(float(np.std(calib_probs)), 4),
                "min": round(float(np.min(calib_probs)), 4),
                "max": round(float(np.max(calib_probs)), 4),
                "p25": round(float(np.percentile(calib_probs, 25)), 4),
                "p50": round(med_p, 4),
                "p75": round(float(np.percentile(calib_probs, 75)), 4),
                "p90": round(float(np.percentile(calib_probs, 90)), 4),
                "p95": round(float(np.percentile(calib_probs, 95)), 4),
                "p99": round(float(np.percentile(calib_probs, 99)), 4)
            },
            "predictions": results
        }


_model_service_instance: Optional[ModelService] = None

def get_model_service() -> ModelService:
    global _model_service_instance
    if _model_service_instance is None:
        _model_service_instance = ModelService()
    return _model_service_instance
