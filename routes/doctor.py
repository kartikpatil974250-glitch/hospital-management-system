"""Doctor Portal Routes for PulseCare HMS."""

from datetime import date, datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database.connection import execute_query, execute_stored_procedure
from extensions import login_required, role_required, validate_csrf
from services.medical_record_service import create_medical_record_and_prescription

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")


@doctor_bp.route("/dashboard")
@login_required
@role_required("doctor")
def dashboard():
    """Renders doctor's daily clinical overview with real database stats."""
    doctor_id = session["user_id"]

    # Today's appointments
    today_apps = execute_query(
        """
        SELECT 
            a.appointment_id, a.start_time, a.end_time, a.reason, a.status,
            p.patient_id, p.full_name AS patient_name, p.gender, p.date_of_birth, p.phone
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.doctor_id = %s AND a.appointment_date = CURDATE()
        ORDER BY a.start_time ASC
        """,
        (doctor_id,),
        fetch="all"
    ) or []

    # Aggregated Stats via Stored Procedure or Direct SQL
    stats_list = execute_stored_procedure("sp_get_doctor_schedule_stats", (doctor_id,))
    stats = stats_list[0] if stats_list else {
        "today_appointments": len(today_apps),
        "upcoming_appointments": 0,
        "completed_consultations": 0,
        "total_unique_patients": 0
    }

    # Upcoming Appointments for next 7 days
    upcoming_apps = execute_query(
        """
        SELECT 
            a.appointment_id, a.appointment_date, a.start_time, a.reason, a.status,
            p.full_name AS patient_name, p.phone
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.doctor_id = %s 
          AND a.appointment_date > CURDATE()
          AND a.status IN ('Scheduled', 'Confirmed')
        ORDER BY a.appointment_date ASC, a.start_time ASC
        LIMIT 5
        """,
        (doctor_id,),
        fetch="all"
    ) or []

    return render_template(
        "doctor/dashboard.html",
        today_appointments=today_apps,
        stats=stats,
        upcoming_appointments=upcoming_apps
    )


@doctor_bp.route("/appointments")
@login_required
@role_required("doctor")
def appointments():
    """List of all consultations assigned to this doctor."""
    doctor_id = session["user_id"]
    status_filter = request.args.get("status", "")

    sql = """
        SELECT 
            a.appointment_id, a.appointment_date, a.start_time, a.end_time, a.reason,
            a.status, a.cancellation_reason,
            p.patient_id, p.full_name AS patient_name, p.phone, p.gender, p.date_of_birth,
            m.record_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        LEFT JOIN medical_records m ON a.appointment_id = m.appointment_id
        WHERE a.doctor_id = %s
    """
    params = [doctor_id]

    if status_filter:
        sql += " AND a.status = %s"
        params.append(status_filter)

    sql += " ORDER BY a.appointment_date DESC, a.start_time DESC"
    doctor_apps = execute_query(sql, tuple(params), fetch="all") or []

    return render_template("doctor/appointments.html", appointments=doctor_apps, current_status=status_filter)


@doctor_bp.route("/appointments/<int:appointment_id>/no-show", methods=["POST"])
@login_required
@role_required("doctor")
def mark_no_show(appointment_id: int):
    """Marks an appointment as No-show when authorized."""
    validate_csrf()
    doctor_id = session["user_id"]

    # Verify authorization
    app = execute_query(
        "SELECT * FROM appointments WHERE appointment_id = %s AND doctor_id = %s",
        (appointment_id, doctor_id),
        fetch="one"
    )

    if not app:
        flash("Consultation not found or access denied.", "danger")
        return redirect(url_for("doctor.appointments"))

    if app["status"] in ("Completed", "Cancelled"):
        flash(f"Cannot mark {app['status']} appointment as no-show.", "danger")
        return redirect(url_for("doctor.appointments"))

    execute_query(
        """
        UPDATE appointments 
        SET status = 'No-show', updated_at = CURRENT_TIMESTAMP
        WHERE appointment_id = %s
        """,
        (appointment_id,),
        commit=True
    )
    flash("Appointment has been marked as No-show.", "info")
    return redirect(url_for("doctor.appointments"))


@doctor_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def profile():
    """Allows doctor to view and update permitted profile information."""
    doctor_id = session["user_id"]

    if request.method == "POST":
        validate_csrf()
        phone = request.form.get("phone", "").strip()
        qualification = request.form.get("qualification", "").strip()
        years_exp = request.form.get("years_experience", 0, type=int)
        fee = request.form.get("consultation_fee", 50.0, type=float)

        if not phone:
            flash("Phone number is required.", "danger")
        else:
            execute_query(
                """
                UPDATE doctors
                SET phone = %s, qualification = %s, years_experience = %s, consultation_fee = %s
                WHERE doctor_id = %s
                """,
                (phone, qualification, years_exp, fee, doctor_id),
                commit=True
            )
            flash("Doctor profile updated successfully.", "success")
            return redirect(url_for("doctor.profile"))

    doctor = execute_query(
        """
        SELECT d.*, dept.department_name
        FROM doctors d
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE d.doctor_id = %s
        """,
        (doctor_id,),
        fetch="one"
    )
    return render_template("doctor/profile.html", doctor=doctor)



