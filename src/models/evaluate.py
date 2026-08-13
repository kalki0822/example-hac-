import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    recall_score,
    precision_score,
    confusion_matrix
)

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
    Evaluates binary classification metrics:
    - ROC-AUC, PR-AUC, F1, Recall (Positive Class), Precision, Confusion Matrix, Cost metrics.
    """
    y_pred = (y_probs >= threshold).astype(int)
    
    roc_auc = roc_auc_score(y_true, y_probs)
    pr_auc = average_precision_score(y_true, y_probs)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    precision = precision_score(y_true, y_pred, zero_division=0)
    
    cost_metrics = compute_cost_score(y_true, y_pred, cost_fn=cost_fn, cost_fp=cost_fp)
    
    return {
        "threshold": float(threshold),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "f1_score": float(f1),
        "recall_positive": float(recall),
        "precision_positive": float(precision),
        "confusion_matrix": {
            "tn": cost_metrics["tn"],
            "fp": cost_metrics["fp"],
            "fn": cost_metrics["fn"],
            "tp": cost_metrics["tp"]
        },
        "total_cost": cost_metrics["total_cost"],
        "avg_cost_per_patient": cost_metrics["avg_cost_per_patient"]
    }
