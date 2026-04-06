import logging
from functools import wraps
from flask import session, redirect, url_for, flash
import bcrypt as _bcrypt
from database import get_db, User, Patient, AuditLog

log = logging.getLogger(__name__)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Login / Register ──────────────────────────────────────────────────────────

def login_user(email: str, password: str):
    with get_db() as db:
        u = db.query(User).filter(User.email == email.lower().strip()).first()
        if not u:
            return None, "No account found with that email address."
        if not u.is_active:
            return None, "This account has been deactivated."
        if not verify_password(password, u.password_hash):
            return None, "Incorrect password."
        _audit(db, u.id, "LOGIN", u.email)
        return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}, None


def register_user(name, email, password, role="patient",
                  age=None, gender=None, conditions=None):
    with get_db() as db:
        if db.query(User).filter(User.email == email.lower().strip()).first():
            return None, "That email address is already registered."

        u = User(
            name=name.strip(),
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role=role,
        )
        db.add(u)
        db.flush()

        if role == "patient":
            db.add(Patient(
                user_id=u.id, age=age,
                gender=gender, underlying_conditions=conditions,
            ))

        db.commit()
        _audit(db, u.id, "REGISTER", f"New {role}: {u.email}")
        return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}, None


# ── Session helpers ───────────────────────────────────────────────────────────

def set_session(user: dict) -> None:
    session["user_id"]    = user["id"]
    session["user_name"]  = user["name"]
    session["user_email"] = user["email"]
    session["user_role"]  = user["role"]
    session.permanent     = True


def clear_session() -> None:
    session.clear()


def get_current_user() -> dict | None:
    if "user_id" not in session:
        return None
    return {
        "id":    session["user_id"],
        "name":  session["user_name"],
        "email": session["user_email"],
        "role":  session["user_role"],
    }


# ── Route decorators ──────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            flash("Please sign in to access that page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please sign in.", "warning")
                return redirect(url_for("auth.login"))
            if user["role"] not in roles:
                flash("Access denied.", "danger")
                return redirect(url_for("main.landing"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Audit ─────────────────────────────────────────────────────────────────────

def log_action(user_id: int, action: str, details: str = "") -> None:
    try:
        with get_db() as db:
            db.add(AuditLog(user_id=user_id, action=action, details=details))
            db.commit()
    except Exception as exc:
        log.error("Audit write failed: %s", exc)


def _audit(db, user_id, action, details=""):
    try:
        db.add(AuditLog(user_id=user_id, action=action, details=details))
        db.commit()
    except Exception:
        pass


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_defaults(admin_email, admin_password, doctor_email, doctor_password) -> None:
    with get_db() as db:
        if db.query(User).filter(User.role == "admin").first():
            return
        db.add(User(
            name="System Administrator",
            email=admin_email,
            password_hash=hash_password(admin_password),
            role="admin",
        ))
        db.add(User(
            name="Dr. Sarah Johnson",
            email=doctor_email,
            password_hash=hash_password(doctor_password),
            role="doctor",
        ))
        db.commit()
        log.info("Default admin and doctor accounts seeded.")
