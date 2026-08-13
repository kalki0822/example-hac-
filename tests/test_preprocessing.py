import os
import sys
import pytest
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.load_data import generate_synthetic_data, validate_schema
from src.data.preprocess import clean_and_preprocess_data, prepare_features_and_target
from src.features.build_features import FeatureEngineer, build_features

def test_generate_synthetic_data():
    df = generate_synthetic_data(n_samples=100, seed=42)
    assert len(df) == 100
    assert validate_schema(df) is True
    assert df["readmitted"].isin(["yes", "no"]).all()

def test_clean_and_preprocess_data():
    df_raw = pd.DataFrame({
        "age": ["[50-60)", "[70-80)"],
        "time_in_hospital": [3, 5],
        "n_procedures": [1, 2],
        "n_lab_procedures": [30, 40],
        "n_medications": [10, 15],
        "n_outpatient": [0, 1],
        "n_inpatient": [0, 2],
        "n_emergency": [0, 1],
        "medical_specialty": ["Cardiology", "?"],
        "diag_1": ["Circulatory", "Respiratory"],
        "diag_2": ["Diabetes", "None"],
        "diag_3": ["Other", "Missing"],
        "glucose_test": ["normal", "high"],
        "A1Ctest": ["none", "normal"],
        "change": ["no", "yes"],
        "diabetes_med": ["yes", "yes"],
        "readmitted": ["no", "yes"]
    })
    
    df_clean = clean_and_preprocess_data(df_raw, target_col="readmitted")
    assert df_clean["readmitted"].tolist() == [0, 1]
    assert "?" not in df_clean["medical_specialty"].values
    assert "None" not in df_clean["diag_2"].values

def test_feature_engineer():
    df_raw = pd.DataFrame({
        "age": ["[70-80)"],
        "time_in_hospital": [4],
        "n_procedures": [2],
        "n_lab_procedures": [30],
        "n_medications": [10],
        "n_outpatient": [1],
        "n_inpatient": [2],
        "n_emergency": [1],
        "diag_1": ["Circulatory"],
        "diag_2": ["Respiratory"],
        "diag_3": ["Other"]
    })
    
    fe = FeatureEngineer()
    df_feat = fe.transform(df_raw)
    
    # Expected utilization_score: 3.0*2 + 2.0*1 + 1.0*1 = 9.0
    assert df_feat["utilization_score"].iloc[0] == 9.0
    
    # Expected care_intensity: (2 + 30 + 10) / 4 = 10.5
    assert df_feat["care_intensity"].iloc[0] == 10.5
    
    # Expected age_utilization_interaction: 75.0 * 9.0 = 675.0
    assert df_feat["age_utilization_interaction"].iloc[0] == 675.0
    
    assert "diagnosis_risk_bucket" in df_feat.columns
    assert df_feat["diagnosis_risk_bucket"].iloc[0] in ["High", "Medium", "Low"]

def test_prepare_features_and_target():
    df_raw = generate_synthetic_data(n_samples=50, seed=42)
    X, y = prepare_features_and_target(df_raw, target_col="readmitted")
    
    assert len(X) == 50
    assert len(y) == 50
    assert "readmitted" not in X.columns
    assert set(y.unique()).issubset({0, 1})
