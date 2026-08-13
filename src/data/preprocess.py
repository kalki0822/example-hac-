import logging
import numpy as np
import pandas as pd
from typing import Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def clean_and_preprocess_data(df: pd.DataFrame, target_col: str = "readmitted") -> pd.DataFrame:
    """
    Cleans raw DataFrame:
    - Replaces missing indicator values ('?', 'None', 'null', NaN) with standardized missing labels.
    - Encodes binary target ('yes'/'no' or '>30'/'<30'/'NO') into 1/0 integer values.
    """
    df_clean = df.copy()
    
    # Replace question marks, empty strings, and 'None' with 'Missing' for categoricals
    df_clean = df_clean.replace(["?", "None", "null", "NaN", ""], np.nan)
    
    # Standardize target encoding if present
    if target_col in df_clean.columns:
        target_series = df_clean[target_col].astype(str).str.lower().str.strip()
        # Handle standard Kaggle readmitted values ('yes'/'no', or '>30'/'<30'/'no')
        df_clean[target_col] = np.where(
            target_series.isin(["yes", "<30", ">30", "1", "true"]), 1, 0
        )
        logger.info(f"Target column '{target_col}' encoded. Positive class proportion: {df_clean[target_col].mean():.2%}")
        
    # Impute categorical NaNs with 'Missing'
    cat_cols = df_clean.select_dtypes(include=["object", "category", "string"]).columns
    for col in cat_cols:
        if col != target_col:
            df_clean[col] = df_clean[col].fillna("Missing").astype(str)
            
    # Impute numeric NaNs with median
    num_cols = df_clean.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if col != target_col:
            median_val = df_clean[col].median() if not df_clean[col].dropna().empty else 0
            df_clean[col] = df_clean[col].fillna(median_val)
            
    return df_clean

def prepare_features_and_target(df: pd.DataFrame, target_col: str = "readmitted") -> Tuple[pd.DataFrame, pd.Series]:
    """
    Splits cleaned DataFrame into features DataFrame (X) and target Series (y).
    """
    df_clean = clean_and_preprocess_data(df, target_col=target_col)
    
    if target_col not in df_clean.columns:
        raise ValueError(f"Target column '{target_col}' not found in DataFrame.")
        
    X = df_clean.drop(columns=[target_col])
    y = df_clean[target_col].astype(int)
    
    return X, y
