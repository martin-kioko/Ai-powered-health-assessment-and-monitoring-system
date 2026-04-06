from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import role_required, get_current_user
from services.doctor_service import get_doctor_dashboard_data, submit_review

doctor_bp = Blueprint("doctor", __name__)


@doctor_bp.route("/doctor")
@role_required("doctor", "admin")
def dashboard():
    user = get_current_user()
    data = get_doctor_dashboard_data()
    return render_template("doctor_dashboard.html", user=user, **data)


@doctor_bp.route("/doctor/review/<int:assessment_id>", methods=["POST"])
@role_required("doctor", "admin")
def review(assessment_id):
    user      = get_current_user()
    note_text = request.form.get("note", "").strip()

    if not note_text:
        flash("A clinical note is required before marking as reviewed.", "warning")
        return redirect(url_for("doctor.dashboard"))

    ok = submit_review(assessment_id, user["id"], note_text)
    if not ok:
        flash("Assessment not found.", "danger")
    else:
        flash("Assessment reviewed.", "success")

    return redirect(url_for("doctor.dashboard"))
