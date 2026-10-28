"""Medical Records Routes for PulseCare HMS."""

from flask import Blueprint, flash, redirect, render_template, session, url_for
from extensions import get_current_user, login_required
from services.medical_record_service import get_medical_record_by_id

medical_records_bp = Blueprint("medical_records", __name__, url_prefix="/medical-records")


@medical_records_bp.route("/<int:record_id>")
@login_required
def detail(record_id: int):
    """View clinical record with symptoms, diagnosis, treatment, and prescription."""
    user = get_current_user()
    record = get_medical_record_by_id(record_id, user_id=user["id"], role=user["role"])

    if not record:
        flash("Medical record not found or access unauthorized.", "danger")
        if user["role"] == "patient":
            return redirect(url_for("patient.medical_records"))
        elif user["role"] == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("admin.dashboard"))

    return render_template("medical_records/detail.html", record=record)
