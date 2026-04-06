import os
import pickle
import logging
import numpy as np

log = logging.getLogger(__name__)

FEATURE_NAMES = [
    "Respiratory Rate", "Oxygen Saturation", "O2 Scale",
    "Systolic BP", "Heart Rate", "Temperature",
    "Consciousness (C)", "Consciousness (P)",
    "Consciousness (U)", "Consciousness (V)", "On Oxygen",
]

_DATA_MIN = np.array([12.,  74., 1.,  50.,  64., 35.6])
_DATA_MAX = np.array([40., 100., 2., 144., 163., 41.8])

_model  = None
_scaler = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def preload(model_path: str, scaler_path: str) -> None:
    global _model, _scaler
    try:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        import tensorflow as tf
        from tensorflow.keras.layers import BatchNormalization

        class CompatBatchNorm(BatchNormalization):
            def __init__(self, **kwargs):
                kwargs.pop("renorm", None)
                kwargs.pop("renorm_clipping", None)
                kwargs.pop("renorm_momentum", None)
                super().__init__(**kwargs)

        _model = tf.keras.models.load_model(
            model_path,
            compile=False,
            custom_objects={"BatchNormalization": CompatBatchNorm}
        )
        log.info("Keras model loaded from %s", model_path)
    except Exception as exc:
        log.error("Model load failed: %s", exc)
        _model = None
    try:
        with open(scaler_path, "rb") as f:
            _scaler = pickle.load(f)
        log.info("Scaler loaded from %s", scaler_path)
    except Exception as exc:
        log.error("Scaler load failed: %s", exc)
        _scaler = None


preload(
    os.path.join(BASE_DIR, "models", "risk_model_v2.h5"),
    os.path.join(BASE_DIR, "models", "scaler_v2.pkl"),
)


def get_model():
    return _model


def get_scaler():
    return _scaler


def build_feature_vector(vitals: dict, scaler) -> np.ndarray:
    cons = str(vitals.get("consciousness", "A")).upper()
    numeric = np.array([[
        vitals["respiratory_rate"], vitals["oxygen_saturation"],
        vitals["o2_scale"],         vitals["systolic_bp"],
        vitals["heart_rate"],       vitals["temperature"],
    ]], dtype=float)

    if scaler is not None:
        try:
            scaled = scaler.transform(numeric)[0]
            scaled = np.clip(scaled, -5.0, 5.0)
        except Exception:
            scaled = np.clip(
                (numeric[0] - _DATA_MIN) / (_DATA_MAX - _DATA_MIN + 1e-8), 0, 1
            )
    else:
        scaled = np.clip(
            (numeric[0] - _DATA_MIN) / (_DATA_MAX - _DATA_MIN + 1e-8), 0, 1
        )

    ohe = [
        1 if cons == "C" else 0,
        1 if cons == "P" else 0,
        1 if cons == "U" else 0,
        1 if cons == "V" else 0,
    ]
    vec = np.concatenate([scaled, ohe, [int(vitals.get("on_oxygen", 0))]]).astype(np.float32)
    return vec.reshape(1, -1)


def predict(vitals: dict, model, scaler):
    """
    Three-class label mapping:
      Index 0 = Low
      Index 1 = Medium
      Index 2 = High

    Confidence = probability of the winning class.
    """
    try:
        x     = build_feature_vector(vitals, scaler)
        probs = model.predict(x, verbose=0)[0]

        label_map = {0: "Low", 1: "Medium", 2: "High"}
        ml_risk   = label_map[int(np.argmax(probs))]
        ml_conf   = float(probs[np.argmax(probs)])

        # Remapped for display: [High, Low, Medium]
        remapped = [float(probs[2]), float(probs[0]), float(probs[1])]
        return ml_risk, ml_conf, remapped

    except Exception as exc:
        log.error("Prediction failed: %s", exc)
        return None, None, None


def shap_explanation(vitals: dict, model, scaler, top_n: int = 4) -> list:
    try:
        import shap
        x          = build_feature_vector(vitals, scaler)
        background = np.zeros((1, 11), dtype=np.float32)
        explainer  = shap.GradientExplainer(model, background)
        shap_vals  = explainer.shap_values(x)
        if isinstance(shap_vals, list):
            importance = np.abs(np.array(shap_vals)).mean(axis=0)[0]
        else:
            importance = np.abs(shap_vals[0])
        top_idx = np.argsort(importance)[::-1][:top_n]
        return [(FEATURE_NAMES[i], float(importance[i])) for i in top_idx]
    except Exception as exc:
        log.warning("SHAP explanation unavailable: %s", exc)
        return []