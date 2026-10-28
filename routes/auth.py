"""Authentication Routes for PulseCare HMS.

Handles patient registration, role-based login (Patient, Doctor, Admin), and session logout.
"""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database.connection import execute_query
from extensions import (
    get_current_user,
    hash_password,
    login_user,
    logout_user,
    validate_csrf,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Allows new patients or doctors to register with validation."""
    if get_current_user():
        return redirect(url_for("index"))

    # Fetch active departments for doctor registration dropdown
    departments = execute_query(
        "SELECT department_id, department_name FROM departments WHERE is_active = 1 ORDER BY department_name ASC",
        fetch="all"
    ) or []

    default_role = request.args.get("role", "patient").lower()
    if default_role not in ("patient", "doctor"):
        default_role = "patient"

    if request.method == "POST":
        validate_csrf()
        role = request.form.get("role", "patient").lower()

        if role == "doctor":
            full_name = request.form.get("full_name", "").strip()
            if full_name and not full_name.lower().startswith("dr.") and not full_name.lower().startswith("dr "):
                full_name = f"Dr. {full_name}"

            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            department_id = request.form.get("department_id", type=int)
            specialization = request.form.get("specialization", "").strip()
            qualification = request.form.get("qualification", "").strip()
            years_experience = request.form.get("years_experience", 0, type=int)
            consultation_fee = request.form.get("consultation_fee", 75.0, type=float)
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            # Validation
            if not full_name or not email or not phone or not department_id or not specialization or not qualification or not password:
                flash("All required clinician fields must be filled.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="doctor")

            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="doctor")

            if len(password) < 6:
                flash("Password must be at least 6 characters long.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="doctor")

            existing = execute_query("SELECT doctor_id FROM doctors WHERE email = %s", (email,), fetch="one")
            if existing:
                flash("A doctor account with this email address already exists.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="doctor")

            pwhash = hash_password(password)
            try:
                doctor_id = execute_query(
                    """
                    INSERT INTO doctors (full_name, email, phone, specialization, department_id, qualification, years_experience, consultation_fee, password_hash, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """,
                    (full_name, email, phone, specialization, department_id, qualification, years_experience, consultation_fee, pwhash),
                    commit=True
                )

                # Initialize standard Monday-Friday weekly availability schedules
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                for day in days:
                    try:
                        execute_query(
                            """
                            INSERT INTO doctor_schedules (doctor_id, day_of_week, start_time, end_time, slot_duration, is_available)
                            VALUES (%s, %s, '09:00:00', '17:00:00', 30, 1)
                            """,
                            (doctor_id, day),
                            commit=True
                        )
                    except Exception:
                        pass

                flash(f"Doctor account for {full_name} successfully registered! You can now sign in.", "success")
                return redirect(url_for("auth.login", role="doctor"))
            except Exception as e:
                flash(f"Error registering doctor account: {str(e)}", "danger")
                return render_template("auth/register.html", departments=departments, default_role="doctor")

        else:  # Patient registration
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            dob = request.form.get("date_of_birth", "").strip()
            gender = request.form.get("gender", "").strip()
            address = request.form.get("address", "").strip()
            emergency_contact = request.form.get("emergency_contact", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            # Form validation
            if not full_name or not email or not phone or not dob or not gender or not password:
                flash("All required patient fields must be filled.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="patient")

            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="patient")

            if len(password) < 6:
                flash("Password must be at least 6 characters long.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="patient")

            # Check existing email in patients table
            existing = execute_query(
                "SELECT patient_id FROM patients WHERE email = %s",
                (email,),
                fetch="one"
            )
            if existing:
                flash("An account with this email address already exists.", "danger")
                return render_template("auth/register.html", departments=departments, default_role="patient")

            # Insert new patient with hashed password
            pwhash = hash_password(password)
            try:
                patient_id = execute_query(
                    """
                    INSERT INTO patients (full_name, email, phone, date_of_birth, gender, address, emergency_contact, password_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (full_name, email, phone, dob, gender, address, emergency_contact, pwhash),
                    commit=True
                )
                flash("Registration successful! You may now sign in.", "success")
                return redirect(url_for("auth.login", role="patient"))
            except Exception as e:
                flash(f"Error registering patient account: {str(e)}", "danger")
                return render_template("auth/register.html", departments=departments, default_role="patient")

    return render_template("auth/register.html", departments=departments, default_role=default_role)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Universal login endpoint supporting Patient, Doctor, and Administrator roles."""
    if get_current_user():
        role = session.get("role")
        if role == "patient":
            return redirect(url_for("patient.dashboard"))
        elif role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        elif role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("index"))

    if request.method == "POST":
        validate_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        requested_role = request.form.get("role", "patient")  # 'patient', 'doctor', 'admin'

        if not email or not password:
            flash("Please provide both email address and password.", "danger")
            return render_template("auth/login.html")

        # Authenticate based on role
        if requested_role == "admin":
            user = execute_query(
                "SELECT admin_id, full_name, email, password_hash, role FROM admins WHERE email = %s",
                (email,),
                fetch="one"
            )
            if user and verify_password(user["password_hash"], password):
                login_user(user["admin_id"], "admin", user["full_name"], user["email"])
                flash(f"Welcome back, Administrator {user['full_name']}!", "success")
                return redirect(url_for("admin.dashboard"))

        elif requested_role == "doctor":
            user = execute_query(
                "SELECT doctor_id, full_name, email, password_hash, is_active FROM doctors WHERE email = %s",
                (email,),
                fetch="one"
            )
            if user and verify_password(user["password_hash"], password):
                if not user["is_active"]:
                    flash("Your doctor account has been deactivated. Contact administration.", "danger")
                    return render_template("auth/login.html")
                login_user(user["doctor_id"], "doctor", user["full_name"], user["email"])
                flash(f"Welcome back, {user['full_name']}!", "success")
                return redirect(url_for("doctor.dashboard"))

        else:  # Patient
            user = execute_query(
                "SELECT patient_id, full_name, email, password_hash FROM patients WHERE email = %s",
                (email,),
                fetch="one"
            )
            if user and verify_password(user["password_hash"], password):
                login_user(user["patient_id"], "patient", user["full_name"], user["email"])
                flash(f"Welcome back, {user['full_name']}!", "success")
                next_page = request.args.get("next")
                return redirect(next_page if next_page else url_for("patient.dashboard"))

        flash("Invalid email address, password, or role selection.", "danger")

    selected_role = request.args.get("role", "patient")
    return render_template("auth/login.html", selected_role=selected_role)


@auth_bp.route("/logout")
def logout():
    """Clears session and redirects to login."""
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))
