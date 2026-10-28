"""PulseCare Hospital Management System - Main Flask Application Factory."""

from datetime import date, datetime, time, timedelta
import os
from flask import Flask, redirect, render_template, session, url_for
from config import config_by_name
from database.connection import close_db, execute_query, init_mysql_pool
from extensions import generate_csrf_token, get_current_user


def create_app(config_name=None):
    """Factory creating and configuring the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    # Initialize Database Connection Pool
    with app.app_context():
        init_mysql_pool(app.config)

    # Teardown connection
    app.teardown_appcontext(close_db)

    # Context processors
    @app.context_processor
    def inject_global_template_vars():
        return {
            "current_user": get_current_user(),
            "csrf_token": generate_csrf_token(),
            "current_year": datetime.now().year,
            "app_name": app.config.get("APP_NAME", "PulseCare HMS")
        }

    # Template filters
    @app.template_filter("date_fmt")
    def format_date(value, format_str="%b %d, %Y"):
        if not value:
            return "—"
        if isinstance(value, str):
            try:
                dt = datetime.strptime(value[:10], "%Y-%m-%d")
                return dt.strftime(format_str)
            except Exception:
                return value
        if isinstance(value, (datetime, date)):
            return value.strftime(format_str)
        return str(value)

    @app.template_filter("time_fmt")
    def format_time(value):
        if not value:
            return "—"
        if isinstance(value, timedelta):
            # mysql TIME returned as timedelta
            tot_sec = int(value.total_seconds())
            h = (tot_sec // 3600) % 24
            m = (tot_sec % 3600) // 60
            t_obj = time(h, m)
            return t_obj.strftime("%I:%M %p")
        if isinstance(value, time):
            return value.strftime("%I:%M %p")
        if isinstance(value, str):
            try:
                parts = [int(p) for p in value.split(":")[:2]]
                t_obj = time(parts[0], parts[1])
                return t_obj.strftime("%I:%M %p")
            except Exception:
                return value
        return str(value)

    @app.template_filter("currency_fmt")
    def format_currency(value):
        try:
            val_float = float(value)
            return f"${val_float:,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.patient import patient_bp
    from routes.doctor import doctor_bp
    from routes.appointments import appointments_bp
    from routes.medical_records import medical_records_bp
    from routes.prescriptions import prescriptions_bp
    from routes.billing import billing_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(medical_records_bp)
    app.register_blueprint(prescriptions_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(admin_bp)

    # Public Landing Page Route
    @app.route("/")
    def index():
        # Fetch featured doctors and departments from database
        featured_doctors = execute_query(
            """
            SELECT d.doctor_id, d.full_name, d.specialization, d.qualification,
                   d.years_experience, d.consultation_fee, dept.department_name
            FROM doctors d
            JOIN departments dept ON d.department_id = dept.department_id
            WHERE d.is_active = 1
            ORDER BY d.doctor_id ASC
            LIMIT 8
            """,
            fetch="all"
        ) or []

        departments = execute_query(
            """
            SELECT department_id, department_name, description, location
            FROM departments
            WHERE is_active = 1
            LIMIT 6
            """,
            fetch="all"
        ) or []

        return render_template(
            "index.html",
            featured_doctors=featured_doctors,
            departments=departments
        )

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", error=e), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html", error=e), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html", error=e), 500

    return app


if __name__ == "__main__":
    app = create_app("development")
    app.run(host="127.0.0.1", port=5000, debug=True)
