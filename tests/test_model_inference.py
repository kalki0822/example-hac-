import os
import sys
import pytest
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.dependencies import ModelService, translate_to_plain_language

def test_model_service_load():
    service = ModelService()
    assert service.is_loaded() is True
    assert service.threshold > 0.0
    assert len(service.feature_names) > 0

def test_translate_to_plain_language():
    sample_patient = {
        "n_emergency": 3,
        "n_inpatient": 2,
        "n_outpatient": 1,
        "n_medications": 15,
        "time_in_hospital": 4,
        "age": "[70-80)"
    }
    
    label_emerg = translate_to_plain_language("n_emergency", sample_patient, 0.5)
    assert "3 emergency room visit" in label_emerg
    
    label_inp = translate_to_plain_language("n_inpatient", sample_patient, 0.4)
    assert "2 prior inpatient admission" in label_inp
    
    label_diag = translate_to_plain_language("diag_1_Circulatory", sample_patient, 0.3)
    assert "Circulatory condition" in label_diag

def test_model_service_predict_single():
    service = ModelService()
    sample = {
        "age": "[60-70)",
        "time_in_hospital": 3,
        "n_procedures": 1,
        "n_lab_procedures": 40,
        "n_medications": 12,
        "n_outpatient": 0,
        "n_inpatient": 1,
        "n_emergency": 0,
        "medical_specialty": "Cardiology",
        "diag_1": "Circulatory",
        "diag_2": "Diabetes",
        "diag_3": "Other",
        "glucose_test": "normal",
        "A1Ctest": "none",
        "change": "no",
        "diabetes_med": "yes"
    }
    
    res = service.predict_single(sample)
    assert 0.0 <= res["readmission_probability"] <= 1.0
    assert res["predicted_readmitted"] in ["yes", "no"]
    assert res["clinical_risk_tier"] in ["Minimal Risk", "Moderate Risk", "Elevated Risk", "High Risk", "Low Risk"]
    assert len(res["top_3_shap_drivers"]) == 3
