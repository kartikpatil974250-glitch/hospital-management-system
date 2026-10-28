"""Administrator Portal Routes for PulseCare HMS.

Hospital-wide management: Doctors, Patients, Departments, Appointments,
Billing, System Statistics, and Trigger Audit Logs.
"""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database.connection import execute_query
from extensions import hash_password, login_required, role_required, validate_csrf

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    """Renders hospital-wide dashboard computed directly from MySQL database tables."""
    # 1. High-level metric counts
    stats = execute_query(
        """
        SELECT 
            (SELECT COUNT(*) FROM patients) AS total_patients,
            (SELECT COUNT(*) FROM doctors) AS total_doctors,
            (SELECT COUNT(*) FROM departments) AS total_departments,
            (SELECT COUNT(*) FROM appointments WHERE appointment_date = CURDATE()) AS today_appointments,
            (SELECT COUNT(*) FROM appointments WHERE appointment_date > CURDATE() AND status IN ('Scheduled', 'Confirmed')) AS upcoming_appointments,
            (SELECT COUNT(*) FROM appointments WHERE status = 'Completed') AS completed_appointments,
            (SELECT COUNT(*) FROM appointments WHERE status = 'Cancelled') AS cancelled_appointments,
            (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_status = 'Success') AS total_payments,
            (SELECT COALESCE(SUM(total_amount - amount_paid), 0) FROM bills) AS outstanding_balance
        """,
        fetch="one"
    ) or {}

    # 2. Today's appointment schedule
    today_schedule = execute_query(
        """
        SELECT 
            a.appointment_id, a.start_time, a.end_time, a.status,
            p.full_name AS patient_name,
            d.full_name AS doctor_name,
            dept.department_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE a.appointment_date = CURDATE()
        ORDER BY a.start_time ASC
        """,
        fetch="all"
    ) or []

    # 3. Recent patient registrations
    recent_patients = execute_query(
        """
        SELECT patient_id, full_name, email, phone, gender, created_at
        FROM patients
        ORDER BY created_at DESC
        LIMIT 5
        """,
        fetch="all"
    ) or []

    # 4. Status distribution counts for appointments
    status_distribution = execute_query(
        """
        SELECT status, COUNT(*) AS count
        FROM appointments
        GROUP BY status
        """,
        fetch="all"
    ) or []

    # 5. Recent billing and payment activity
    recent_payments = execute_query(
        """
        SELECT 
            p.payment_id, p.amount, p.payment_method, p.payment_date, p.transaction_reference,
            b.bill_id, pt.full_name AS patient_name
        FROM payments p
        JOIN bills b ON p.bill_id = b.bill_id
        JOIN patients pt ON b.patient_id = pt.patient_id
        ORDER BY p.payment_date DESC
        LIMIT 5
        """,
        fetch="all"
    ) or []

    # 6. Active hospital specialists roster
    doctors_roster = execute_query(
        """
        SELECT 
            d.doctor_id, d.full_name, d.specialization, d.qualification,
            d.years_experience, d.consultation_fee, d.is_active,
            dept.department_name
        FROM doctors d
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE d.is_active = 1
        ORDER BY d.doctor_id ASC
        LIMIT 8
        """,
        fetch="all"
    ) or []

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        today_schedule=today_schedule,
        recent_patients=recent_patients,
        status_distribution=status_distribution,
        recent_payments=recent_payments,
        doctors_roster=doctors_roster
    )


@admin_bp.route("/doctors", methods=["GET", "POST"])
@login_required
@role_required("admin")
def doctors():
    """Add and manage doctor profiles."""
    if request.method == "POST":
        validate_csrf()
        action = request.form.get("action")

        if action == "add_doctor":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            specialization = request.form.get("specialization", "").strip()
            department_id = request.form.get("department_id", type=int)
            qualification = request.form.get("qualification", "").strip()
            years_experience = request.form.get("years_experience", 0, type=int)
            fee = request.form.get("consultation_fee", 50.0, type=float)
            password = request.form.get("password", "Doctor@123")

            if not full_name or not email or not phone or not specialization or not department_id:
                flash("All required doctor fields must be filled.", "danger")
            else:
                existing = execute_query("SELECT doctor_id FROM doctors WHERE email = %s", (email,), fetch="one")
                if existing:
                    flash("A doctor with this email address already exists.", "danger")
                else:
                    pwhash = hash_password(password)
                    try:
                        execute_query(
                            """
                            INSERT INTO doctors (full_name, email, phone, specialization, department_id, qualification, years_experience, consultation_fee, password_hash, is_active)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                            """,
                            (full_name, email, phone, specialization, department_id, qualification, years_experience, fee, pwhash),
                            commit=True
                        )
                        flash(f"Doctor {full_name} successfully registered.", "success")
                        return redirect(url_for("admin.doctors"))
                    except Exception as e:
                        flash(f"Error adding doctor: {str(e)}", "danger")

        elif action == "toggle_active":
            doctor_id = request.form.get("doctor_id", type=int)
            current_status = request.form.get("current_status", type=int)
            new_status = 0 if current_status == 1 else 1

            execute_query(
                "UPDATE doctors SET is_active = %s WHERE doctor_id = %s",
                (new_status, doctor_id),
                commit=True
            )
            flash(f"Doctor status updated to {'Active' if new_status else 'Inactive'}.", "success")
            return redirect(url_for("admin.doctors"))

    doctors_list = execute_query(
        """
        SELECT 
            d.doctor_id, d.full_name, d.email, d.phone, d.specialization,
            d.qualification, d.years_experience, d.consultation_fee, d.is_active, d.created_at,
            dept.department_name
        FROM doctors d
        JOIN departments dept ON d.department_id = dept.department_id
        ORDER BY d.created_at DESC
        """,
        fetch="all"
    ) or []

    departments_list = execute_query(
        "SELECT department_id, department_name FROM departments WHERE is_active = 1 ORDER BY department_name",
        fetch="all"
    ) or []

    return render_template("admin/doctors.html", doctors=doctors_list, departments=departments_list)


