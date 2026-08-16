import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_preventive_actions(
    patient_data: Dict[str, Any],
    risk_tier: str,
    shap_drivers: List[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """
    Deterministic clinical recommendation engine for hospital readmission risk prevention.
    
    Translates patient clinical parameters, risk tier (High / Moderate / Low Risk),
    and SHAP explainability drivers into prioritized preventive actions for clinician consideration.
    
    Does NOT use LLMs, random generation, or automated prescribing.
    """
    actions = []
    
    # Extract numerical & categorical features safely
    n_inpatient = int(patient_data.get("n_inpatient", 0) or 0)
    n_emergency = int(patient_data.get("n_emergency", 0) or 0)
    n_outpatient = int(patient_data.get("n_outpatient", 0) or 0)
    n_medications = int(patient_data.get("n_medications", 0) or 0)
    time_stay = int(patient_data.get("time_in_hospital", 0) or 0)
    age = str(patient_data.get("age", ""))
    
    diag_1 = str(patient_data.get("diag_1", ""))
    diag_2 = str(patient_data.get("diag_2", ""))
    diag_3 = str(patient_data.get("diag_3", ""))
    
    diabetes_med = str(patient_data.get("diabetes_med", "")).lower()
    change = str(patient_data.get("change", "")).lower()
    glucose_test = str(patient_data.get("glucose_test", "")).lower()
    a1c_test = str(patient_data.get("A1Ctest", "")).lower()

    shap_labels = []
    if shap_drivers:
        for sd in shap_drivers:
            lbl = sd.get("plain_language_driver") or sd.get("feature")
            if lbl:
                shap_labels.append(str(lbl))

    # Rule A: Elevated Prior Healthcare Utilization
    if n_inpatient > 0 or n_emergency > 0 or n_outpatient >= 2:
        reasons = []
        if n_inpatient > 0:
            reasons.append(f"{n_inpatient} prior inpatient admission(s)")
        if n_emergency > 0:
            reasons.append(f"{n_emergency} ER visit(s)")
        if n_outpatient >= 2:
            reasons.append(f"{n_outpatient} outpatient visit(s)")
        
        reason_str = f"Elevated healthcare utilization in past year ({', '.join(reasons)})"
        if any("utilization" in l.lower() or "emergency" in l.lower() or "inpatient" in l.lower() for l in shap_labels):
            reason_str += " — confirmed as a top SHAP risk driver."

        actions.append({
            "title": "Consider early post-discharge follow-up (within 7 days)",
            "reason": reason_str
        })

    # Rule B: High Medication Burden
    if n_medications >= 12:
        reason_str = f"High medication count ({n_medications} prescribed medications during stay)"
        if any("medication" in l.lower() for l in shap_labels):
            reason_str += " — SHAP identified polypharmacy burden as a major contributor."

        actions.append({
            "title": "Review medication reconciliation and polypharmacy adherence plan",
            "reason": reason_str
        })

    # Rule C: Advanced Age Bracket
    if age in ["[70-80)", "[80-90)", "[90-100)"]:
        actions.append({
            "title": "Consider closer post-discharge clinical monitoring and caregiver support",
            "reason": f"Advanced patient age bracket ({age}) associated with post-discharge vulnerability"
        })

    # Rule D: Longer Hospital Stay
    if time_stay >= 4:
        actions.append({
            "title": "Coordinate extended transition-of-care discharge planning",
            "reason": f"Extended hospitalization stay length ({time_stay} days)"
        })

    # Rule E: Diabetes-Related Management Indicators
    if (
        "Diabetes" in (diag_1, diag_2, diag_3)
        or diabetes_med == "yes"
        or change == "yes"
        or glucose_test == "high"
        or a1c_test == "high"
    ):
        actions.append({
            "title": "Review diabetes management, glucose log monitoring, and outpatient care plan",
            "reason": "Diabetes-related diagnostic classification, active medication, or elevated lab results"
        })

    # Rule F: High-Risk Cardiopulmonary Diagnoses
    if "Circulatory" in (diag_1, diag_2) or "Respiratory" in (diag_1, diag_2):
        actions.append({
            "title": "Schedule specialized cardiopulmonary outpatient follow-up review",
            "reason": f"Primary or secondary diagnosis of Circulatory/Respiratory condition ({diag_1})"
        })

    # Fallback for High Risk if few specific rules matched
    if risk_tier == "High Risk" and len(actions) < 2:
        actions.append({
            "title": "Arrange multi-disciplinary discharge planning review prior to discharge",
            "reason": "Patient categorized as High Risk for 30-day readmission"
        })

    # Risk-based prioritization tagging and caps
    if risk_tier == "High Risk":
        priority = "High"
        final_actions = actions[:4]
    elif risk_tier == "Moderate Risk":
        priority = "Medium"
        if not actions:
            actions.append({
                "title": "Schedule routine outpatient follow-up within 14 days",
                "reason": "Moderate readmission risk profile"
            })
        final_actions = actions[:3]
    else:  # Low Risk
        priority = "Routine"
        final_actions = [{
            "title": "Standard post-discharge follow-up care and patient instructions",
            "reason": "Patient categorized as Low Risk; routine clinical transition plan recommended."
        }]

    return [
        {
            "title": item["title"],
            "reason": item["reason"],
            "priority": priority
        }
        for item in final_actions
    ]
