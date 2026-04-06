from datetime import timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import limiter
from auth import login_user, register_user, set_session, clear_session, get_current_user

auth_bp = Blueprint("auth", __name__)


def _role_redirect(role: str):
    dest = {
        "patient": "patient.dashboard",
        "doctor":  "doctor.dashboard",
        "admin":   "admin.dashboard",
    }.get(role, "main.landing")
    return redirect(url_for(dest))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def login():
    if get_current_user():
        return _role_redirect(get_current_user()["role"])

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Email and password are required."
        else:
            user, err = login_user(email, password)
            if err:
                error = err
            else:
                set_session(user)
                flash(f"Welcome back, {user['name']}.", "success")
                return _role_redirect(user["role"])

    return render_template("login.html", error=error)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if get_current_user():
        return redirect(url_for("patient.dashboard"))

    error = None
    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        email      = request.form.get("email", "").strip()
        password   = request.form.get("password", "")
        confirm    = request.form.get("confirm_password", "")
        role       = request.form.get("role", "patient")
        age        = request.form.get("age", "")
        gender     = request.form.get("gender", "")
        conditions = request.form.get("conditions", "").strip()

        if not all([name, email, password, confirm]):
            error = "All required fields must be completed."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            age_val = int(age) if age and age.isdigit() else None
            user, err = register_user(
                name=name, email=email, password=password,
                role=role, age=age_val, gender=gender or None,
                conditions=conditions or None,
            )
            if err:
                error = err
            else:
                set_session(user)
                flash("Account created successfully.", "success")
                return _role_redirect(user["role"])

    return render_template("register.html", error=error)


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per minute")
def forgot_password():
    """
    Accepts the reset-email form submitted from the login page modal.
    Always returns a 200 JSON-style response so the frontend can show
    the success state without revealing whether the email exists
    (prevents user enumeration).

    To wire up real email delivery, replace the TODO block below with
    your preferred mail library (Flask-Mail, SendGrid, etc.).
    """
    email = request.form.get("reset_email", "").strip().lower()

    if email:
        # TODO: look up the user by email in your database, generate a
        # signed reset token (e.g. with itsdangerous.URLSafeTimedSerializer),
        # build a reset URL, and send it via your mail provider.
        #
        # Example skeleton:
        #
        #   from itsdangerous import URLSafeTimedSerializer
        #   from flask import current_app
        #   from extensions import mail          # Flask-Mail instance
        #   from flask_mail import Message
        #   from db import get_user_by_email     # your DB helper
        #
        #   user = get_user_by_email(email)
        #   if user:
        #       s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        #       token = s.dumps(email, salt="password-reset")
        #       reset_url = url_for("auth.reset_password", token=token, _external=True)
        #       msg = Message(
        #           subject="Reset your ClinicalAI password",
        #           recipients=[email],
        #           body=f"Click the link below to reset your password:\n\n{reset_url}\n\n"
        #                "This link expires in 30 minutes. If you did not request this, ignore this email.",
        #       )
        #       mail.send(msg)
        pass

    # Always return 200 — the modal already shows a success message
    # regardless of whether the email matched a real account.
    return ("", 200)


@auth_bp.route("/logout")
def logout():
    clear_session()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.landing"))