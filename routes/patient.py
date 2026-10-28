"""Patient Portal Routes for PulseCare HMS."""

from datetime import date
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database.connection import execute_query
from extensions import get_current_user, login_required, role_required, validate_csrf

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")


@patient_bp.route("/dashboard")
@login_required
@role_required("patient")
def dashboard():
    """Renders personalized patient dashboard with real database metrics."""
    patient_id = session["user_id"]

    # 1. Next upcoming appointment
    next_appointment = execute_query(
        """
        SELECT 
            a.appointment_id, a.appointment_date, a.start_time, a.end_time, a.reason, a.status,
            d.full_name AS doctor_name, d.specialization, dept.department_name, dept.location
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE a.patient_id = %s 
          AND a.appointment_date >= CURDATE()
          AND a.status IN ('Scheduled', 'Confirmed')
        ORDER BY a.appointment_date ASC, a.start_time ASC
        LIMIT 1
        """,
        (patient_id,),
        fetch="one"
    )

    # 2. Recent appointments list (up to 5)
    recent_appointments = execute_query(
        """
        SELECT 
            a.appointment_id, a.appointment_date, a.start_time, a.status, a.reason,
            d.full_name AS doctor_name, d.specialization, dept.department_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.start_time DESC
        LIMIT 5
        """,
        (patient_id,),
        fetch="all"
    ) or []

    # 3. Outstanding bills count & total
    unpaid_summary = execute_query(
        """
        SELECT 
            COUNT(bill_id) AS unpaid_count,
            COALESCE(SUM(total_amount - amount_paid), 0) AS balance_due
        FROM bills
        WHERE patient_id = %s AND payment_status IN ('Unpaid', 'Partially Paid')
        """,
        (patient_id,),
        fetch="one"
    )

    # 4. Recent Prescriptions count
    recent_prescriptions = execute_query(
        """
        SELECT 
            p.prescription_id, p.prescription_date, d.full_name AS doctor_name,
            (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = p.prescription_id) AS item_count
        FROM prescriptions p
        JOIN doctors d ON p.doctor_id = d.doctor_id
        WHERE p.patient_id = %s
        ORDER BY p.prescription_date DESC
        LIMIT 3
        """,
        (patient_id,),
        fetch="all"
    ) or []

    # 5. Featured doctors list for immediate appointment booking from dashboard
    featured_doctors = execute_query(
        """
        SELECT 
            d.doctor_id, d.full_name, d.specialization, d.qualification,
            d.years_experience, d.consultation_fee, dept.department_name, dept.location
        FROM doctors d
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE d.is_active = 1
        ORDER BY d.doctor_id ASC
        LIMIT 6
        """,
        fetch="all"
    ) or []

    return render_template(
        "patient/dashboard.html",
        next_appointment=next_appointment,
        recent_appointments=recent_appointments,
        unpaid_summary=unpaid_summary or {"unpaid_count": 0, "balance_due": 0.0},
        recent_prescriptions=recent_prescriptions,
        featured_doctors=featured_doctors
    )


@patient_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("patient")
def profile():
    """Allows patient to view and update permitted contact information."""
    patient_id = session["user_id"]

    if request.method == "POST":
        validate_csrf()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()

        if not phone:
            flash("Phone number is required.", "danger")
        else:
            execute_query(
                """
                UPDATE patients 
                SET phone = %s, address = %s, emergency_contact = %s, updated_at = CURRENT_TIMESTAMP
                WHERE patient_id = %s
                """,
                (phone, address, emergency_contact, patient_id),
                commit=True
            )
            flash("Profile updated successfully.", "success")
            return redirect(url_for("patient.profile"))

    patient = execute_query(
        "SELECT * FROM patients WHERE patient_id = %s",
        (patient_id,),
        fetch="one"
    )
    return render_template("patient/profile.html", patient=patient)


