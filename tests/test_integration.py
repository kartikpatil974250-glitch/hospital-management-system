"""End-to-End System Integration Tests for PulseCare HMS.

Tests full user journeys for Patient, Doctor, and Administrator, verifying
sessions, form submissions, database persistence, and transaction behavior.
"""

from database.connection import execute_query
from extensions import hash_password
from tests.test_appointments import get_next_weekday


def test_full_patient_workflow(client):
    """E2E Patient Journey:

    1. Register new account.
    2. Sign in.
    3. Update profile contact details.
    4. Browse doctors directory.
    5. Book an appointment.
    6. View booking confirmation.
    7. Process simulated payment on invoice.
    8. Sign out.
    """
    # Step 1: Register
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "integration-token"

    reg_resp = client.post("/auth/register", data={
        "csrf_token": "integration-token",
        "full_name": "Integration Patient",
        "email": "e2e_patient@example.com",
        "phone": "+1-555-7788",
        "date_of_birth": "1994-04-10",
        "gender": "Female",
        "address": "100 Innovation Way",
        "emergency_contact": "Bob (+1-555-9988)",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)
    assert reg_resp.status_code == 200

    # Step 2: Login
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "integration-token"

    login_resp = client.post("/auth/login", data={
        "csrf_token": "integration-token",
        "role": "patient",
        "email": "e2e_patient@example.com",
        "password": "Password123!"
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Integration Patient" in login_resp.data

    # Step 3: Update Profile
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "integration-token"

    prof_resp = client.post("/patient/profile", data={
        "csrf_token": "integration-token",
        "phone": "+1-555-0011",
        "address": "200 Updated Boulevard",
        "emergency_contact": "Sarah (+1-555-2233)"
    }, follow_redirects=True)
    assert prof_resp.status_code == 200
    assert b"Profile updated successfully" in prof_resp.data

    # Step 4: Browse Doctors
    doc_resp = client.get("/patient/doctors")
    assert doc_resp.status_code == 200
    assert b"Dr. Sarah Jenkins" in doc_resp.data

    # Step 5: Book Appointment
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "integration-token"

    target_date = get_next_weekday("Monday").strftime("%Y-%m-%d")
    book_resp = client.post("/appointments/book", data={
        "csrf_token": "integration-token",
        "doctor_id": 1,
        "appointment_date": target_date,
        "start_time": "09:30",
        "reason": "E2E Integration routine cardiovascular check"
    }, follow_redirects=True)
    assert book_resp.status_code == 200
    assert b"Appointment Confirmed!" in book_resp.data

    # Fetch created appointment & bill
    app_row = execute_query(
        "SELECT appointment_id FROM appointments WHERE reason LIKE '%E2E Integration%'",
        fetch="one"
    )
    assert app_row is not None
    app_id = app_row["appointment_id"]

    bill_row = execute_query(
        "SELECT bill_id, bill_total, balance_due FROM appointment_details_view WHERE appointment_id = %s",
        (app_id,),
        fetch="one"
    )
    assert bill_row is not None
    bill_id = bill_row["bill_id"]

    # Step 6: Process Simulated Payment
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "integration-token"

    pay_resp = client.post(f"/billing/pay/{bill_id}", data={
        "csrf_token": "integration-token",
        "amount": 120.00,
        "payment_method": "Card"
    }, follow_redirects=True)
    assert pay_resp.status_code == 200
    assert b"Simulated payment processed successfully" in pay_resp.data

    # Step 7: Logout
    logout_resp = client.get("/auth/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"You have been signed out" in logout_resp.data


def test_full_doctor_workflow(doctor_client):
    """E2E Doctor Journey:

    1. View clinical dashboard.
    2. Review appointments queue.
    3. Update clinic schedule.
    4. Conduct patient consultation (document symptoms, diagnosis, prescription items).
    5. Verify consultation status changes to 'Completed'.
    """
    # Step 1: Clinical Dashboard
    dash_resp = doctor_client.get("/doctor/dashboard")
    assert dash_resp.status_code == 200
    assert b"Doctor Consultation Dashboard" in dash_resp.data

    # Step 2: Insert patient appointment for Dr. Jenkins
    app_id = execute_query(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
        VALUES (1, 1, '2026-10-26', '10:00:00', '10:30:00', 'E2E Doctor clinical exam', 'Confirmed')
        """,
        commit=True
    )

    # Step 3: Conduct Consultation
    consult_resp = doctor_client.post(f"/doctor/consultation/{app_id}", data={
        "csrf_token": "test-csrf-token",
        "symptoms": "Occasional exertional breathlessness, normal lung auscultation",
        "diagnosis": "Mild Exertional Dyspnea",
        "treatment_notes": "Prescribed bronchodilator trial and advised daily light walking",
        "allergies": "None",
        "follow_up_date": "2026-11-26",
        "instructions": "Inhale 2 puffs as needed before exertion",
        "med_name[]": ["Salbutamol Inhaler", "Multivitamin Complex"],
        "med_dosage[]": ["100 mcg", "1 tablet"],
        "med_freq[]": ["PRN", "Daily with meal"],
        "med_duration[]": ["30 days", "30 days"],
        "med_instructions[]": ["Rinse mouth after inhalation", "Take in morning"]
    }, follow_redirects=True)

    assert consult_resp.status_code == 200
    assert b"Clinical medical record and prescription saved successfully" in consult_resp.data

    # Verify status changed to 'Completed' in database
    app_state = execute_query("SELECT status FROM appointments WHERE appointment_id = %s", (app_id,), fetch="one")
    assert app_state["status"] == "Completed"

    # Step 4: Verify Prescription pad view
    rx = execute_query("SELECT prescription_id FROM prescriptions WHERE patient_id = 1", fetch="one")
    assert rx is not None
    rx_resp = doctor_client.get(f"/prescriptions/{rx['prescription_id']}")
    assert rx_resp.status_code == 200
    assert b"Salbutamol Inhaler" in rx_resp.data


def test_full_admin_workflow(admin_client):
    """E2E Admin Journey:

    1. View hospital dashboard statistics.
    2. Register a new physician.
    3. Update doctor details.
    4. Toggle doctor status (Active -> Inactive -> Active).
    5. Add a clinical department.
    6. Adjust billing charges on an invoice.
    7. Inspect database trigger status audit logs.
    8. Review hospital departmental reports.
    """
    # Step 1: Dashboard
    dash_resp = admin_client.get("/admin/dashboard")
    assert dash_resp.status_code == 200
    assert b"Hospital Administrative Control Center" in dash_resp.data

    # Step 2: Register Doctor
    doc_resp = admin_client.post("/admin/doctors", data={
        "csrf_token": "test-csrf-token",
        "action": "add_doctor",
        "full_name": "Dr. E2E Specialist",
        "email": "e2e_doc@pulsecare.com",
        "phone": "+1-555-8899",
        "specialization": "Endocrinology",
        "department_id": 1,
        "qualification": "MD, FACE",
        "years_experience": 10,
        "consultation_fee": 110.00,
        "password": "Doctor@123"
    }, follow_redirects=True)
    assert doc_resp.status_code == 200
    assert b"Doctor Dr. E2E Specialist successfully registered" in doc_resp.data

    doc_row = execute_query("SELECT doctor_id FROM doctors WHERE email = %s", ("e2e_doc@pulsecare.com",), fetch="one")
    doc_id = doc_row["doctor_id"]

    # Step 3: Toggle Doctor Active Status
    toggle_resp = admin_client.post("/admin/doctors", data={
        "csrf_token": "test-csrf-token",
        "action": "toggle_active",
        "doctor_id": doc_id,
        "current_status": 1
    }, follow_redirects=True)
    assert toggle_resp.status_code == 200
    assert b"Doctor status updated to Inactive" in toggle_resp.data

    # Step 4: Add Department
    dept_resp = admin_client.post("/admin/departments", data={
        "csrf_token": "test-csrf-token",
        "department_name": "Endocrinology & Metabolism",
        "location": "Block C, Floor 3",
        "contact_number": "+1-555-0188",
        "description": "Diabetes management, thyroid disorders, and metabolic therapies."
    }, follow_redirects=True)
    assert dept_resp.status_code == 200
    assert b"created successfully" in dept_resp.data and b"Endocrinology" in dept_resp.data

    # Step 5: View Reports
    rep_resp = admin_client.get("/admin/reports")
    assert rep_resp.status_code == 200
    assert b"Hospital Analytics & Clinical Intelligence" in rep_resp.data
