import os
import logging
import numpy as np
import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "age", "time_in_hospital", "n_lab_procedures", "n_procedures",
    "n_medications", "n_outpatient", "n_inpatient", "n_emergency",
    "medical_specialty", "diag_1", "diag_2", "diag_3", "glucose_test",
    "A1Ctest", "change", "diabetes_med", "readmitted"
]

AGE_GROUPS = ["[40-50)", "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"]
SPECIALTIES = ["InternalMedicine", "Cardiology", "Family/GeneralPractice", "Emergency/Trauma", "Surgery", "Other", "Missing"]
DIAGNOSES = ["Circulatory", "Respiratory", "Diabetes", "Digestive", "Injury", "Musculoskeletal", "Other", "Missing"]
TEST_RESULTS = ["no", "normal", "high"]
BOOLEAN_FLAGS = ["no", "yes"]

def generate_synthetic_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Fallback generator for development when raw Kaggle CSV is missing.
    Matches the Kaggle dataset schema.
    """
    logger.info(f"Generating fallback synthetic dataset ({n_samples} records)...")
    np.random.seed(seed)
    
    age = np.random.choice(AGE_GROUPS, size=n_samples, p=[0.10, 0.20, 0.30, 0.25, 0.10, 0.05])
    time_in_hospital = np.random.geometric(p=0.25, size=n_samples).clip(1, 14)
    n_lab_procedures = np.random.normal(loc=43, scale=18, size=n_samples).astype(int).clip(1, 113)
    n_procedures = np.random.poisson(lam=1.3, size=n_samples).clip(0, 6)
    n_medications = np.random.normal(loc=16, scale=8, size=n_samples).astype(int).clip(1, 79)
    
    n_outpatient = np.random.negative_binomial(n=1, p=0.7, size=n_samples).clip(0, 33)
    n_inpatient = np.random.negative_binomial(n=1, p=0.6, size=n_samples).clip(0, 15)
    n_emergency = np.random.negative_binomial(n=1, p=0.8, size=n_samples).clip(0, 64)
    
    medical_specialty = np.random.choice(SPECIALTIES, size=n_samples)
    diag_1 = np.random.choice(DIAGNOSES, size=n_samples)
    diag_2 = np.random.choice(DIAGNOSES, size=n_samples)
    diag_3 = np.random.choice(DIAGNOSES, size=n_samples)
    
    glucose_test = np.random.choice(TEST_RESULTS, size=n_samples, p=[0.82, 0.10, 0.08])
    A1Ctest = np.random.choice(TEST_RESULTS, size=n_samples, p=[0.78, 0.12, 0.10])
    change = np.random.choice(BOOLEAN_FLAGS, size=n_samples, p=[0.53, 0.47])
    diabetes_med = np.random.choice(BOOLEAN_FLAGS, size=n_samples, p=[0.23, 0.77])
    
    high_risk = np.isin(diag_1, ["Circulatory", "Respiratory", "Diabetes"]).astype(int)
    log_odds = -0.5 + 0.4 * n_inpatient + 0.3 * n_emergency + 0.03 * n_medications + 0.3 * high_risk
    readmission_prob = 1 / (1 + np.exp(-log_odds))
    readmitted = np.where(np.random.rand(n_samples) < readmission_prob, "yes", "no")
    
    df = pd.DataFrame({
        "age": age,
        "time_in_hospital": time_in_hospital,
        "n_lab_procedures": n_lab_procedures,
        "n_procedures": n_procedures,
        "n_medications": n_medications,
        "n_outpatient": n_outpatient,
        "n_inpatient": n_inpatient,
        "n_emergency": n_emergency,
        "medical_specialty": medical_specialty,
        "diag_1": diag_1,
        "diag_2": diag_2,
        "diag_3": diag_3,
        "glucose_test": glucose_test,
        "A1Ctest": A1Ctest,
        "change": change,
        "diabetes_med": diabetes_med,
        "readmitted": readmitted
    })
    return df

def validate_schema(df: pd.DataFrame) -> bool:
    """Verifies that required columns are present in the dataset."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in dataset: {missing_cols}")
    logger.info("Dataset schema validation passed successfully.")
    return True

def load_raw_data(config_path: str = "config.yaml") -> pd.DataFrame:
    """
    Primary Data Loader Rule:
    IF data/raw/hospital_readmissions.csv exists, ALWAYS use the real Kaggle CSV dataset.
    IF missing, use synthetic dataset generator as fallback.
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    raw_path = config["data"]["raw_path"]
    
    if os.path.exists(raw_path):
        logger.info(f"Loading REAL Kaggle dataset from {raw_path}")
        df = pd.read_csv(raw_path)
    else:
        logger.warning(f"Real data file not found at {raw_path}. Using synthetic fallback...")
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        sample_size = config["data"].get("synthetic_sample_size", 5000)
        seed = config["data"].get("random_seed", 42)
        df = generate_synthetic_data(n_samples=sample_size, seed=seed)
        df.to_csv(raw_path, index=False)
        logger.info(f"Saved fallback dataset to {raw_path}")
        
    validate_schema(df)
    return df

if __name__ == "__main__":
    df = load_raw_data()
    print(f"Loaded DataFrame shape: {df.shape}")
    print(df.head())
