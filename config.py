import os
from dotenv import load_dotenv

load_dotenv()

_raw_db = os.environ.get("DATABASE_URL", "")
if _raw_db.startswith("postgres://"):
    _raw_db = _raw_db.replace("postgres://", "postgresql://", 1)


class BaseConfig:
    SECRET_KEY        = os.environ.get("SECRET_KEY", "dev-only-key-change-in-production")
    WTF_CSRF_ENABLED  = True
    DATABASE_URL      = _raw_db
    APP_NAME          = "ClinicalAI"
    DEBUG             = False
    TESTING           = False

    BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
    MODEL_PATH        = os.path.join(BASE_DIR, "models", "risk_model_v2.h5")
    SCALER_PATH       = os.path.join(BASE_DIR, "models", "scaler_v2.pkl")

    ML_CLASS_LABELS       = {0: "High", 1: "Low", 2: "Medium"}
    MODEL_FEATURE_COUNT   = 11

    CLINICAL_LIMITS = {
        "respiratory_rate":  (1,    70),
        "oxygen_saturation": (50,  100),
        "systolic_bp":       (50,  300),
        "heart_rate":        (20,  250),
        "temperature":       (30.0, 44.0),
    }

    CLINICAL_WARNINGS = {
        "respiratory_rate":  (8,   30),
        "oxygen_saturation": (85, 100),
        "systolic_bp":       (80, 220),
        "heart_rate":        (40, 180),
        "temperature":       (35.0, 40.5),
    }

    ADMIN_EMAIL     = os.environ.get("ADMIN_EMAIL",  "admin@clinic.local")
    ADMIN_PASSWORD  = os.environ.get("ADMIN_PASSWORD", "Admin@1234")
    DOCTOR_EMAIL    = os.environ.get("DOCTOR_EMAIL",  "doctor@clinic.local")
    DOCTOR_PASSWORD = os.environ.get("DOCTOR_PASSWORD", "Doctor@1234")


class DevelopmentConfig(BaseConfig):
    DEBUG            = True
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    # Ensure session cookies are sent only over HTTPS and are protected
    # from cross-site requests — required for CSRF to work behind Railway's proxy
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     ProductionConfig,
}
