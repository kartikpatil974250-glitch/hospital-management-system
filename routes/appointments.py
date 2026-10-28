"""Appointment Booking and Scheduling Routes for PulseCare HMS."""

from datetime import date
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from database.connection import execute_query
from extensions import get_current_user, login_required, role_required, validate_csrf
from services.appointment_service import book_appointment_concurrency_safe, cancel_appointment, get_available_slots

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")


@appointments_bp.route("/book", methods=["GET", "POST"])
@login_required
@role_required("patient")
def book():
    """Guided multi-step appointment booking workflow:

    1. Select department
    2. Select doctor
    3. Choose date
    4. Select available slot
    5. Enter reason
    6. Review & confirm
    """
    patient_id = session["user_id"]

    if request.method == "POST":
        validate_csrf()
        doctor_id = request.form.get("doctor_id", type=int)
        appointment_date = request.form.get("appointment_date", "").strip()
        start_time = request.form.get("start_time", "").strip()
        reason = request.form.get("reason", "").strip()

        if not doctor_id or not appointment_date or not start_time or not reason:
            flash("All appointment booking fields are required.", "danger")
            return redirect(url_for("appointments.book"))

        success, msg, app_id = book_appointment_concurrency_safe(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date_str=appointment_date,
            start_time_str=start_time,
            reason=reason
        )

        if success:
            flash(msg, "success")
            return redirect(url_for("appointments.confirmation", appointment_id=app_id))
        else:
            flash(msg, "danger")
            return redirect(url_for("appointments.book", doctor_id=doctor_id, date=appointment_date))

    # Pre-selection query parameters
    selected_doctor_id = request.args.get("doctor_id", type=int)
    selected_dept_id = request.args.get("department_id", type=int)

    departments = execute_query(
        "SELECT department_id, department_name FROM departments WHERE is_active = 1 ORDER BY department_name",
        fetch="all"
    ) or []

    doctors = execute_query(
        """
        SELECT doctor_id, full_name, specialization, department_id, consultation_fee
        FROM doctors 
        WHERE is_active = 1 
        ORDER BY full_name
        """,
        fetch="all"
    ) or []

    return render_template(
        "appointments/book.html",
        departments=departments,
        doctors=doctors,
        selected_doctor_id=selected_doctor_id,
        selected_dept_id=selected_dept_id,
        min_date=date.today().strftime("%Y-%m-%d")
    )


@appointments_bp.route("/api/slots")
def api_slots():
    """Asynchronous JSON endpoint returning slots for doctor on requested date."""
    doctor_id = request.args.get("doctor_id", type=int)
    date_str = request.args.get("date", "").strip()

    if not doctor_id or not date_str:
        return jsonify({"success": False, "message": "Doctor ID and date required.", "slots": []}), 400

    slots = get_available_slots(doctor_id, date_str)
    return jsonify({"success": True, "slots": slots})


@appointments_bp.route("/confirmation/<int:appointment_id>")
@login_required
def confirmation(appointment_id: int):
    """Displays confirmed appointment receipt with doctor, department, and billing details."""
    user = get_current_user()

    app_details = execute_query(
        """
        SELECT * FROM appointment_details_view WHERE appointment_id = %s
        """,
        (appointment_id,),
        fetch="one"
    )

    if not app_details:
        flash("Appointment not found.", "danger")
        return redirect(url_for("index"))

    # Access check: Patient can only view their own
    if user["role"] == "patient" and app_details["patient_id"] != user["id"]:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("patient.dashboard"))

    return render_template("appointments/confirmation.html", appointment=app_details)


@appointments_bp.route("/cancel/<int:appointment_id>", methods=["POST"])
@login_required
def cancel(appointment_id: int):
    """Cancels an appointment if authorized."""
    validate_csrf()
    user = get_current_user()
    reason = request.form.get("cancellation_reason", "Cancelled by user").strip()

    success, msg = cancel_appointment(
        appointment_id=appointment_id,
        user_id=user["id"],
        role=user["role"],
        cancellation_reason=reason
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    if user["role"] == "doctor":
        return redirect(url_for("doctor.appointments"))
    elif user["role"] == "admin":
        return redirect(url_for("admin.appointments"))
    return redirect(url_for("patient.appointments"))
