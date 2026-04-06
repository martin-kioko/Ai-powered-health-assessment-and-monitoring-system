from database import get_db, User, Assessment, Patient, AuditLog
from auth import log_action


def get_admin_dashboard_data() -> dict:
    with get_db() as db:
        all_users = db.query(User).order_by(User.created_at.desc()).all()
        all_asms  = db.query(Assessment).order_by(Assessment.created_at.desc()).all()
        logs = (
            db.query(AuditLog, User)
            .outerjoin(User, AuditLog.user_id == User.id)
            .order_by(AuditLog.timestamp.desc())
            .limit(100)
            .all()
        )

        risk_counts = {"Low": 0, "Medium": 0, "High": 0}
        for a in all_asms:
            risk_counts[a.final_risk] = risk_counts.get(a.final_risk, 0) + 1

        users_data = [
            {
                "id": u.id, "name": u.name, "email": u.email,
                "role": u.role, "is_active": u.is_active,
                "created_at": u.created_at.strftime("%b %d, %Y") if u.created_at else "N/A",
            }
            for u in all_users
        ]

        logs_data = [
            {
                "time":    lg.timestamp.strftime("%b %d, %Y %H:%M") if lg.timestamp else "N/A",
                "user":    lu.name if lu else "System",
                "role":    lu.role.title() if lu else "—",
                "action":  lg.action,
                "details": (lg.details or "")[:120],
            }
            for lg, lu in logs
        ]

        # Build patient assessments view for admin
        patients = db.query(Patient).all()
        patient_user_map = {}
        for p in patients:
            u = db.query(User).filter(User.id == p.user_id).first()
            if u:
                patient_user_map[p.id] = {
                    "name": u.name,
                    "email": u.email,
                    "age": p.age,
                    "gender": p.gender,
                    "conditions": p.underlying_conditions,
                }

        # Recent assessments with vitals — last 50
        recent_assessments = []
        for a in all_asms[:50]:
            pat_info = patient_user_map.get(a.patient_id, {})
            recent_assessments.append({
                "id": a.id,
                "patient_name": pat_info.get("name", "Unknown"),
                "patient_email": pat_info.get("email", ""),
                "final_risk": a.final_risk,
                "ml_prediction": a.ml_prediction,
                "ml_probability": a.ml_probability or 0.0,
                "status": a.status,
                "respiratory_rate": a.respiratory_rate,
                "oxygen_saturation": a.oxygen_saturation,
                "systolic_bp": a.systolic_bp,
                "heart_rate": a.heart_rate,
                "temperature": a.temperature,
                "consciousness": a.consciousness,
                "on_oxygen": a.on_oxygen,
                "recommendation": a.recommendation,
                "created_at": a.created_at.strftime("%b %d, %Y %H:%M") if a.created_at else "N/A",
            })

        return {
            "users": users_data,
            "risk_counts": risk_counts,
            "total_assessments": len(all_asms),
            "patients_count": sum(1 for u in users_data if u["role"] == "patient"),
            "doctors_count": sum(1 for u in users_data if u["role"] == "doctor"),
            "logs": logs_data,
            "recent_assessments": recent_assessments,
        }


def toggle_user_active(user_id: int, current_user_id: int) -> tuple[bool, str]:
    if user_id == current_user_id:
        return False, "You cannot deactivate your own account."
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            return False, "User not found."
        u.is_active = not u.is_active
        db.commit()
        action = "ACTIVATE_USER" if u.is_active else "DEACTIVATE_USER"
        log_action(current_user_id, action, u.email)
        verb = "Activated" if u.is_active else "Deactivated"
        return True, f"{verb}: {u.email}"