@doctor_bp.route("/consultation/<int:appointment_id>", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def consultation(appointment_id: int):
    """Clinical consultation interface to examine patient, record diagnosis,

    and prescribe medications.
    """
    doctor_id = session["user_id"]

    # Verify appointment belongs to this doctor
    app_info = execute_query(
        """
        SELECT 
            a.appointment_id, a.appointment_date, a.start_time, a.reason, a.status,
            p.patient_id, p.full_name AS patient_name, p.date_of_birth, p.gender, p.phone, p.emergency_contact
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.appointment_id = %s AND a.doctor_id = %s
        """,
        (appointment_id, doctor_id),
        fetch="one"
    )

    if not app_info:
        flash("Consultation not found or access denied.", "danger")
        return redirect(url_for("doctor.appointments"))

    # Check if record already exists
    existing_record = execute_query(
        "SELECT record_id FROM medical_records WHERE appointment_id = %s",
        (appointment_id,),
        fetch="one"
    )

    if request.method == "POST":
        validate_csrf()
        symptoms = request.form.get("symptoms", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        treatment_notes = request.form.get("treatment_notes", "").strip()
        allergies = request.form.get("allergies", "").strip()
        follow_up_date = request.form.get("follow_up_date", "").strip()
        instructions = request.form.get("instructions", "").strip()

        # Parse dynamic medication items
        med_names = request.form.getlist("med_name[]")
        med_dosages = request.form.getlist("med_dosage[]")
        med_freqs = request.form.getlist("med_freq[]")
        med_durs = request.form.getlist("med_duration[]")
        med_notes = request.form.getlist("med_instructions[]")

        med_items = []
        for i in range(len(med_names)):
            if med_names[i].strip():
                med_items.append({
                    "medication_name": med_names[i].strip(),
                    "dosage": med_dosages[i].strip() if i < len(med_dosages) else "",
                    "frequency": med_freqs[i].strip() if i < len(med_freqs) else "",
                    "duration": med_durs[i].strip() if i < len(med_durs) else "",
                    "instructions": med_notes[i].strip() if i < len(med_notes) else ""
                })

        success, msg, rec_id = create_medical_record_and_prescription(
            doctor_id=doctor_id,
            patient_id=app_info["patient_id"],
            appointment_id=appointment_id,
            visit_date_str=str(app_info["appointment_date"]),
            symptoms=symptoms,
            diagnosis=diagnosis,
            treatment_notes=treatment_notes,
            allergies=allergies,
            follow_up_date_str=follow_up_date,
            prescription_instructions=instructions,
            medication_items=med_items
        )

        if success:
            flash(msg, "success")
            return redirect(url_for("doctor.appointments"))
        else:
            flash(msg, "danger")

    # Fetch patient's past medical history
    history = execute_query(
        """
        SELECT record_id, visit_date, symptoms, diagnosis, treatment_notes
        FROM medical_records
        WHERE patient_id = %s AND appointment_id != %s
        ORDER BY visit_date DESC
        """,
        (app_info["patient_id"], appointment_id),
        fetch="all"
    ) or []

    return render_template(
        "doctor/consultation.html",
        appointment=app_info,
        existing_record=existing_record,
        patient_history=history
    )


@doctor_bp.route("/schedule", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def schedule():
    """Manage weekly clinic hours and block off unavailable dates/leaves."""
    doctor_id = session["user_id"]

    if request.method == "POST":
        validate_csrf()
        action = request.form.get("action")

        if action == "update_schedule":
            day = request.form.get("day_of_week")
            start = request.form.get("start_time")
            end = request.form.get("end_time")
            slot_duration = request.form.get("slot_duration", 30, type=int)
            is_avail = 1 if request.form.get("is_available") == "1" else 0

            if start >= end:
                flash("Schedule end time must be after start time.", "danger")
            else:
                execute_query(
                    """
                    INSERT INTO doctor_schedules (doctor_id, day_of_week, start_time, end_time, slot_duration, is_available)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE start_time=VALUES(start_time), end_time=VALUES(end_time),
                        slot_duration=VALUES(slot_duration), is_available=VALUES(is_available)
                    """,
                    (doctor_id, day, start, end, slot_duration, is_avail),
                    commit=True
                )
                flash(f"Clinic schedule for {day} updated successfully.", "success")
                return redirect(url_for("doctor.schedule"))

        elif action == "add_unavailability":
            start_dt = request.form.get("start_datetime")
            end_dt = request.form.get("end_datetime")
            reason = request.form.get("reason", "").strip()

            if not start_dt or not end_dt or start_dt >= end_dt:
                flash("End date/time must be strictly after start date/time.", "danger")
            else:
                execute_query(
                    """
                    INSERT INTO doctor_unavailability (doctor_id, start_datetime, end_datetime, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (doctor_id, start_dt, end_dt, reason),
                    commit=True
                )
                flash("Leave/unavailability block recorded.", "success")
                return redirect(url_for("doctor.schedule"))

    schedules = execute_query(
        "SELECT * FROM doctor_schedules WHERE doctor_id = %s ORDER BY schedule_id",
        (doctor_id,),
        fetch="all"
    ) or []

    unavailabilities = execute_query(
        "SELECT * FROM doctor_unavailability WHERE doctor_id = %s ORDER BY start_datetime DESC",
        (doctor_id,),
        fetch="all"
    ) or []

    return render_template("doctor/schedule.html", schedules=schedules, unavailabilities=unavailabilities)