@admin_bp.route("/patients")
@login_required
@role_required("admin")
def patients():
    """Lists all registered patients."""
    search_q = request.args.get("q", "").strip()

    sql = """
        SELECT 
            p.patient_id, p.full_name, p.email, p.phone, p.date_of_birth, p.gender,
            p.emergency_contact, p.created_at,
            COUNT(a.appointment_id) AS total_visits
        FROM patients p
        LEFT JOIN appointments a ON p.patient_id = a.patient_id
    """
    params = []
    if search_q:
        sql += " WHERE p.full_name LIKE %s OR p.email LIKE %s OR p.phone LIKE %s"
        like_term = f"%{search_q}%"
        params.extend([like_term, like_term, like_term])

    sql += " GROUP BY p.patient_id, p.full_name, p.email, p.phone, p.date_of_birth, p.gender, p.emergency_contact, p.created_at ORDER BY p.created_at DESC"
    patient_list = execute_query(sql, tuple(params), fetch="all") or []

    return render_template("admin/patients.html", patients=patient_list, search_query=search_q)


@admin_bp.route("/departments", methods=["GET", "POST"])
@login_required
@role_required("admin")
def departments():
    """Lists and adds departments."""
    if request.method == "POST":
        validate_csrf()
        name = request.form.get("department_name", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        contact = request.form.get("contact_number", "").strip()

        if not name:
            flash("Department name is required.", "danger")
        else:
            try:
                execute_query(
                    """
                    INSERT INTO departments (department_name, description, location, contact_number, is_active)
                    VALUES (%s, %s, %s, %s, 1)
                    """,
                    (name, description, location, contact),
                    commit=True
                )
                flash(f"Department '{name}' created successfully.", "success")
                return redirect(url_for("admin.departments"))
            except Exception as e:
                flash(f"Error creating department: {str(e)}", "danger")

    dept_list = execute_query(
        """
        SELECT 
            dept.department_id, dept.department_name, dept.description, dept.location,
            dept.contact_number, dept.is_active,
            COUNT(d.doctor_id) AS doctor_count
        FROM departments dept
        LEFT JOIN doctors d ON dept.department_id = d.department_id
        GROUP BY dept.department_id, dept.department_name, dept.description, dept.location, dept.contact_number, dept.is_active
        ORDER BY dept.department_name ASC
        """,
        fetch="all"
    ) or []

    return render_template("admin/departments.html", departments=dept_list)


@admin_bp.route("/appointments")
@login_required
@role_required("admin")
def appointments():
    """Hospital appointment management with status audit trail."""
    status_filter = request.args.get("status", "")

    sql = """
        SELECT * FROM appointment_details_view
    """
    params = []
    if status_filter:
        sql += " WHERE status = %s"
        params.append(status_filter)

    sql += " ORDER BY appointment_date DESC, start_time DESC LIMIT 100"
    apps = execute_query(sql, tuple(params), fetch="all") or []

    # Fetch recent audit logs populated by the MySQL Trigger
    audit_logs = execute_query(
        """
        SELECT audit_id, appointment_id, old_status, new_status, changed_at, remarks
        FROM audit_appointment_logs
        ORDER BY changed_at DESC
        LIMIT 20
        """,
        fetch="all"
    ) or []

    return render_template("admin/appointments.html", appointments=apps, audit_logs=audit_logs, current_status=status_filter)


@admin_bp.route("/billing")
@login_required
@role_required("admin")
def billing():
    """Hospital revenue overview, billing list, and payment records."""
    summary = execute_query(
        """
        SELECT 
            COALESCE(SUM(total_amount), 0) AS total_billed,
            COALESCE(SUM(amount_paid), 0) AS total_collected,
            COALESCE(SUM(total_amount - amount_paid), 0) AS total_outstanding,
            COUNT(bill_id) AS total_bills
        FROM bills
        """,
        fetch="one"
    ) or {}

    bills = execute_query(
        """
        SELECT 
            b.bill_id, b.patient_id, b.appointment_id, b.consultation_fee,
            b.additional_charges, b.discount, b.total_amount, b.amount_paid,
            (b.total_amount - b.amount_paid) AS balance,
            b.payment_status, b.created_at,
            p.full_name AS patient_name,
            d.full_name AS doctor_name
        FROM bills b
        JOIN patients p ON b.patient_id = p.patient_id
        LEFT JOIN appointments a ON b.appointment_id = a.appointment_id
        LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY b.created_at DESC
        LIMIT 50
        """,
        fetch="all"
    ) or []

    return render_template("admin/billing.html", summary=summary, bills=bills)


@admin_bp.route("/billing/update/<int:bill_id>", methods=["POST"])
@login_required
@role_required("admin")
def update_bill(bill_id: int):
    """Updates bill additional charges and discounts, recomputing totals atomically."""
    validate_csrf()
    additional = request.form.get("additional_charges", 0.0, type=float)
    discount = request.form.get("discount", 0.0, type=float)

    bill = execute_query("SELECT consultation_fee, amount_paid FROM bills WHERE bill_id = %s", (bill_id,), fetch="one")
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("admin.billing"))

    fee = float(bill["consultation_fee"])
    paid = float(bill["amount_paid"])
    new_total = max(0.0, round(fee + additional - discount, 2))
    new_status = "Paid" if paid >= new_total and new_total > 0 else ("Partially Paid" if paid > 0 else "Unpaid")

    execute_query(
        """
        UPDATE bills
        SET additional_charges = %s, discount = %s, total_amount = %s, payment_status = %s
        WHERE bill_id = %s
        """,
        (additional, discount, new_total, new_status, bill_id),
        commit=True
    )
    flash(f"Invoice #INV-{bill_id} adjusted. New total: ${new_total:.2f}.", "success")
    return redirect(url_for("billing.detail", bill_id=bill_id))


