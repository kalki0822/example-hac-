import os
import sys
import json
import joblib
import hashlib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

sys.path.append(os.path.abspath("."))
from src.features.build_features import build_canonical_model_features

def compute_calibration_metrics(y_true, y_prob):
    # 10-bin calibration curve
    bins = np.linspace(0, 1, 11)
    binids = np.digitize(y_prob, bins) - 1
    
    ece = 0.0
    mce = 0.0
    curve_data = []
    
    for i in range(10):
        idx = (binids == i)
        n_pts = int(np.sum(idx))
        if n_pts > 0:
            mean_pred = float(np.mean(y_prob[idx]))
            actual_rate = float(np.mean(y_true[idx]))
            cal_err = abs(mean_pred - actual_rate)
            ece += (n_pts / len(y_true)) * cal_err
            if cal_err > mce:
                mce = cal_err
            curve_data.append({
                "bin": i + 1,
                "range_min": round(float(bins[i]), 1),
                "range_max": round(float(bins[i+1]), 1),
                "patients": n_pts,
                "mean_predicted_prob": round(mean_pred, 4),
                "actual_readmission_rate": round(actual_rate, 4),
                "calibration_error": round(cal_err, 4)
            })
        else:
            curve_data.append({
                "bin": i + 1,
                "range_min": round(float(bins[i]), 1),
                "range_max": round(float(bins[i+1]), 1),
                "patients": 0,
                "mean_predicted_prob": None,
                "actual_readmission_rate": None,
                "calibration_error": None
            })
            
    # Calibration Slope and Intercept via Logistic Regression logit mapping
    epsilon = 1e-15
    y_prob_clipped = np.clip(y_prob, epsilon, 1 - epsilon)
    logit_p = np.log(y_prob_clipped / (1 - y_prob_clipped))
    
    calib_lr = LogisticRegression(C=1e5, solver="lbfgs")
    calib_lr.fit(logit_p.reshape(-1, 1), y_true)
    
    slope = float(calib_lr.coef_[0][0])
    intercept = float(calib_lr.intercept_[0])
    
    brier = float(brier_score_loss(y_true, y_prob))
    l_loss = float(log_loss(y_true, y_prob))
    r_auc = float(roc_auc_score(y_true, y_prob))
    pr_auc = float(average_precision_score(y_true, y_prob))
    
    return {
        "brier_score": round(brier, 4),
        "log_loss": round(l_loss, 4),
        "ece": round(float(ece), 4),
        "mce": round(float(mce), 4),
        "calibration_slope": round(slope, 4),
        "calibration_intercept": round(intercept, 4),
        "roc_auc": round(r_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "curve_data": curve_data
    }

def main():
    print("=== VITALS ENTERPRISE V1.0 — MODEL CALIBRATION PIPELINE ===")
    
    base_model_path = "models/best_model.pkl"
    assert os.path.exists(base_model_path), "Base model artifact models/best_model.pkl not found!"
    
    with open(base_model_path, "rb") as f:
        base_bytes = f.read()
    base_hash = hashlib.sha256(base_bytes).hexdigest().upper()
    print(f"Base Model SHA-256 Hash: {base_hash}")
    assert base_hash == "74BA9C6508BAD62F6378E35679E0BB8C693FDC7B2D33AD51C2C859FCBF9FB3C0", "Base model hash mismatch!"
    
    base_pipeline = joblib.load(base_model_path)
    
    # Load 25,000 reference Kaggle dataset
    df = pd.read_csv("data/raw/hospital_readmissions.csv")
    X = build_canonical_model_features(df)
    y = (df["readmitted"].str.lower() == "yes").astype(int).values
    
    # 70% Train (17,500), 15% Calibration (3,750), 15% Test (3,750) stratified split
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_calib, y_train, y_calib = train_test_split(
        X_train_val, y_train_val, test_size=(0.15 / 0.85), random_state=42, stratify=y_train_val
    )
    
    print(f"Dataset Split Sizes: Train={len(y_train)}, Calibration={len(y_calib)}, Test={len(y_test)}")
    
    # Compute raw probabilities from frozen base model on Calibration set and Test set
    raw_probs_calib = base_pipeline.predict_proba(X_calib)[:, 1]
    raw_probs_test = base_pipeline.predict_proba(X_test)[:, 1]
    
    # Fit Platt Scaling Calibrator on 15% Calibration set (Logit(raw_prob) -> y_calib)
    epsilon = 1e-15
    raw_probs_calib_clipped = np.clip(raw_probs_calib, epsilon, 1 - epsilon)
    logit_calib = np.log(raw_probs_calib_clipped / (1 - raw_probs_calib_clipped)).reshape(-1, 1)
    
    platt_calibrator = LogisticRegression(C=1e5, solver="lbfgs")
    platt_calibrator.fit(logit_calib, y_calib)
    
    # Predict calibrated probabilities on untouched 15% Test set
    raw_probs_test_clipped = np.clip(raw_probs_test, epsilon, 1 - epsilon)
    logit_test = np.log(raw_probs_test_clipped / (1 - raw_probs_test_clipped)).reshape(-1, 1)
    calib_probs_test = platt_calibrator.predict_proba(logit_test)[:, 1]
    
    # Compute Raw vs Calibrated Metrics on untouched Test set
    raw_metrics = compute_calibration_metrics(y_test, raw_probs_test)
    calib_metrics = compute_calibration_metrics(y_test, calib_probs_test)
    
    print("\n=== RAW VS CALIBRATED METRICS ON UNTOUCHED TEST SET (N=3,750) ===")
    print(f"Brier Score:           Raw = {raw_metrics['brier_score']:.4f} | Calibrated = {calib_metrics['brier_score']:.4f}")
    print(f"ECE (Calibration Error): Raw = {raw_metrics['ece']:.4f} | Calibrated = {calib_metrics['ece']:.4f}")
    print(f"MCE (Max Calib Error): Raw = {raw_metrics['mce']:.4f} | Calibrated = {calib_metrics['mce']:.4f}")
    print(f"Log Loss:              Raw = {raw_metrics['log_loss']:.4f} | Calibrated = {calib_metrics['log_loss']:.4f}")
    print(f"Calibration Slope:     Raw = {raw_metrics['calibration_slope']:.4f} | Calibrated = {calib_metrics['calibration_slope']:.4f}")
    print(f"Calibration Intercept: Raw = {raw_metrics['calibration_intercept']:.4f} | Calibrated = {calib_metrics['calibration_intercept']:.4f}")
    print(f"ROC-AUC:               Raw = {raw_metrics['roc_auc']:.4f} | Calibrated = {calib_metrics['roc_auc']:.4f}")
    print(f"PR-AUC:                Raw = {raw_metrics['pr_auc']:.4f} | Calibrated = {calib_metrics['pr_auc']:.4f}")
    
    # Save calibrator artifact
    os.makedirs("models", exist_ok=True)
    calibrator_path = "models/calibrator.pkl"
    joblib.dump(platt_calibrator, calibrator_path)
    print(f"\nCalibrator saved to {calibrator_path}")
    
    # Compute new reference cohort calibrated percentiles (P25, P50, P75) on full 25,000 reference dataset
    ref_raw_probs = base_pipeline.predict_proba(X)[:, 1]
    ref_raw_clipped = np.clip(ref_raw_probs, epsilon, 1 - epsilon)
    ref_logit = np.log(ref_raw_clipped / (1 - ref_raw_clipped)).reshape(-1, 1)
    ref_calib_probs = platt_calibrator.predict_proba(ref_logit)[:, 1]
    
    ref_p25 = round(float(np.percentile(ref_calib_probs, 25)), 4)
    ref_p50 = round(float(np.percentile(ref_calib_probs, 50)), 4)
    ref_p75 = round(float(np.percentile(ref_calib_probs, 75)), 4)
    
    print("\n=== RECALCULATED REFERENCE COHORT CALIBRATED QUARTILE BOUNDARIES ===")
    print(f"Reference P25 (Minimal -> Moderate):  {ref_p25:.4f}")
    print(f"Reference P50 (Moderate -> Elevated): {ref_p50:.4f}")
    print(f"Reference P75 (Elevated -> High):     {ref_p75:.4f}")
    
    # Export calibration metadata JSON
    metadata = {
        "base_model": "LogisticRegression",
        "base_model_hash": base_hash,
        "calibration_method": "Platt Scaling (Sigmoid)",
        "calibrator_version": "1.0.0",
        "calibration_dataset_split": "70% Train (17,500), 15% Calibration (3,750), 15% Test (3,750)",
        "test_set_size": len(y_test),
        "reference_cohort_size": len(df),
        "reference_boundaries": {
            "p25": ref_p25,
            "p50": ref_p50,
            "p75": ref_p75,
            "q1_label": "Minimal Risk · Q1 Reference",
            "q2_label": "Moderate Risk · Q2 Reference",
            "q3_label": "Elevated Risk · Q3 Reference",
            "q4_label": "High Risk · Q4 Reference"
        },
        "raw_metrics": raw_metrics,
        "calibrated_metrics": calib_metrics,
        "ece_explanation": "Calibration metrics are sample-based estimates. When dataset size increases, the estimate can change because more observations reveal the model's actual probability behavior. Dataset distribution shift can also change observed calibration. Therefore, increasing N does not guarantee a lower ECE.",
        "risk_methodology": "Calibrated probability estimates the patient's predicted likelihood of readmission. Reference-cohort risk bands indicate where that patient falls relative to the prediction distribution of the reference hospital population. A new patient population may have a different risk distribution. Therefore, new datasets are not expected to contain exactly 25% of patients in each risk band."
    }
    
    metadata_path = "models/calibration_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Calibration metadata exported to {metadata_path}")

if __name__ == "__main__":
    main()
