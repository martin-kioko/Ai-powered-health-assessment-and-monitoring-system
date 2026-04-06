import logging
from config import BaseConfig as cfg
from database import get_db, Assessment, Patient, DoctorNote, User
from risk_engine.engine import run_assessment
from auth import log_action

log = logging.getLogger(__name__)


def validate_vitals(vitals: dict) -> tuple[list, list]:
    errors, warnings = [], []
    for field, (lo, hi) in cfg.CLINICAL_LIMITS.items():
        v = vitals.get(field)
        if v is not None and not (lo <= v <= hi):
            label = field.replace("_", " ").title()
            errors.append(f"{label} = {v} is outside the physiologically possible range ({lo}–{hi}).")
    for field, (lo, hi) in cfg.CLINICAL_WARNINGS.items():
        v = vitals.get(field)
        if v is not None and not (lo <= v <= hi):
            label = field.replace("_", " ").title()
            warnings.append(f"{label} ({v}) is outside the normal range ({lo}–{hi}). Please verify.")
    return errors, warnings


def submit_assessment(patient_id: int, vitals: dict, user_id: int) -> dict:
    result = run_assessment(vitals)

    lines = [
        f"Risk level: {result['final_risk']} (model confidence: {result['ml_probability']:.1%})",
        f"NEWS2 clinical score: {result.get('news2_score', 'N/A')} — {result.get('news2_detail', '')}",
        f"Model prediction: {result['ml_prediction']}",
    ]

    if result.get("safety_override"):
        lines.append(f"\nClinical note: {result['override_reason']}")

    if result["shap_features"]:
        factor_lines = "\n".join(
            f"  {name}: {imp:.3f}" for name, imp in result["shap_features"]
        )
        lines.append(f"\nTop contributing factors (SHAP):\n{factor_lines}")

    explanation = "\n".join(lines)

    with get_db() as db:
        a = Assessment(
            patient_id=patient_id,
            respiratory_rate=vitals["respiratory_rate"],
            oxygen_saturation=vitals["oxygen_saturation"],
            o2_scale=vitals["o2_scale"],
            systolic_bp=vitals["systolic_bp"],
            heart_rate=vitals["heart_rate"],
            temperature=vitals["temperature"],
            consciousness=vitals["consciousness"],
            on_oxygen=vitals["on_oxygen"],
            ml_prediction=result["ml_prediction"],
            ml_probability=result["ml_probability"],
            final_risk=result["final_risk"],
            explanation=explanation,
            recommendation=result["recommendation"],
            status="pending",
        )
        db.add(a)
        db.commit()
        result["assessment_id"] = a.id

    log_action(user_id, "SUBMIT_ASSESSMENT",
               f"Assessment #{result['assessment_id']} — {result['final_risk']}"
               + (" [SAFETY OVERRIDE]" if result.get("safety_override") else ""))
    return result


def get_patient_id_for_user(user_id: int) -> int | None:
    with get_db() as db:
        p = db.query(Patient).filter(Patient.user_id == user_id).first()
        return p.id if p else None


