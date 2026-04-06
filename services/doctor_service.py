import logging
from sqlalchemy.orm import joinedload
from database import get_db, Assessment, Patient, DoctorNote, User
from auth import log_action

log = logging.getLogger(__name__)


def get_doctor_dashboard_data() -> dict:
    with get_db() as db:
        assessments = (
            db.query(Assessment)
            .options(
                joinedload(Assessment.patient).joinedload(Patient.user),
                joinedload(Assessment.doctor_notes),
            )
            .order_by(Assessment.created_at.desc())
            .all()
        )

        risk_counts = {"Low": 0, "Medium": 0, "High": 0}
        pending_data = []
        all_patients_map = {}

        for a in assessments:
            risk_counts[a.final_risk] = risk_counts.get(a.final_risk, 0) + 1

            patient_name = (
                a.patient.user.name if a.patient and a.patient.user else "Unknown"
            )

            if a.status == "pending":
                pending_data.append({
                    "id": a.id, "patient_name": patient_name,
                    "final_risk": a.final_risk,
                    "ml_prediction": a.ml_prediction,
                    "ml_probability": a.ml_probability or 0.0,
                    "respiratory_rate": a.respiratory_rate,
                    "oxygen_saturation": a.oxygen_saturation,
                    "systolic_bp": a.systolic_bp, "heart_rate": a.heart_rate,
                    "temperature": a.temperature, "consciousness": a.consciousness,
                    "on_oxygen": a.on_oxygen, "explanation": a.explanation,
                    "recommendation": a.recommendation,
                    "created_at": a.created_at.strftime("%b %d, %Y %H:%M")
                                  if a.created_at else "N/A",
                })

            pid = a.patient_id
            if pid not in all_patients_map:
                p = a.patient
                pu = p.user if p else None
                all_patients_map[pid] = {
                    "name": pu.name if pu else "Unknown",
                    "email": pu.email if pu else "",
                    "age": p.age if p else None,
                    "gender": p.gender if p else None,
                    "conditions": p.underlying_conditions if p else None,
                    "latest_risk": a.final_risk,
                    "total": 0,
                }
            all_patients_map[pid]["total"] += 1

        return {
            "pending": pending_data,
            "patients": list(all_patients_map.values()),
            "risk_counts": risk_counts,
            "total_assessments": len(assessments),
        }


def submit_review(assessment_id: int, doctor_id: int, note_text: str) -> bool:
    with get_db() as db:
        a = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not a:
            return False
        db.add(DoctorNote(
            assessment_id=a.id, doctor_id=doctor_id, note=note_text.strip()
        ))
        a.status = "reviewed"
        db.commit()
    log_action(doctor_id, "REVIEW_ASSESSMENT", f"Assessment #{assessment_id}")
    return True
