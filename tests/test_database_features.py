"""Database Features Verification Tests for PulseCare HMS.

Tests Views, Stored Procedures, Relational Constraints, and Transaction Rollback.
"""

import pytest
from database.connection import execute_query, execute_stored_procedure, get_db


def test_appointment_details_view():
    """Verify appointment_details_view joins appointments, patients, doctors, and departments."""
    # Insert appointment
    app_id = execute_query(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
        VALUES (1, 1, '2026-10-30', '11:00:00', '11:30:00', 'View test visit', 'Confirmed')
        """,
        commit=True
    )

    # Query view
    row = execute_query(
        "SELECT * FROM appointment_details_view WHERE appointment_id = %s",
        (app_id,),
        fetch="one"
    )

    assert row is not None
    assert row["patient_name"] == "John Doe"
    assert row["doctor_name"] == "Dr. Sarah Jenkins"
    assert row["department_name"] == "Cardiology"
    assert row["status"] == "Confirmed"


def test_stored_procedures_execution():
    """Verify stored procedure invocation for patient appointment history and doctor statistics."""
    # sp_get_patient_appointment_history
    history = execute_stored_procedure("sp_get_patient_appointment_history", (1,))
    assert isinstance(history, list)

    # sp_get_doctor_schedule_stats
    stats = execute_stored_procedure("sp_get_doctor_schedule_stats", (1,))
    assert isinstance(stats, list)
    assert len(stats) > 0


def test_unique_email_constraint():
    """Verify DBMS enforces unique email constraint on patients table."""
    with pytest.raises(Exception):
        execute_query(
            """
            INSERT INTO patients (full_name, email, phone, date_of_birth, gender, password_hash)
            VALUES ('Duplicate John', 'john.doe@example.com', '+1-555-0000', '1990-01-01', 'Male', 'hash')
            """,
            commit=True
        )


def test_transaction_rollback_on_failure():
    """Verify uncommitted transactions roll back cleanly upon syntax or runtime error."""
    conn = get_db()
    initial_count = execute_query("SELECT COUNT(*) AS c FROM departments", fetch="one")["c"]

    try:
        # Begin manual multi-step transaction
        execute_query("INSERT INTO departments (department_name) VALUES ('Temp Dept')", commit=False)
        # Deliberately cause error
        execute_query("INSERT INTO non_existent_table VALUES (1)", commit=False)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()

    after_count = execute_query("SELECT COUNT(*) AS c FROM departments", fetch="one")["c"]
    assert after_count == initial_count


def test_database_trigger_status_audit_log():
    """Verify database trigger automatically fires upon appointment status update

    and inserts a record into audit_appointment_logs.
    """
    app_id = execute_query(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
        VALUES (1, 1, '2026-10-31', '12:00:00', '12:30:00', 'Trigger test', 'Scheduled')
        """,
        commit=True
    )

    # Perform status update
    execute_query(
        "UPDATE appointments SET status = 'Confirmed' WHERE appointment_id = %s",
        (app_id,),
        commit=True
    )

    # Check that database trigger inserted audit row
    audit = execute_query(
        "SELECT * FROM audit_appointment_logs WHERE appointment_id = %s ORDER BY audit_id DESC",
        (app_id,),
        fetch="one"
    )
    assert audit is not None
    assert audit["old_status"] == "Scheduled"
    assert audit["new_status"] == "Confirmed"


def test_foreign_key_violation():
    """Verify database foreign key constraint rejects appointment with non-existent doctor."""
    with pytest.raises(Exception):
        execute_query(
            """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
            VALUES (1, 99999, '2026-10-31', '12:00:00', '12:30:00', 'Invalid FK Doctor', 'Scheduled')
            """,
            commit=True
        )