def get_patient_dashboard_data(user_id: int) -> dict:
    with get_db() as db:
        patient = db.query(Patient).filter(Patient.user_id == user_id).first()
        if not patient:
            return {}

        assessments = (
            db.query(Assessment)
            .filter(Assessment.patient_id == patient.id)
            .order_by(Assessment.created_at.desc())
            .all()
        )
        latest = assessments[0] if assessments else None

        latest_notes = []
        if latest:
            latest_notes = (
                db.query(DoctorNote, User)
                .join(User, DoctorNote.doctor_id == User.id)
                .filter(DoctorNote.assessment_id == latest.id)
                .all()
            )

        risk_counts = {"Low": 0, "Medium": 0, "High": 0}
        trend_dates = []
        trend_risks = []
        for a in assessments:
            risk_counts[a.final_risk] = risk_counts.get(a.final_risk, 0) + 1
            if a.created_at:
                trend_dates.append(a.created_at.strftime("%b %d"))
                trend_risks.append({"Low": 1, "Medium": 2, "High": 3}.get(a.final_risk, 0))

        pat_data = {
            "id": patient.id, "age": patient.age,
            "gender": patient.gender, "conditions": patient.underlying_conditions,
        }

        latest_data = None
        if latest:
            latest_data = {
                "id": latest.id, "final_risk": latest.final_risk,
                "ml_prediction": latest.ml_prediction,
                "ml_probability": latest.ml_probability or 0.0,
                "explanation": latest.explanation,
                "recommendation": latest.recommendation,
                "status": latest.status,
                "respiratory_rate": latest.respiratory_rate,
                "oxygen_saturation": latest.oxygen_saturation,
                "systolic_bp": latest.systolic_bp,
                "heart_rate": latest.heart_rate,
                "temperature": latest.temperature,
                "consciousness": latest.consciousness,
                "on_oxygen": latest.on_oxygen,
                "created_at": latest.created_at.strftime("%B %d, %Y at %H:%M")
                              if latest.created_at else "N/A",
            }

        notes_data = [
            {
                "doctor": doc.name,
                "date": note.created_at.strftime("%b %d, %Y") if note.created_at else "",
                "note": note.note,
            }
            for note, doc in latest_notes
        ]

        # History now includes full vitals for expandable rows
        history = [
            {
                "id": a.id,
                "final_risk": a.final_risk,
                "ml_prediction": a.ml_prediction,
                "ml_probability": a.ml_probability or 0.0,
                "status": a.status,
                "created_at": a.created_at.strftime("%b %d, %Y %H:%M") if a.created_at else "N/A",
                "recommendation": a.recommendation,
                "explanation": a.explanation,
                # Vitals
                "respiratory_rate": a.respiratory_rate,
                "oxygen_saturation": a.oxygen_saturation,
                "systolic_bp": a.systolic_bp,
                "heart_rate": a.heart_rate,
                "temperature": a.temperature,
                "consciousness": a.consciousness,
                "on_oxygen": a.on_oxygen,
            }
            for a in assessments
        ]

        return {
            "pat": pat_data, "latest": latest_data, "notes": notes_data,
            "history": history, "risk_counts": risk_counts,
            "trend_dates": trend_dates, "trend_risks": trend_risks,
            "total": len(assessments),
            "pending": sum(1 for a in history if a["status"] == "pending"),
        }


def get_assessment_for_pdf(assessment_id: int, user_id: int) -> dict | None:
    with get_db() as db:
        a       = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        patient = db.query(Patient).filter(Patient.user_id == user_id).first()
        if not a or not patient or a.patient_id != patient.id:
            return None
        user = db.query(User).filter(User.id == user_id).first()

        notes = (
            db.query(DoctorNote, User)
            .join(User, DoctorNote.doctor_id == User.id)
            .filter(DoctorNote.assessment_id == a.id)
            .all()
        )

        return {
            "patient_info": {
                "name": user.name, "email": user.email,
                "age": patient.age, "gender": patient.gender,
                "conditions": patient.underlying_conditions,
            },
            "assessment": {
                "id": a.id, "final_risk": a.final_risk,
                "ml_prediction": a.ml_prediction,
                "ml_probability": a.ml_probability or 0.0,
                "respiratory_rate": a.respiratory_rate,
                "oxygen_saturation": a.oxygen_saturation,
                "o2_scale": a.o2_scale, "systolic_bp": a.systolic_bp,
                "heart_rate": a.heart_rate, "temperature": a.temperature,
                "consciousness": a.consciousness, "on_oxygen": a.on_oxygen,
                "explanation": a.explanation, "recommendation": a.recommendation,
            },
            "doctor_notes": [
                {
                    "doctor_name": doc.name,
                    "date": note.created_at.strftime("%b %d, %Y") if note.created_at else "",
                    "note": note.note,
                }
                for note, doc in notes
            ],
        }