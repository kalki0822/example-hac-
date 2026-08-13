import os
import json
import joblib
import logging
import yaml
import numpy as np
import pandas as pd
from datetime import datetime

from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_curve

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.data.load_data import load_raw_data
from src.data.preprocess import prepare_features_and_target
from src.features.build_features import build_features
from src.models.evaluate import find_optimal_threshold, evaluate_predictions
from src.explainability.shap_utils import generate_global_shap_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def build_preprocessing_transformer(config: dict, feature_engineered_df: pd.DataFrame) -> ColumnTransformer:
    """
    Constructs scikit-learn ColumnTransformer with OneHotEncoder for categoricals
    and StandardScaler for numerics.
    """
    num_cols = config["features"]["numerical"]
    cat_cols = config["features"]["categorical"]
    
    actual_num_cols = [c for c in num_cols if c in feature_engineered_df.columns]
    actual_cat_cols = [c for c in cat_cols if c in feature_engineered_df.columns]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), actual_num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), actual_cat_cols)
        ],
        remainder="drop"
    )
    return preprocessor

def train_and_evaluate_models(config_path: str = "config.yaml"):
    """
    Main training workflow for 25,000-row real Kaggle dataset:
    1. Ingestion & Preprocessing
    2. Feature Engineering
    3. Stratified 5-Fold Cross Validation across candidate models
    4. Cost-sensitive threshold optimization (C_fn=5.0, C_fp=1.0)
    5. OOF ROC Curve Data Extraction
    6. Model Selection & Artifact Serialization
    7. Global SHAP Summary Plot Generation
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    logger.info("Starting Vitals Model Training Pipeline on REAL Kaggle Dataset...")
    
    # 1. Load Raw Data
    raw_df = load_raw_data(config_path)
    logger.info(f"Loaded raw dataset shape: {raw_df.shape}")
    
    target_col = config["data"]["target_col"]
    X_raw, y = prepare_features_and_target(raw_df, target_col=target_col)
    
    # 2. Feature Engineering
    logger.info("Applying domain feature engineering transformations...")
    X_feat = build_features(X_raw)
    
    # 3. Candidate Models Setup
    candidate_models = {
        "LogisticRegression": LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=config["cross_validation"]["random_state"]
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=config["cross_validation"]["random_state"],
            n_jobs=-1
        )
    }
    
    lgbm_used = False
    try:
        from lightgbm import LGBMClassifier
        candidate_models["LightGBM"] = LGBMClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=config["cross_validation"]["random_state"],
            verbose=-1,
            n_jobs=-1
        )
        lgbm_used = True
        logger.info("LightGBM successfully loaded.")
    except Exception as e:
        logger.warning(f"LightGBM unavailable ({e}). Falling back to XGBoost.")
        try:
            from xgboost import XGBClassifier
            scale_pos_weight = (len(y) - y.sum()) / max(y.sum(), 1)
            candidate_models["XGBoost"] = XGBClassifier(
                n_estimators=100,
                scale_pos_weight=scale_pos_weight,
                random_state=config["cross_validation"]["random_state"],
                eval_metric="logloss",
                n_jobs=-1
            )
            logger.info("XGBoost successfully loaded as fallback model.")
        except Exception as ex:
            logger.error(f"Neither LightGBM nor XGBoost could be loaded: {ex}")

    # 4. Stratified 5-Fold CV Evaluation
    cv = StratifiedKFold(
        n_splits=config["cross_validation"]["n_splits"],
        shuffle=True,
        random_state=config["cross_validation"]["random_state"]
    )
    
    cost_fn = config["cost_matrix"]["cost_fn"]
    cost_fp = config["cost_matrix"]["cost_fp"]
    
    model_results = {}
    oof_probs_map = {}
    best_model_name = None
    best_cost = float("inf")
    best_metrics = None
    best_threshold = 0.5
    
    for name, model_instance in candidate_models.items():
        logger.info(f"Evaluating {name} with Stratified 5-Fold Cross Validation...")
        
        preprocessor = build_preprocessing_transformer(config, X_feat)
        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("classifier", model_instance)
        ])
        
        # Out-of-fold probability predictions
        oof_probs = cross_val_predict(
            pipeline,
            X_feat,
            y,
            cv=cv,
            method="predict_proba"
        )[:, 1]
        
        oof_probs_map[name] = oof_probs
        
        # Threshold tuning
        opt_thresh, opt_cost = find_optimal_threshold(
            y.values, oof_probs, cost_fn=cost_fn, cost_fp=cost_fp
        )
        
        metrics = evaluate_predictions(
            y.values, oof_probs, threshold=opt_thresh, cost_fn=cost_fn, cost_fp=cost_fp
        )
        
        logger.info(
            f"{name} Results -> ROC-AUC: {metrics['roc_auc']:.4f} | PR-AUC: {metrics['pr_auc']:.4f} | "
            f"F1: {metrics['f1_score']:.4f} | Recall: {metrics['recall_positive']:.4f} | "
            f"Avg Cost: ${metrics['avg_cost_per_patient']:.4f}"
        )
        
        model_results[name] = metrics
        
        # Select winning model based on minimum average cost per patient
        if metrics["avg_cost_per_patient"] < best_cost:
            best_cost = metrics["avg_cost_per_patient"]
            best_model_name = name
            best_metrics = metrics
            best_threshold = opt_thresh

    logger.info(f"\n==========================================")
    logger.info(f"WINNING MODEL: {best_model_name} (Avg Cost: ${best_cost:.4f}/patient)")
    logger.info(f"==========================================\n")
    
    # 5. Extract ROC Curve points for winning model
    winning_oof_probs = oof_probs_map[best_model_name]
    fpr_array, tpr_array, _ = roc_curve(y.values, winning_oof_probs)
    
    # Subsample 15 ROC points for UI rendering
    subsample_idx = np.linspace(0, len(fpr_array) - 1, 15, dtype=int)
    roc_curve_points = [
        {"fpr": round(float(fpr_array[i]), 4), "tpr": round(float(tpr_array[i]), 4)}
        for i in subsample_idx
    ]
    
    # 6. Fit Final Winning Pipeline on Full 25,000 Dataset
    winning_model_instance = candidate_models[best_model_name]
    final_preprocessor = build_preprocessing_transformer(config, X_feat)
    final_pipeline = Pipeline(steps=[
        ("preprocessor", final_preprocessor),
        ("classifier", winning_model_instance)
    ])
    
    logger.info(f"Fitting final {best_model_name} pipeline on full {len(X_feat)} dataset...")
    final_pipeline.fit(X_feat, y)
    
    fitted_preprocessor = final_pipeline.named_steps["preprocessor"]
    feature_names_out = [f.split("__")[-1] for f in fitted_preprocessor.get_feature_names_out()]
    
    # 7. Global SHAP Summary Plot
    X_transformed = fitted_preprocessor.transform(X_feat)
    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()
        
    shap_summary_path = config["output"]["shap_summary_path"]
    generate_global_shap_summary(
        final_pipeline.named_steps["classifier"],
        X_transformed,
        feature_names=feature_names_out,
        output_path=shap_summary_path
    )
    
    # 8. Serialize Model Artifacts
    os.makedirs(config["output"]["model_dir"], exist_ok=True)
    best_model_path = config["output"]["best_model_path"]
    metadata_path = config["output"]["metadata_path"]
    
    joblib.dump(final_pipeline, best_model_path)
    logger.info(f"Serialized final pipeline to {best_model_path}")
    
    metadata = {
        "model_name": best_model_name,
        "version": config["project"]["version"],
        "timestamp": datetime.now().isoformat(),
        "gradient_boosting_backend": "LightGBM" if lgbm_used else "XGBoost",
        "dataset_rows": len(raw_df),
        "target_distribution": {
            "negative_0_no": int((y == 0).sum()),
            "positive_1_yes": int((y == 1).sum())
        },
        "optimal_threshold": float(best_threshold),
        "cost_parameters": {
            "cost_fn": cost_fn,
            "cost_fp": cost_fp
        },
        "evaluation_metrics_oof": best_metrics,
        "roc_curve_points": roc_curve_points,
        "all_model_results_oof": model_results,
        "num_features_raw": len(X_raw.columns),
        "num_features_engineered": len(X_feat.columns),
        "num_transformed_features": len(feature_names_out),
        "feature_names_transformed": feature_names_out
    }
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved real-data model metadata to {metadata_path}")
    
    return final_pipeline, metadata

if __name__ == "__main__":
    train_and_evaluate_models()
