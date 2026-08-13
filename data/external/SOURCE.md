# Data Source & Provenance

## Primary Dataset
- **Dataset Name**: Hospital Readmissions
- **Source**: Kaggle Dataset
- **URL**: https://www.kaggle.com/datasets/dubradave/hospital-readmissions
- **Dataset Size**: 25,000 patient records × 17 features
- **Target Variable**: `readmitted` (`yes` / `no`)
- **Local Project Path**: `data/raw/hospital_readmissions.csv`

## Dataset Priority & Development Fallback Policy
The primary model is trained directly on the real Kaggle Hospital Readmissions dataset (25,000 patient records) supplied by the problem statement and copied to `data/raw/hospital_readmissions.csv`. Synthetic data generation is retained solely as a development fallback when the real CSV is absent.
