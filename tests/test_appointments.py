"""Appointment Service and Concurrency Safe Booking Tests for PulseCare HMS."""

from datetime import date, timedelta
from database.connection import execute_query
from services.appointment_service import book_appointment_concurrency_safe, cancel_appointment, get_available_slots


def get_next_weekday(weekday_name="Monday"):
    """Finds next upcoming date matching weekday name."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    target_idx = days.index(weekday_name)
    today = date.today()
    days_ahead = target_idx - today.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def test_doctor_slots_calculation():
    """Verify slots generated match doctor schedule hours."""
    next_mon = get_next_weekday("Monday").strftime("%Y-%m-%d")
    slots = get_available_slots(doctor_id=1, target_date_str=next_mon)

    assert len(slots) > 0
    # Monday schedule is 09:00 to 13:00 (4 hours / 30 mins = 8 slots)
    assert len(slots) == 8
    assert slots[0]["start_time"] == "09:00"
    assert slots[0]["is_available"] is True


def test_book_appointment_success():
    """Verify booking an appointment locks slot and creates initial unpaid bill."""
    next_mon = get_next_weekday("Monday").strftime("%Y-%m-%d")

    success, msg, app_id = book_appointment_concurrency_safe(
        patient_id=1,
        doctor_id=1,
        appointment_date_str=next_mon,
        start_time_str="09:00",
        reason="Heart palpitations and mild dizziness"
    )

    assert success is True
    assert app_id is not None

    # Verify appointment in database
    app = execute_query("SELECT * FROM appointments WHERE appointment_id = %s", (app_id,), fetch="one")
    assert app["status"] == "Confirmed"
    assert app["doctor_id"] == 1
    assert app["patient_id"] == 1

    # Verify automatic bill creation
    bill = execute_query("SELECT * FROM bills WHERE appointment_id = %s", (app_id,), fetch="one")
    assert bill is not None
    assert float(bill["consultation_fee"]) == 120.00
    assert float(bill["total_amount"]) == 120.00
    assert bill["payment_status"] == "Unpaid"


def test_reject_overlapping_appointment():
    """Verify booking same doctor at same slot is strictly rejected."""
    next_wed = get_next_weekday("Wednesday").strftime("%Y-%m-%d")

    # Patient 1 books 10:00 AM
    ok1, _, app1_id = book_appointment_concurrency_safe(
        patient_id=1,
        doctor_id=1,
        appointment_date_str=next_wed,
        start_time_str="10:00",
        reason="Checkup 1"
    )
    assert ok1 is True

    # Patient 2 attempts to book same 10:00 AM slot with same doctor
    ok2, msg2, app2_id = book_appointment_concurrency_safe(
        patient_id=2,
        doctor_id=1,
        appointment_date_str=next_wed,
        start_time_str="10:00",
        reason="Checkup 2"
    )
    assert ok2 is False
    assert "reserved by another patient" in msg2 or "unavailable" in msg2


def test_cancel_appointment_authorized_and_unauthorized():
    """Verify patient can only cancel their own appointments."""
    next_mon = get_next_weekday("Monday").strftime("%Y-%m-%d")
    _, _, app_id = book_appointment_concurrency_safe(
        patient_id=1,
        doctor_id=1,
        appointment_date_str=next_mon,
        start_time_str="11:00",
        reason="Follow up"
    )

    # Patient 2 tries to cancel Patient 1's appointment -> Must fail
    unauth_ok, unauth_msg = cancel_appointment(app_id, user_id=2, role="patient", cancellation_reason="Malicious cancel")
    assert unauth_ok is False
    assert "Unauthorized" in unauth_msg

    # Patient 1 cancels their own appointment -> Must succeed
    auth_ok, auth_msg = cancel_appointment(app_id, user_id=1, role="patient", cancellation_reason="Rescheduling")
    assert auth_ok is True

    # Verify status in database
    app = execute_query("SELECT status FROM appointments WHERE appointment_id = %s", (app_id,), fetch="one")
    assert app["status"] == "Cancelled"


def test_concurrent_booking_race_condition():
    """Verify that when 5 concurrent threads attempt to book the exact same slot,

    only 1 succeeds and the remaining 4 receive graceful collision rejections.
    """
    import concurrent.futures

    next_mon = get_next_weekday("Monday").strftime("%Y-%m-%d")
    slot = "12:00"

    results = []

    def attempt_booking(patient_num):
        ok, msg, app_id = book_appointment_concurrency_safe(
            patient_id=1,
            doctor_id=1,
            appointment_date_str=next_mon,
            start_time_str=slot,
            reason=f"Concurrent thread attempt {patient_num}"
        )
        return ok, msg, app_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_booking, i) for i in range(1, 6)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    assert len(successes) == 1, f"Expected exactly 1 booking to succeed, got {len(successes)}"
    assert len(failures) == 4, f"Expected 4 bookings to fail with slot reserved message, got {len(failures)}"


def test_doctor_mark_no_show(doctor_client):
    """Verify authorized doctor can mark an appointment as No-show."""
    # Insert test appointment for doctor 1
    app_id = execute_query(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
        VALUES (1, 1, '2026-10-29', '09:00:00', '09:30:00', 'Followup', 'Confirmed')
        """,
        commit=True
    )

    resp = doctor_client.post(f"/doctor/appointments/{app_id}/no-show", data={
        "csrf_token": "test-csrf-token"
    }, follow_redirects=True)

    assert resp.status_code == 200
    app = execute_query("SELECT status FROM appointments WHERE appointment_id = %s", (app_id,), fetch="one")
    assert app["status"] == "No-show"


def test_reject_past_date_booking():
    """Verify booking attempt in the past is rejected."""
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    ok, msg, _ = book_appointment_concurrency_safe(
        patient_id=1,
        doctor_id=1,
        appointment_date_str=yesterday,
        start_time_str="10:00",
        reason="Past test"
    )
    assert ok is False
    assert "past" in msg.lower()


def test_reject_booking_outside_working_hours():
    """Verify booking on an unscheduled day (e.g. Sunday) is rejected."""
    next_sun = get_next_weekday("Sunday").strftime("%Y-%m-%d")
    ok, msg, _ = book_appointment_concurrency_safe(
        patient_id=1,
        doctor_id=1,
        appointment_date_str=next_sun,
        start_time_str="10:00",
        reason="Sunday visit"
    )
    assert ok is False
    assert "not have available clinic hours" in msg.lower()


def test_reject_booking_during_doctor_unavailability():
    """Verify booking during a doctor's registered leave period is rejected."""
    next_mon = get_next_weekday("Monday").strftime("%Y-%m-%d")

    # Insert leave block from 10:00 to 12:00
    execute_query(
        """
        INSERT INTO doctor_unavailability (doctor_id, start_datetime, end_datetime, reason)
        VALUES (1, %s, %s, 'Medical symposium')
        """,
        (f"{next_mon} 10:00:00", f"{next_mon} 12:00:00"),
        commit=True
    )

    ok, msg, _ = book_appointment_concurrency_safe(
        patient_id=1,
        doctor_id=1,
        appointment_date_str=next_mon,
        start_time_str="10:30",
        reason="Consultation during doctor leave"
    )
    assert ok is False
    assert "unavailable" in msg.lower()



