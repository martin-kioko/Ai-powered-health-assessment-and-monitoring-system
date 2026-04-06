import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from auth import login_required, get_current_user
from services.assessment_service import (
    validate_vitals, submit_assessment,
    get_patient_dashboard_data, get_assessment_for_pdf,
    get_patient_id_for_user,
)
from pdf_utils import generate_pdf

patient_bp = Blueprint("patient", __name__)


@patient_bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    data = get_patient_dashboard_data(user["id"])
    if not data:
        flash("Patient profile not found.", "danger")
        return redirect(url_for("main.landing"))
    return render_template(
        "patient_dashboard.html",
        user=user,
        trend_dates=json.dumps(data["trend_dates"]),
        trend_risks=json.dumps(data["trend_risks"]),
        **{k: v for k, v in data.items() if k not in ("trend_dates", "trend_risks")},
    )


@patient_bp.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    user   = get_current_user()
    result = None
    errors, warnings = [], []

    patient_id = get_patient_id_for_user(user["id"])
    if patient_id is None:
        flash("Patient profile not found.", "danger")
        return redirect(url_for("main.landing"))

    if request.method == "POST":
        try:
            vitals = {
                "respiratory_rate":  int(request.form["respiratory_rate"]),
                "oxygen_saturation": int(request.form["oxygen_saturation"]),
                "o2_scale":          int(request.form["o2_scale"]),
                "systolic_bp":       int(request.form["systolic_bp"]),
                "heart_rate":        int(request.form["heart_rate"]),
                "temperature":       float(request.form["temperature"]),
                "consciousness":     request.form["consciousness"],
                "on_oxygen":         1 if request.form.get("on_oxygen") else 0,
            }
        except (ValueError, KeyError) as exc:
            errors = [f"Invalid input: {exc}"]
            return render_template("assessment.html", user=user,
                                   errors=errors, warnings=[], result=None)

        errors, warnings = validate_vitals(vitals)
        if not errors:
            try:
                result = submit_assessment(patient_id, vitals, user["id"])
            except RuntimeError as exc:
                errors = [str(exc)]

    return render_template("assessment.html", user=user,
                           errors=errors, warnings=warnings, result=result)


@patient_bp.route("/download-pdf/<int:assessment_id>")
@login_required
def download_pdf(assessment_id):
    user = get_current_user()
    data = get_assessment_for_pdf(assessment_id, user["id"])
    if not data:
        flash("Assessment not found.", "danger")
        return redirect(url_for("patient.dashboard"))

    pdf_bytes = generate_pdf(
        patient_info=data["patient_info"],
        assessment=data["assessment"],
        doctor_notes=data["doctor_notes"],
    )
    return Response(
        pdf_bytes, mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=assessment_{assessment_id}.pdf"},
    )
