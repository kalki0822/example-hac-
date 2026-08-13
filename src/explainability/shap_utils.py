import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environment
import matplotlib.pyplot as plt
import shap
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_global_shap_summary(
    model,
    X_transformed: np.ndarray,
    feature_names: List[str],
    output_path: str = "reports/figures/shap_summary.png"
) -> np.ndarray:
    """
    Computes SHAP values for global dataset and saves summary plot to disk.
    """
    logger.info("Computing SHAP values for global dataset explainability...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    model_name = type(model).__name__.lower()
    
    if any(tree_type in model_name for tree_type in ["lgbm", "lightgbm", "xgboost", "randomforest", "decisiontree"]):
        try:
            explainer = shap.TreeExplainer(model)
            shap_values = explainer(X_transformed)
        except Exception as e:
            logger.warning(f"TreeExplainer failed ({e}), using Linear/Generic Explainer")
            background = shap.sample(X_transformed, min(100, len(X_transformed)))
            explainer = shap.Explainer(model, background)
            shap_values = explainer(X_transformed)
    elif "logistic" in model_name or "linear" in model_name:
        try:
            background = shap.sample(X_transformed, min(100, len(X_transformed)))
            explainer = shap.LinearExplainer(model, background)
            shap_values = explainer(X_transformed)
        except Exception as e:
            logger.warning(f"LinearExplainer failed ({e}), using Linear coefficient attribution")
            coefs = model.coef_[0]
            shap_values = X_transformed * coefs
    else:
        background = shap.sample(X_transformed, min(100, len(X_transformed)))
        explainer = shap.Explainer(model, background)
        shap_values = explainer(X_transformed)
    
    # Standardize SHAP values array for plotting
    if hasattr(shap_values, "values"):
        vals = shap_values.values
        if len(vals.shape) == 3:
            shap_vals_matrix = vals[:, :, 1]
        else:
            shap_vals_matrix = vals
    else:
        shap_vals_matrix = shap_values
        if isinstance(shap_vals_matrix, list):
            shap_vals_matrix = shap_vals_matrix[1]

    plt.figure(figsize=(10, 6))
    try:
        shap.summary_plot(
            shap_vals_matrix,
            features=X_transformed,
            feature_names=feature_names,
            show=False
        )
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Global SHAP summary plot saved to {output_path}")
    except Exception as e:
        logger.error(f"Error plotting SHAP summary: {e}")
        plt.close()
        plt.figure(figsize=(10, 6))
        mean_abs_shap = np.abs(shap_vals_matrix).mean(axis=0)
        top_idx = np.argsort(mean_abs_shap)[-15:]
        plt.barh(np.array(feature_names)[top_idx], mean_abs_shap[top_idx], color="#1f77b4")
        plt.xlabel("Mean |SHAP Value| (Impact on Model Output)")
        plt.title("Top Feature Importances (SHAP)")
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Fallback feature importance plot saved to {output_path}")
        
    return shap_vals_matrix

def explain_single_prediction(
    pipeline,
    X_feat: pd.DataFrame,
    feature_names: List[str] = None,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    Calculates SHAP driver contributions for a single patient instance.
    Returns list of top N feature drivers: [{feature, shap_value, direction}]
    """
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["classifier"]
    
    X_transformed = preprocessor.transform(X_feat)
    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()
        
    if feature_names is None:
        if hasattr(preprocessor, "get_feature_names_out"):
            feature_names = [f.split("__")[-1] for f in preprocessor.get_feature_names_out()]
        else:
            feature_names = [f"feature_{i}" for i in range(X_transformed.shape[1])]
            
    model_name = type(model).__name__.lower()
    
    if any(t in model_name for t in ["lgbm", "lightgbm", "xgboost", "randomforest"]):
        explainer = shap.TreeExplainer(model)
        shap_res = explainer(X_transformed)
        if hasattr(shap_res, "values"):
            vals = shap_res.values
            instance_shap = vals[0, :, 1] if len(vals.shape) == 3 else vals[0, :]
        else:
            instance_shap = shap_res[0]
    elif "logistic" in model_name or "linear" in model_name:
        # Linear SHAP contribution for logistic regression: coef * normalized_feature_value
        coefs = model.coef_[0]
        instance_shap = coefs * X_transformed[0]
    else:
        explainer = shap.Explainer(model, X_transformed)
        shap_res = explainer(X_transformed)
        instance_shap = shap_res.values[0] if hasattr(shap_res, "values") else shap_res[0]

    # Sort features by absolute SHAP impact
    top_indices = np.argsort(np.abs(instance_shap))[::-1][:top_n]
    
    results = []
    for idx in top_indices:
        fname = feature_names[idx]
        val = float(instance_shap[idx])
        direction = "Increases Readmission Risk" if val > 0 else "Decreases Readmission Risk"
        results.append({
            "feature": fname,
            "shap_value": round(val, 4),
            "direction": direction
        })
        
    return results
