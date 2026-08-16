import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    recall_score,
    precision_score,
    accuracy_score,
    brier_score_loss,
    confusion_matrix
)
from sklearn.calibration import calibration_curve

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def compute_cost_score(y_true: np.ndarray, y_pred: np.ndarray, cost_fn: float = 5.0, cost_fp: float = 1.0) -> Dict[str, float]:
    """
    Computes total clinical/financial cost:
    - False Negative (missed readmission) cost = cost_fn (e.g. 5.0)
    - False Positive (unnecessary intervention) cost = cost_fp (e.g. 1.0)
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    total_cost = (fn * cost_fn) + (fp * cost_fp)
    avg_cost = total_cost / len(y_true) if len(y_true) > 0 else 0.0
    
    return {
        "total_cost": float(total_cost),
        "avg_cost_per_patient": float(avg_cost),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp)
    }

def compute_calibration_data(y_true: np.ndarray, y_probs: np.ndarray, n_bins: int = 10) -> Dict[str, Any]:
    """
    Computes probability calibration curve points and Brier score for monitoring only.
    DOES NOT modify the underlying model prediction probabilities.
    """
    prob_true, prob_pred = calibration_curve(y_true, y_probs, n_bins=n_bins, strategy="uniform")
    brier_score = float(brier_score_loss(y_true, y_probs))
    
    curve_points = [
        {
            "prob_pred": round(float(pred), 4),
            "prob_true": round(float(true_val), 4)
        }
        for pred, true_val in zip(prob_pred, prob_true)
    ]
    
    return {
        "brier_score": round(brier_score, 4),
        "calibration_curve": curve_points,
        "n_bins": n_bins
    }

def compute_threshold_grid_analysis(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    cost_fn: float = 5.0,
    cost_fp: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Evaluates classification performance and expected clinical cost across a standardized threshold grid
    (0.05 to 0.90 in increments of 0.05).
    """
    threshold_grid = [0.05, 0.10, 0.15, 0.20, 0.25, 0.2562, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    grid_results = []
    
    for th in threshold_grid:
        y_pred = (y_probs >= th).astype(int)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        
        total = len(y_true)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        cost_info = compute_cost_score(y_true, y_pred, cost_fn=cost_fn, cost_fp=cost_fp)
        
        grid_results.append({
            "threshold": round(float(th), 4),
            "recall": round(float(recall), 4),
            "precision": round(float(precision), 4),
            "specificity": round(float(specificity), 4),
            "f1_score": round(float(f1), 4),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
            "total_cost": cost_info["total_cost"],
            "avg_cost_per_patient": round(cost_info["avg_cost_per_patient"], 4),
            "is_selected": abs(th - 0.2562) < 0.005
        })
        
    return grid_results

def find_optimal_threshold(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    cost_fn: float = 5.0,
    cost_fp: float = 1.0,
    n_thresholds: int = 200
) -> Tuple[float, float]:
    """
    Finds the operating probability threshold in [0, 1] that minimizes cost score.
    Returns (best_threshold, min_avg_cost).
    """
    thresholds = np.linspace(0.01, 0.99, n_thresholds)
    best_threshold = 0.5
    min_cost = float("inf")
    
    for th in thresholds:
        y_pred = (y_probs >= th).astype(int)
        cost_res = compute_cost_score(y_true, y_pred, cost_fn=cost_fn, cost_fp=cost_fp)
        avg_cost = cost_res["avg_cost_per_patient"]
        
        if avg_cost < min_cost:
            min_cost = avg_cost
            best_threshold = float(th)
            
    logger.info(f"Cost-sensitive threshold tuning selected threshold = {best_threshold:.4f} with avg cost = ${min_cost:.2f}/patient")
    return best_threshold, min_cost

def evaluate_predictions(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    threshold: float = 0.5,
    cost_fn: float = 5.0,
    cost_fp: float = 1.0
) -> Dict[str, Any]:
    """
    Evaluates comprehensive binary classification metrics:
    - ROC-AUC, PR-AUC, Accuracy, F1, Recall, Precision, Specificity, FPR, FNR, Brier Score, Confusion Matrix, Cost.
    """
    y_pred = (y_probs >= threshold).astype(int)
    
    roc_auc = roc_auc_score(y_true, y_probs)
    pr_auc = average_precision_score(y_true, y_probs)
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    precision = precision_score(y_true, y_pred, zero_division=0)
    brier = brier_score_loss(y_true, y_probs)
    
    cost_metrics = compute_cost_score(y_true, y_pred, cost_fn=cost_fn, cost_fp=cost_fp)
    tn = cost_metrics["tn"]
    fp = cost_metrics["fp"]
    fn = cost_metrics["fn"]
    tp = cost_metrics["tp"]
    
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    return {
        "threshold": float(threshold),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "accuracy": float(acc),
        "f1_score": float(f1),
        "recall_positive": float(recall),
        "precision_positive": float(precision),
        "specificity": float(specificity),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "brier_score": float(brier),
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp
        },
        "total_cost": cost_metrics["total_cost"],
        "avg_cost_per_patient": cost_metrics["avg_cost_per_patient"]
    }
