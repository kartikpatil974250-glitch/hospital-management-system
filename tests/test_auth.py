"""Authentication and Role-Based Authorization Tests for PulseCare HMS."""

from database.connection import execute_query
from extensions import verify_password


def test_patient_registration_success(client):
    """Test patient registration with valid information."""
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    response = client.post("/auth/register", data={
        "csrf_token": "valid-token",
        "full_name": "Alice Wonderland",
        "email": "alice@example.com",
        "phone": "+1-555-4321",
        "date_of_birth": "1995-05-15",
        "gender": "Female",
        "address": "42 Rabbit Hole",
        "emergency_contact": "White Rabbit",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    # Verify database persistence & password hashing
    user = execute_query("SELECT * FROM patients WHERE email = %s", ("alice@example.com",), fetch="one")
    assert user is not None
    assert user["full_name"] == "Alice Wonderland"
    assert user["password_hash"] != "Password123!"
    assert verify_password(user["password_hash"], "Password123!")


def test_patient_registration_duplicate_email(client):
    """Test that duplicate email registration is rejected."""
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    response = client.post("/auth/register", data={
        "csrf_token": "valid-token",
        "full_name": "John Duplicate",
        "email": "john.doe@example.com",  # Already in fixture
        "phone": "+1-555-9999",
        "date_of_birth": "1985-06-15",
        "gender": "Male",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    assert b"account with this email address already exists" in response.data


def test_login_patient_success(client):
    """Test successful patient login."""
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    response = client.post("/auth/login", data={
        "csrf_token": "valid-token",
        "role": "patient",
        "email": "john.doe@example.com",
        "password": "Patient@123"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, John Doe" in response.data


def test_login_invalid_credentials(client):
    """Test login failure with wrong password."""
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    response = client.post("/auth/login", data={
        "csrf_token": "valid-token",
        "role": "patient",
        "email": "john.doe@example.com",
        "password": "WrongPassword!"
    }, follow_redirects=True)

    assert b"Invalid email address, password, or role" in response.data


def test_login_admin_success(client):
    """Test administrator authentication."""
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    response = client.post("/auth/login", data={
        "csrf_token": "valid-token",
        "role": "admin",
        "email": "admin@pulsecare.com",
        "password": "Admin@123"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, Administrator" in response.data


def test_role_based_access_controls(patient_client, doctor_client):
    """Ensure patients cannot access admin or doctor dashboards."""
    # Patient attempting admin route
    resp_admin = patient_client.get("/admin/dashboard", follow_redirects=True)
    assert b"Access denied: You do not have permission" in resp_admin.data

    # Patient attempting doctor route
    resp_doc = patient_client.get("/doctor/dashboard", follow_redirects=True)
    assert b"Access denied: You do not have permission" in resp_doc.data

    # Doctor attempting admin route
    resp_doc_admin = doctor_client.get("/admin/dashboard", follow_redirects=True)
    assert b"Access denied: You do not have permission" in resp_doc_admin.data


def test_doctor_registration_success(client):
    """Test doctor registration and subsequent login."""
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    response = client.post("/auth/register", data={
        "csrf_token": "valid-token",
        "role": "doctor",
        "full_name": "Alexander Hayes",
        "email": "dr.hayes@pulsecare.com",
        "phone": "+1-555-9876",
        "department_id": 1,
        "specialization": "Pediatric Cardiology",
        "qualification": "MBBS, MD (Pediatrics)",
        "years_experience": 8,
        "consultation_fee": 110.0,
        "password": "DoctorPass123!",
        "confirm_password": "DoctorPass123!"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"successfully registered" in response.data

    # Check persistence in database
    doc = execute_query("SELECT * FROM doctors WHERE email = %s", ("dr.hayes@pulsecare.com",), fetch="one")
    assert doc is not None
    assert doc["full_name"] == "Dr. Alexander Hayes"
    assert doc["specialization"] == "Pediatric Cardiology"
    assert doc["is_active"] == 1

    # Check that default schedules were generated
    schedules = execute_query("SELECT COUNT(*) AS c FROM doctor_schedules WHERE doctor_id = %s", (doc["doctor_id"],), fetch="one")
    assert schedules["c"] == 5

    # Check login as newly registered doctor
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "valid-token"

    login_resp = client.post("/auth/login", data={
        "csrf_token": "valid-token",
        "role": "doctor",
        "email": "dr.hayes@pulsecare.com",
        "password": "DoctorPass123!"
    }, follow_redirects=True)

    assert login_resp.status_code == 200
    assert b"Welcome back, Dr. Alexander Hayes" in login_resp.data
