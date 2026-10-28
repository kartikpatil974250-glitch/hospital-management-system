# PULSECARE HMS — HOSPITAL MANAGEMENT SYSTEM
### Advanced Full-Stack DBMS Mini Project & Healthcare SaaS Platform

---

## 1. Executive Summary & Architecture Overview

**PulseCare HMS** is an enterprise-grade Hospital Management System engineered with Python Flask, MySQL, and vanilla JavaScript/CSS3. It models real-world outpatient clinical workflows, secure multi-role role-based access control (RBAC), ACID-compliant financial and booking transactions, and relational database management principles (DDL/DML constraints, indexes, views, stored procedures, and triggers).

### Core Technological Foundations
- **Backend Architecture:** Python 3.11+, Flask Application Factory pattern, Blueprints.
- **Relational Database (DBMS):** MySQL 8.0+ (InnoDB Engine) with connection pooling (`mysql-connector-python`).
- **Security & Cryptography:** Werkzeug Scrypt password hashing, session tokens, and CSRF protection.
- **Frontend Presentation:** HTML5, CSS3 Custom Properties (Design System Tokens), responsive Flexbox & CSS Grid, vanilla ES6 JavaScript.
- **Automated Verification:** Pytest test suite covering authentication, RBAC, clinical EHR, concurrency locking, and database features.

---

## 2. Relational Database Architecture

The system schema resides in `hospital_management_db` across 12 relational tables, 1 database view, 2 triggers, and 2 stored procedures.

### Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    DEPARTMENTS ||--o{ DOCTORS : "employs"
    DOCTORS ||--o{ DOCTOR_SCHEDULES : "maintains"
    DOCTORS ||--o{ DOCTOR_UNAVAILABILITY : "records_leaves"
    DOCTORS ||--o{ APPOINTMENTS : "attends"
    PATIENTS ||--o{ APPOINTMENTS : "books"
    APPOINTMENTS ||--o| MEDICAL_RECORDS : "generates"
    APPOINTMENTS ||--o| BILLS : "incurs"
    MEDICAL_RECORDS ||--o| PRESCRIPTIONS : "includes"
    PRESCRIPTIONS ||--o{ PRESCRIPTION_ITEMS : "contains"
    BILLS ||--o{ PAYMENTS : "settled_by"
    APPOINTMENTS ||--o{ AUDIT_APPOINTMENT_LOGS : "triggers_audit"

    DEPARTMENTS {
        int department_id PK
        string department_name UK
        text description
        string location
        string contact_number
        boolean is_active
    }

    DOCTORS {
        int doctor_id PK
        int department_id FK
        string full_name
        string email UK
        string phone
        string specialization
        string qualification
        int years_experience
        decimal consultation_fee
        string password_hash
        boolean is_active
    }

    DOCTOR_SCHEDULES {
        int schedule_id PK
        int doctor_id FK
        string day_of_week
        time start_time
        time end_time
        int slot_duration
        boolean is_available
    }

    PATIENTS {
        int patient_id PK
        string full_name
        string email UK
        string phone
        date date_of_birth
        string gender
        text address
        string emergency_contact
        string password_hash
    }

    APPOINTMENTS {
        int appointment_id PK
        int patient_id FK
        int doctor_id FK
        date appointment_date
        time start_time
        time end_time
        text reason
        string status
        string cancellation_reason
    }

    MEDICAL_RECORDS {
        int record_id PK
        int patient_id FK
        int doctor_id FK
        int appointment_id FK_UK
        date visit_date
        text symptoms
        text diagnosis
        text treatment_notes
        string allergies
        date follow_up_date
    }

    PRESCRIPTIONS {
        int prescription_id PK
        int medical_record_id FK_UK
        int patient_id FK
        int doctor_id FK
        date prescription_date
        text instructions
    }

    PRESCRIPTION_ITEMS {
        int item_id PK
        int prescription_id FK
        string medication_name
        string dosage
        string frequency
        string duration
        string instructions
    }

    BILLS {
        int bill_id PK
        int patient_id FK
        int appointment_id FK_UK
        decimal consultation_fee
        decimal additional_charges
        decimal discount
        decimal total_amount
        decimal amount_paid
        string payment_status
    }

    PAYMENTS {
        int payment_id PK
        int bill_id FK
        decimal amount
        datetime payment_date
        string payment_method
        string transaction_reference UK
        string payment_status
    }

    AUDIT_APPOINTMENT_LOGS {
        int audit_id PK
        int appointment_id
        string old_status
        string new_status
        datetime changed_at
        string remarks
    }
```

---

## 3. Database Features & DBMS Viva Justification

### A. JOIN Queries
- **Multi-Table Consultation Join:** Joins `appointments`, `doctors`, `departments`, `patients`, and `bills` to present consolidated patient rosters without redundant queries.
- **Prescription Medication Hierarchy:** Joins `prescriptions`, `prescription_items`, `medical_records`, `patients`, and `doctors` to construct official clinical prescription pads.

### B. Relational View: `appointment_details_view`
```sql
CREATE OR REPLACE VIEW appointment_details_view AS
SELECT 
    a.appointment_id,
    a.patient_id,
    p.full_name AS patient_name,
    p.email AS patient_email,
    p.phone AS patient_phone,
    d.doctor_id,
    d.full_name AS doctor_name,
    d.specialization AS doctor_specialization,
    d.consultation_fee,
    dept.department_name,
    dept.location AS department_location,
    a.appointment_date,
    a.start_time,
    a.end_time,
    a.status,
    b.bill_id,
    b.payment_status AS bill_status,
    b.total_amount AS bill_total,
    b.amount_paid AS bill_paid
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors d ON a.doctor_id = d.doctor_id
JOIN departments dept ON d.department_id = dept.department_id
LEFT JOIN bills b ON a.appointment_id = b.appointment_id;
```
*Purpose:* Provides high-performance, single-query access for appointment summaries and admin reporting while abstracting relational complexity.

### C. Database Triggers: `trg_appointment_status_update` & `trg_appointment_insert_audit`
```sql
CREATE TRIGGER trg_appointment_status_update
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO audit_appointment_logs (
            appointment_id, old_status, new_status, changed_at, remarks
        ) VALUES (
            NEW.appointment_id, OLD.status, NEW.status, NOW(),
            CONCAT('Status updated from ', OLD.status, ' to ', NEW.status)
        );
    END IF;
END;
```
*Purpose:* Enforces immutable audit logging without relying on application code. Whenever a patient cancels, a doctor completes a visit, or an admin reschedules, the transition is logged.

### D. Stored Procedures: `sp_get_patient_appointment_history` & `sp_get_doctor_schedule_stats`
```sql
DELIMITER $$
CREATE PROCEDURE sp_get_patient_appointment_history(IN p_patient_id INT)
BEGIN
    SELECT a.*, d.full_name, dept.department_name, b.total_amount, b.payment_status
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.doctor_id
    JOIN departments dept ON d.department_id = dept.department_id
    LEFT JOIN bills b ON a.appointment_id = b.appointment_id
    WHERE a.patient_id = p_patient_id
    ORDER BY a.appointment_date DESC, a.start_time DESC;
END$$
DELIMITER ;
```
*Purpose:* Pre-compiled server-side execution eliminating round-trip latency and parameter-injection vectors.

### E. Concurrency-Safe Booking & ACID Transactions
Booking an appointment executes inside an atomic transaction:
1. `SELECT ... FOR UPDATE` acquires an exclusive lock on the doctor's record to serialize concurrent booking threads.
2. Checks working hours against `doctor_schedules`.
3. Verifies doctor leaves against `doctor_unavailability`.
4. Executes non-overlap query `NOT (%s >= end_time OR %s <= start_time)`.
5. Inserts into `appointments` and creates corresponding entry in `bills`.
6. Executes `conn.commit()`. If any step violates constraints, `conn.rollback()` executes automatically.

---

## 4. Project Structure

```text
hospital-management-system/
├── app.py                      # Flask Application Factory & Jinja filters
├── config.py                   # Environment configuration classes
├── extensions.py               # RBAC decorators, CSRF & Password hashing
├── run.py                      # Local server entry point
├── requirements.txt            # Dependency definitions
├── init_db.py                  # Database migrations and seed loader
├── create_admin.py             # CLI utility for provisioning admins
├── .env.example                # Environment template
│
├── database/
│   ├── schema.sql              # MySQL DDL (Tables, Constraints, Indexes, Views)
│   ├── procedures.sql          # Stored Procedures & Triggers
│   ├── seed.sql                # Relational sample demo data
│   └── connection.py           # Connection pool & query manager
│
├── routes/
│   ├── auth.py                 # Registration, multi-role login, logout
│   ├── patient.py              # Patient portal & dashboard
│   ├── doctor.py               # Doctor consultations & schedules
│   ├── appointments.py         # Multi-step booking & cancellation
│   ├── medical_records.py      # EHR access & clinical detail
│   ├── prescriptions.py        # Printable prescription pads
│   ├── billing.py              # Invoice settlement & simulated checkout
│   └── admin.py                # Admin metrics, audit logs, doctor CRUD
│
├── services/
│   ├── appointment_service.py  # Slot math, concurrency locking
│   ├── billing_service.py      # Ledgers, balances, payment simulation
│   └── medical_record_service.py # EHR notes & atomic Rx persistence
│
├── static/
│   ├── css/
│   │   ├── style.css           # Global tokens & layout
│   │   ├── components.css      # Buttons, cards, tables, badges
│   │   ├── dashboard.css       # Invoices, prescription pad, stats
│   │   └── responsive.css      # Breakpoints (Mobile, Tablet, Desktop)
│   └── js/
│       ├── main.js             # Drawer toggle, password reveal, toasts
│       └── appointments.js     # Live AJAX slot fetcher & wizard
│
├── templates/
│   ├── base.html               # Shared layout shell with sidebar/topbar
│   ├── index.html              # Public landing page
│   ├── auth/                   # Split-screen Login & Register
│   ├── patient/                # Patient dashboard, records, bills
│   ├── doctor/                 # Consultations, EHR recording, hours
│   ├── appointments/           # Guided booking & confirmation slip
│   ├── medical_records/        # Detailed EHR view
│   ├── prescriptions/          # Printable prescription layout
│   ├── billing/                # Invoice & simulated checkout
│   ├── admin/                  # Overview, audits, doctors, roster
│   └── errors/                 # 400, 403, 404, 500 handlers
│
└── tests/
    ├── conftest.py             # Pytest fixtures & test database
    ├── test_auth.py            # Authentication & RBAC testing
    ├── test_appointments.py    # Concurrency, overlaps, cancellation
    ├── test_billing.py         # Balance calculations, payments
    ├── test_clinical.py        # EHR, prescription items, privacy
    ├── test_database_features.py # View, triggers, sp, rollbacks
    └── test_integration.py     # E2E Patient, Doctor, Admin user journeys
```

---

## 5. Local Setup Instructions (Windows PowerShell)

### Step 1: Clone or Navigate to Directory
```powershell
cd C:\Users\karti\OneDrive\Desktop\hospital
```

### Step 2: Configure Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your MySQL server is running (e.g. via MySQL Workbench or XAMPP) and verify credentials in `.env`:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=hospital_management_db
DB_USER=root
DB_PASSWORD=your_mysql_password
```

### Step 4: Initialize MySQL Database
Run the automated schema and seed loader:
```powershell
python init_db.py
```
*Note: If your MySQL server is not currently running, the system will automatically initialize the local embedded store so you can test and demonstrate the system immediately!*

### Step 5: Start the Application
```powershell
python run.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 6. Pre-Configured Demo Accounts

| Role | Email | Password | Privileges |
|---|---|---|---|
| **Administrator** | `admin@pulsecare.com` | `Admin@123` | Hospital analytics, doctors, depts, billing, DB audit logs |
| **Doctor** | `sarah.jenkins@pulsecare.com` | `Doctor@123` | Today's appointments, consultation EHR entry, schedule |
| **Patient** | `john.doe@example.com` | `Patient@123` | Book appointments, view medical records, print Rx, pay bills |

---

## 7. Automated Test Suite Execution

Run Pytest to verify all 30 test cases:
```powershell
python -m pytest -v
```

### Verified Test Results (30/30 Passed)
```text
tests/test_appointments.py::test_doctor_slots_calculation PASSED         [  3%]
tests/test_appointments.py::test_book_appointment_success PASSED         [  6%]
tests/test_appointments.py::test_reject_overlapping_appointment PASSED   [ 10%]
tests/test_appointments.py::test_cancel_appointment_authorized_and_unauthorized PASSED [ 13%]
tests/test_appointments.py::test_concurrent_booking_race_condition PASSED [ 16%]
tests/test_appointments.py::test_doctor_mark_no_show PASSED              [ 20%]
tests/test_appointments.py::test_reject_past_date_booking PASSED         [ 23%]
tests/test_appointments.py::test_reject_booking_outside_working_hours PASSED [ 26%]
tests/test_appointments.py::test_reject_booking_during_doctor_unavailability PASSED [ 30%]
tests/test_auth.py::test_patient_registration_success PASSED             [ 33%]
tests/test_auth.py::test_patient_registration_duplicate_email PASSED     [ 36%]
tests/test_auth.py::test_login_patient_success PASSED                    [ 40%]
tests/test_auth.py::test_login_invalid_credentials PASSED                [ 43%]
tests/test_auth.py::test_login_admin_success PASSED                      [ 46%]
tests/test_auth.py::test_role_based_access_controls PASSED               [ 50%]
tests/test_billing.py::test_bill_payment_partial_and_full PASSED         [ 53%]
tests/test_billing.py::test_admin_bill_adjustment PASSED                 [ 56%]
tests/test_billing.py::test_reject_invalid_payment_amounts PASSED        [ 60%]
tests/test_billing.py::test_prevent_duplicate_transaction_reference PASSED [ 63%]
tests/test_clinical.py::test_create_medical_record_and_prescription_atomic PASSED [ 66%]
tests/test_clinical.py::test_patient_medical_record_confidentiality PASSED [ 70%]
tests/test_database_features.py::test_appointment_details_view PASSED    [ 73%]
tests/test_database_features.py::test_stored_procedures_execution PASSED [ 76%]
tests/test_database_features.py::test_unique_email_constraint PASSED     [ 80%]
tests/test_database_features.py::test_transaction_rollback_on_failure PASSED [ 83%]
tests/test_database_features.py::test_database_trigger_status_audit_log PASSED [ 86%]
tests/test_database_features.py::test_foreign_key_violation PASSED       [ 90%]
tests/test_integration.py::test_full_patient_workflow PASSED             [ 93%]
tests/test_integration.py::test_full_doctor_workflow PASSED              [ 96%]
tests/test_integration.py::test_full_admin_workflow PASSED               [100%]

============================= 30 passed in 14.92s =============================
```
