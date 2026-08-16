import pytest
import numpy as np
from src.models.evaluate import compute_calibration_data, compute_threshold_grid_analysis, evaluate_predictions

def test_compute_calibration_data():
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
    y_probs = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.85, 0.15, 0.65, 0.25])
    
    calib = compute_calibration_data(y_true, y_probs, n_bins=5)
    assert "brier_score" in calib
    assert "calibration_curve" in calib
    assert isinstance(calib["calibration_curve"], list)
    assert calib["brier_score"] >= 0.0

def test_compute_threshold_grid_analysis():
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
    y_probs = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.85, 0.15, 0.65, 0.25])
    
    grid = compute_threshold_grid_analysis(y_true, y_probs)
    assert isinstance(grid, list)
    assert len(grid) > 5
    
    for row in grid:
        assert "threshold" in row
        assert "recall" in row
        assert "precision" in row
        assert "specificity" in row
        assert "avg_cost_per_patient" in row

def test_evaluate_predictions_extended_metrics():
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
    y_probs = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.85, 0.15, 0.65, 0.25])
    
    metrics = evaluate_predictions(y_true, y_probs, threshold=0.2562)
    assert "accuracy" in metrics
    assert "specificity" in metrics
    assert "fpr" in metrics
    assert "fnr" in metrics
    assert "brier_score" in metrics

def test_full_precision_boundary_risk_tier_assignment():
    """Verifies full 6-decimal precision risk-tier assignment for boundary epsilon values."""
    from api.dependencies import ModelService
    ms = ModelService()
    eps = 0.000001
    
    # P25 Boundary (0.387042)
    assert ms.assign_risk_tier(0.387042 - eps) == "Minimal Risk"
    assert ms.assign_risk_tier(0.387042 + eps) == "Moderate Risk"
    
    # P50 Boundary (0.444758)
    assert ms.assign_risk_tier(0.444758 - eps) == "Moderate Risk"
    assert ms.assign_risk_tier(0.444758 + eps) == "Elevated Risk"
    
    # P75 Boundary (0.520089)
    assert ms.assign_risk_tier(0.520089 - eps) == "Elevated Risk"
    assert ms.assign_risk_tier(0.520089 + eps) == "High Risk"

