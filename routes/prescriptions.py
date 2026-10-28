"""Prescription Routes for PulseCare HMS."""

from flask import Blueprint, flash, redirect, render_template, url_for
from database.connection import execute_query
from extensions import get_current_user, login_required

prescriptions_bp = Blueprint("prescriptions", __name__, url_prefix="/prescriptions")


@prescriptions_bp.route("/<int:prescription_id>")
@login_required
def detail(prescription_id: int):
    """View and print prescription with medications, dosages, and clinician signature block."""
    user = get_current_user()

    prescription = execute_query(
        """
        SELECT 
            p.prescription_id, p.medical_record_id, p.patient_id, p.doctor_id,
            p.prescription_date, p.instructions, p.created_at,
            pt.full_name AS patient_name, pt.date_of_birth AS patient_dob, pt.gender AS patient_gender,
            pt.phone AS patient_phone,
            d.full_name AS doctor_name, d.specialization, d.qualification,
            dept.department_name, dept.location AS department_location,
            r.diagnosis, r.allergies
        FROM prescriptions p
        JOIN patients pt ON p.patient_id = pt.patient_id
        JOIN doctors d ON p.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        JOIN medical_records r ON p.medical_record_id = r.record_id
        WHERE p.prescription_id = %s
        """,
        (prescription_id,),
        fetch="one"
    )

    if not prescription:
        flash("Prescription not found.", "danger")
        return redirect(url_for("index"))

    # Patient privacy check
    if user["role"] == "patient" and prescription["patient_id"] != user["id"]:
        flash("Unauthorized access to this prescription.", "danger")
        return redirect(url_for("patient.prescriptions"))

    items = execute_query(
        """
        SELECT item_id, medication_name, dosage, frequency, duration, instructions
        FROM prescription_items
        WHERE prescription_id = %s
        ORDER BY item_id ASC
        """,
        (prescription_id,),
        fetch="all"
    ) or []

    prescription["items"] = items
    prescription["medication_items"] = items

    return render_template("prescriptions/detail.html", prescription=prescription)
