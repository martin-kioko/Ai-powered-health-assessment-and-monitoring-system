"""
risk_engine/engine.py

Single-layer classification using ML model only.
Final risk is determined entirely by the ML model prediction.
"""
from .ml_model import get_model, get_scaler, predict, shap_explanation

_RECOMMENDATIONS = {
    "Low":    "Continue routine self-monitoring. Contact your care team if new symptoms develop.",
    "Medium": "Increase monitoring frequency. Contact your care team within 24 hours.",
    "High":   "Seek urgent clinical attention immediately. Contact your doctor or emergency services.",
}


def run_assessment(vitals: dict) -> dict:
    model  = get_model()
    scaler = get_scaler()

    if model is None:
        raise RuntimeError("Prediction model is not available. Please contact support.")

    # ML model prediction
    ml_risk, confidence, class_probs = predict(vitals, model, scaler)
    if ml_risk is None:
        raise RuntimeError("Prediction failed. Please try again.")

    shap_feats = shap_explanation(vitals, model, scaler)

    return {
        "ml_prediction":   ml_risk,
        "ml_probability":  confidence,
        "ml_class_probs":  class_probs or [],
        "final_risk":      ml_risk,
        "recommendation":  _RECOMMENDATIONS[ml_risk],
        "shap_features":   shap_feats,
        "safety_override": False,
        "override_reason": None,
        "news2_score":     None,
        "news2_detail":    None,
    }