@admin_bp.route("/doctors/edit/<int:doctor_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_doctor(doctor_id: int):
    """Allows administrator to update doctor clinical details."""
    if request.method == "POST":
        validate_csrf()
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        specialization = request.form.get("specialization", "").strip()
        department_id = request.form.get("department_id", type=int)
        qualification = request.form.get("qualification", "").strip()
        years_exp = request.form.get("years_experience", 0, type=int)
        fee = request.form.get("consultation_fee", 50.0, type=float)

        execute_query(
            """
            UPDATE doctors
            SET full_name = %s, phone = %s, specialization = %s, department_id = %s,
                qualification = %s, years_experience = %s, consultation_fee = %s
            WHERE doctor_id = %s
            """,
            (full_name, phone, specialization, department_id, qualification, years_exp, fee, doctor_id),
            commit=True
        )
        flash("Doctor credentials updated successfully.", "success")
        return redirect(url_for("admin.doctors"))

    doc = execute_query("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,), fetch="one")
    if not doc:
        flash("Doctor not found.", "danger")
        return redirect(url_for("admin.doctors"))

    departments_list = execute_query("SELECT department_id, department_name FROM departments WHERE is_active = 1", fetch="all") or []
    return render_template("admin/edit_doctor.html", doctor=doc, departments=departments_list)


@admin_bp.route("/reports")
@login_required
@role_required("admin")
def reports():
    """Aggregated clinical, operational, and financial reports from database queries."""
    # 1. Departmental workload & revenue breakdown
    dept_reports = execute_query(
        """
        SELECT 
            dept.department_name,
            COUNT(DISTINCT a.appointment_id) AS total_appointments,
            COUNT(DISTINCT d.doctor_id) AS doctor_count,
            COALESCE(SUM(b.total_amount), 0) AS total_billed,
            COALESCE(SUM(b.amount_paid), 0) AS total_collected
        FROM departments dept
        LEFT JOIN doctors d ON dept.department_id = d.department_id
        LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
        LEFT JOIN bills b ON a.appointment_id = b.appointment_id
        GROUP BY dept.department_id, dept.department_name
        ORDER BY total_billed DESC
        """,
        fetch="all"
    ) or []

    # 2. Doctor consultation workload
    doctor_workload = execute_query(
        """
        SELECT 
            d.full_name, d.specialization, dept.department_name,
            COUNT(a.appointment_id) AS total_appointments,
            COUNT(CASE WHEN a.status = 'Completed' THEN 1 END) AS completed_count,
            COUNT(CASE WHEN a.status = 'Cancelled' THEN 1 END) AS cancelled_count
        FROM doctors d
        JOIN departments dept ON d.department_id = dept.department_id
        LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
        GROUP BY d.doctor_id, d.full_name, d.specialization, dept.department_name
        ORDER BY completed_count DESC
        """,
        fetch="all"
    ) or []

    # 3. Top clinical diagnoses
    top_diagnoses = execute_query(
        """
        SELECT diagnosis, COUNT(*) AS case_count
        FROM medical_records
        GROUP BY diagnosis
        ORDER BY case_count DESC
        LIMIT 8
        """,
        fetch="all"
    ) or []

    return render_template(
        "admin/reports.html",
        dept_reports=dept_reports,
        doctor_workload=doctor_workload,
        top_diagnoses=top_diagnoses
    )

