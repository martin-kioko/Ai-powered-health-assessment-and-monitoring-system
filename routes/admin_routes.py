from flask import Blueprint, render_template, redirect, url_for, flash
from auth import role_required, get_current_user
from services.admin_service import get_admin_dashboard_data, toggle_user_active

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@role_required("admin")
def dashboard():
    user = get_current_user()
    data = get_admin_dashboard_data()
    return render_template("admin_dashboard.html", user=user, **data)


@admin_bp.route("/admin/toggle/<int:user_id>", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    current = get_current_user()
    ok, message = toggle_user_active(user_id, current["id"])
    flash(message, "success" if ok else "warning")
    return redirect(url_for("admin.dashboard"))
