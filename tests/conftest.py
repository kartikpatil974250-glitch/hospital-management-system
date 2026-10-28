"""Pytest Configuration and Fixtures for PulseCare HMS Test Suite."""

import os
import pytest

# Ensure testing configuration is active
os.environ["FLASK_ENV"] = "testing"
os.environ["USE_SQLITE_FALLBACK"] = "1"
os.environ["SQLITE_DB_PATH"] = ":memory:"

from app import create_app
from database.connection import _ensure_sqlite_tables, execute_query, get_db
from extensions import hash_password


@pytest.fixture(scope="session")
def app():
    """Session-wide application fixture."""
    test_app = create_app("testing")
    return test_app


@pytest.fixture(autouse=True)
def app_ctx(app):
    """Provides application context automatically to all tests."""
    with app.app_context():
        conn = get_db()
        _ensure_sqlite_tables(conn)

        # Clear existing rows
        with conn:
            conn.execute("DELETE FROM payments")
            conn.execute("DELETE FROM bills")
            conn.execute("DELETE FROM prescription_items")
            conn.execute("DELETE FROM prescriptions")
            conn.execute("DELETE FROM medical_records")
            conn.execute("DELETE FROM appointments")
            conn.execute("DELETE FROM doctor_unavailability")
            conn.execute("DELETE FROM doctor_schedules")
            conn.execute("DELETE FROM doctors")
            conn.execute("DELETE FROM departments")
            conn.execute("DELETE FROM patients")
            conn.execute("DELETE FROM admins")
            conn.execute("DELETE FROM audit_appointment_logs")

            # Seed core test records
            conn.execute("""
                INSERT INTO departments (department_id, department_name, description, location, contact_number, is_active)
                VALUES (1, 'Cardiology', 'Cardiology unit', 'Block A', '+1-555-0101', 1)
            """)

            doc_hash = hash_password("Doctor@123")
            conn.execute("""
                INSERT INTO doctors (doctor_id, full_name, email, phone, specialization, department_id, qualification, years_experience, consultation_fee, password_hash, is_active)
                VALUES (1, 'Dr. Sarah Jenkins', 'sarah.jenkins@pulsecare.com', '+1-555-0201', 'Cardiologist', 1, 'MD, FACC', 14, 120.00, ?, 1)
            """, (doc_hash,))

            # Doctor Schedule: Monday & Wednesday 09:00 - 13:00, slot_duration=30
            conn.execute("""
                INSERT INTO doctor_schedules (doctor_id, day_of_week, start_time, end_time, slot_duration, is_available)
                VALUES 
                (1, 'Monday', '09:00:00', '13:00:00', 30, 1),
                (1, 'Wednesday', '09:00:00', '13:00:00', 30, 1)
            """)

            pat_hash = hash_password("Patient@123")
            conn.execute("""
                INSERT INTO patients (patient_id, full_name, email, phone, date_of_birth, gender, address, emergency_contact, password_hash)
                VALUES 
                (1, 'John Doe', 'john.doe@example.com', '+1-555-1001', '1985-06-15', 'Male', '742 Evergreen', 'Wife', ?),
                (2, 'Jane Smith', 'jane.smith@example.com', '+1-555-1002', '1992-11-20', 'Female', '128 Baker St', 'Mother', ?)
            """, (pat_hash, pat_hash))

            admin_hash = hash_password("Admin@123")
            conn.execute("""
                INSERT INTO admins (admin_id, full_name, email, password_hash, role)
                VALUES (1, 'System Administrator', 'admin@pulsecare.com', ?, 'Super Admin')
            """, (admin_hash,))
        
        yield


@pytest.fixture
def client(app):
    """Unauthenticated Flask test client."""
    return app.test_client()


@pytest.fixture
def patient_client(app):
    """Authenticated test client logged in as Patient 1 (John Doe)."""
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "patient"
        sess["full_name"] = "John Doe"
        sess["email"] = "john.doe@example.com"
        sess["_csrf_token"] = "test-csrf-token"
    return test_client


@pytest.fixture
def doctor_client(app):
    """Authenticated test client logged in as Doctor 1 (Dr. Sarah Jenkins)."""
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "doctor"
        sess["full_name"] = "Dr. Sarah Jenkins"
        sess["email"] = "sarah.jenkins@pulsecare.com"
        sess["_csrf_token"] = "test-csrf-token"
    return test_client


@pytest.fixture
def admin_client(app):
    """Authenticated test client logged in as Admin 1."""
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"
        sess["full_name"] = "System Administrator"
        sess["email"] = "admin@pulsecare.com"
        sess["_csrf_token"] = "test-csrf-token"
    return test_client