@patient_bp.route("/doctors")
def doctors():
    """Browse doctor directory with search and department filtering."""
    dept_id = request.args.get("department_id", type=int)
    search_q = request.args.get("q", "").strip()

    sql = """
        SELECT 
            d.doctor_id, d.full_name, d.email, d.phone, d.specialization,
            d.qualification, d.years_experience, d.consultation_fee,
            d.profile_image, d.is_active,
            dept.department_name, dept.location
        FROM doctors d
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE d.is_active = 1
    """
    params = []

    if dept_id:
        sql += " AND d.department_id = %s"
        params.append(dept_id)

    if search_q:
        sql += " AND (d.full_name LIKE %s OR d.specialization LIKE %s OR dept.department_name LIKE %s)"
        like_term = f"%{search_q}%"
        params.extend([like_term, like_term, like_term])

    sql += " ORDER BY d.full_name ASC"
    doctors_list = execute_query(sql, tuple(params), fetch="all") or []

    departments_list = execute_query(
        "SELECT department_id, department_name FROM departments WHERE is_active = 1 ORDER BY department_name",
        fetch="all"
    ) or []

    return render_template(
        "patient/doctors.html",
        doctors=doctors_list,
        departments=departments_list,
        selected_dept=dept_id,
        search_query=search_q
    )


@patient_bp.route("/departments")
def departments():
    """Hospital department listing and staff directory."""
    depts = execute_query(
        """
        SELECT 
            dept.department_id, dept.department_name, dept.description, dept.location, dept.contact_number,
            COUNT(d.doctor_id) AS doctor_count
        FROM departments dept
        LEFT JOIN doctors d ON dept.department_id = d.department_id AND d.is_active = 1
        WHERE dept.is_active = 1
        GROUP BY dept.department_id, dept.department_name, dept.description, dept.location, dept.contact_number
        ORDER BY dept.department_name
        """,
        fetch="all"
    ) or []
    return render_template("patient/departments.html", departments=depts)


@patient_bp.route("/appointments")
@login_required
@role_required("patient")
def appointments():
    """Lists all upcoming and past appointments for logged-in patient."""
    patient_id = session["user_id"]
    apps = execute_query(
        """
        SELECT 
            a.appointment_id, a.appointment_date, a.start_time, a.end_time, a.reason,
            a.status, a.cancellation_reason, a.created_at,
            d.full_name AS doctor_name, d.specialization, d.consultation_fee,
            dept.department_name,
            b.bill_id, b.payment_status, b.total_amount
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        LEFT JOIN bills b ON a.appointment_id = b.appointment_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.start_time DESC
        """,
        (patient_id,),
        fetch="all"
    ) or []
    return render_template("patient/appointments.html", appointments=apps)


@patient_bp.route("/medical-records")
@login_required
@role_required("patient")
def medical_records():
    """View patient's clinical visit records."""
    patient_id = session["user_id"]
    records = execute_query(
        """
        SELECT 
            r.record_id, r.visit_date, r.symptoms, r.diagnosis, r.treatment_notes, r.follow_up_date,
            d.full_name AS doctor_name, d.specialization, dept.department_name,
            p.prescription_id
        FROM medical_records r
        JOIN doctors d ON r.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        LEFT JOIN prescriptions p ON r.record_id = p.medical_record_id
        WHERE r.patient_id = %s
        ORDER BY r.visit_date DESC
        """,
        (patient_id,),
        fetch="all"
    ) or []
    return render_template("patient/medical_records.html", records=records)


@patient_bp.route("/prescriptions")
@login_required
@role_required("patient")
def prescriptions():
    """View patient's prescribed medications."""
    patient_id = session["user_id"]
    presc_list = execute_query(
        """
        SELECT 
            p.prescription_id, p.prescription_date, p.instructions,
            d.full_name AS doctor_name, d.specialization, dept.department_name,
            r.diagnosis,
            (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = p.prescription_id) AS items_count
        FROM prescriptions p
        JOIN doctors d ON p.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        JOIN medical_records r ON p.medical_record_id = r.record_id
        WHERE p.patient_id = %s
        ORDER BY p.prescription_date DESC
        """,
        (patient_id,),
        fetch="all"
    ) or []
    return render_template("patient/prescriptions.html", prescriptions=presc_list)


@patient_bp.route("/bills")
@login_required
@role_required("patient")
def bills():
    """View patient invoices and payment histories."""
    patient_id = session["user_id"]
    bill_list = execute_query(
        """
        SELECT 
            b.bill_id, b.appointment_id, b.consultation_fee, b.additional_charges, b.discount,
            b.total_amount, b.amount_paid, (b.total_amount - b.amount_paid) AS balance,
            b.payment_status, b.created_at,
            a.appointment_date,
            d.full_name AS doctor_name,
            dept.department_name
        FROM bills b
        JOIN appointments a ON b.appointment_id = a.appointment_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE b.patient_id = %s
        ORDER BY b.created_at DESC
        """,
        (patient_id,),
        fetch="all"
    ) or []
    return render_template("patient/bills.html", bills=bill_list)
