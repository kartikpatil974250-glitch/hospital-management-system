"""Appointment Service for PulseCare HMS.

Handles slot generation, concurrency-safe booking, transactional validation,
and cancellation rules.
"""

from datetime import datetime, date, time, timedelta
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from database.connection import execute_query, get_db, get_db_cursor


def get_available_slots(doctor_id: int, target_date_str: str) -> List[Dict[str, Any]]:
    """Calculates all possible time slots for a doctor on a specific date,

    marking each as available, booked, or unavailable.
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    # Past dates cannot have booking slots
    today = date.today()
    if target_date < today:
        return []

    day_name = target_date.strftime("%A")  # 'Monday', 'Tuesday', etc.

    # 1. Fetch doctor working schedule for this day of week
    schedule = execute_query(
        """
        SELECT start_time, end_time, slot_duration, is_available
        FROM doctor_schedules
        WHERE doctor_id = %s AND day_of_week = %s AND is_available = 1
        """,
        (doctor_id, day_name),
        fetch="one"
    )

    if not schedule:
        return []

    # Parse schedule times
    def to_time(t_val):
        if isinstance(t_val, str):
            # Might be HH:MM:SS or HH:MM
            parts = [int(p) for p in t_val.split(":")[:2]]
            return time(parts[0], parts[1])
        elif isinstance(t_val, timedelta):
            # mysql-connector returns TIME columns as timedelta
            total_seconds = int(t_val.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return time(hours, minutes)
        elif isinstance(t_val, time):
            return t_val
        return time(9, 0)

    start_t = to_time(schedule["start_time"])
    end_t = to_time(schedule["end_time"])
    slot_minutes = int(schedule["slot_duration"]) or 30

    # 2. Fetch existing active bookings for this doctor on target_date
    booked_rows = execute_query(
        """
        SELECT start_time, end_time, status
        FROM appointments
        WHERE doctor_id = %s AND appointment_date = %s 
          AND status IN ('Scheduled', 'Confirmed')
        """,
        (doctor_id, target_date_str),
        fetch="all"
    ) or []

    booked_starts = set()
    for row in booked_rows:
        t = to_time(row["start_time"])
        booked_starts.add(t.strftime("%H:%M"))

    # 3. Fetch doctor unavailability periods overlapping this date
    unavail_rows = execute_query(
        """
        SELECT start_datetime, end_datetime, reason
        FROM doctor_unavailability
        WHERE doctor_id = %s 
          AND DATE(start_datetime) <= %s 
          AND DATE(end_datetime) >= %s
        """,
        (doctor_id, target_date_str, target_date_str),
        fetch="all"
    ) or []

    # 4. Generate all consecutive slots
    slots = []
    current_dt = datetime.combine(target_date, start_t)
    end_dt = datetime.combine(target_date, end_t)
    now = datetime.now()

    while current_dt + timedelta(minutes=slot_minutes) <= end_dt:
        slot_start_time = current_dt.time()
        slot_end_time = (current_dt + timedelta(minutes=slot_minutes)).time()
        start_str = slot_start_time.strftime("%H:%M")
        end_str = slot_end_time.strftime("%H:%M")

        is_past = (target_date == today and current_dt <= now)
        is_booked = start_str in booked_starts

        # Check unavailability period
        is_blocked = False
        block_reason = ""
        for u in unavail_rows:
            u_start = u["start_datetime"]
            u_end = u["end_datetime"]
            if isinstance(u_start, str):
                u_start = datetime.strptime(u_start[:19], "%Y-%m-%d %H:%M:%S")
            if isinstance(u_end, str):
                u_end = datetime.strptime(u_end[:19], "%Y-%m-%d %H:%M:%S")
            if u_start <= current_dt < u_end:
                is_blocked = True
                block_reason = u.get("reason") or "Doctor on Leave"
                break

        status = "available"
        if is_past:
            status = "past"
        elif is_blocked:
            status = "blocked"
        elif is_booked:
            status = "booked"

        slots.append({
            "start_time": start_str,
            "end_time": end_str,
            "display": f"{start_str} - {end_str}",
            "status": status,
            "is_available": (status == "available"),
            "reason": block_reason
        })

        current_dt += timedelta(minutes=slot_minutes)

    return slots


def book_appointment_concurrency_safe(
    patient_id: int,
    doctor_id: int,
    appointment_date_str: str,
    start_time_str: str,
    reason: str
) -> Tuple[bool, str, Optional[int]]:
    """Books an appointment within a database transaction with concurrency locking.

    Steps:
      1. Begin transaction.
      2. Lock doctor row using SELECT ... FOR UPDATE to serialize concurrent bookings.
      3. Verify working hours on that day of week.
      4. Verify doctor unavailability.
      5. Check for overlapping non-cancelled appointment.
      6. Insert appointment.
      7. Automatically generate corresponding pending bill.
      8. Commit transaction.
    """
    try:
        app_date = datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
    except Exception:
        return False, "Invalid appointment date format.", None

    if app_date < date.today():
        return False, "Cannot book appointments in the past.", None

    # Parse start time
    parts = [int(p) for p in start_time_str.split(":")[:2]]
    slot_start = time(parts[0], parts[1])

    # Fetch doctor info and schedule
    day_name = app_date.strftime("%A")
    schedule = execute_query(
        """
        SELECT slot_duration, start_time, end_time, is_available
        FROM doctor_schedules
        WHERE doctor_id = %s AND day_of_week = %s AND is_available = 1
        """,
        (doctor_id, day_name),
        fetch="one"
    )

    if not schedule:
        return False, f"The doctor does not have available clinic hours on {day_name}s.", None

    slot_minutes = int(schedule["slot_duration"]) or 30
    slot_end_dt = datetime.combine(app_date, slot_start) + timedelta(minutes=slot_minutes)
    slot_end = slot_end_dt.time()
    start_fmt = slot_start.strftime("%H:%M:%S")
    end_fmt = slot_end.strftime("%H:%M:%S")

    conn = get_db()
    cursor = get_db_cursor(conn)
    is_mysql = not isinstance(conn, sqlite3.Connection)

    try:
        # Step 1: Explicitly lock the doctor record to serialize bookings for this doctor
        if is_mysql:
            cursor.execute("SELECT doctor_id, consultation_fee, is_active FROM doctors WHERE doctor_id = %s FOR UPDATE", (doctor_id,))
        else:
            cursor.execute("SELECT doctor_id, consultation_fee, is_active FROM doctors WHERE doctor_id = ?", (doctor_id,))
        doctor = cursor.fetchone()
        if not doctor:
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "Doctor record not found.", None

        is_active = doctor["is_active"] if isinstance(doctor, dict) or hasattr(doctor, "keys") else doctor[2]
        if not is_active:
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "Doctor is currently inactive for consultations.", None

        consultation_fee = doctor["consultation_fee"] if isinstance(doctor, dict) or hasattr(doctor, "keys") else doctor[1]

        # Step 2: Validate Unavailability
        check_unavail_sql = """
            SELECT unavailability_id FROM doctor_unavailability
            WHERE doctor_id = %s 
              AND %s < end_datetime 
              AND %s > start_datetime
        """ if is_mysql else """
            SELECT unavailability_id FROM doctor_unavailability
            WHERE doctor_id = ? 
              AND ? < end_datetime 
              AND ? > start_datetime
        """
        slot_start_iso = f"{appointment_date_str} {start_fmt}"
        slot_end_iso = f"{appointment_date_str} {end_fmt}"
        cursor.execute(check_unavail_sql, (doctor_id, slot_start_iso, slot_end_iso))
        if cursor.fetchone():
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "The doctor is unavailable during the requested time window.", None

        # Step 3: Validate Overlapping Appointments
        check_overlap_sql = """
            SELECT appointment_id FROM appointments
            WHERE doctor_id = %s 
              AND appointment_date = %s
              AND status IN ('Scheduled', 'Confirmed')
              AND NOT (%s >= end_time OR %s <= start_time)
        """ if is_mysql else """
            SELECT appointment_id FROM appointments
            WHERE doctor_id = ? 
              AND appointment_date = ?
              AND status IN ('Scheduled', 'Confirmed')
              AND NOT (? >= end_time OR ? <= start_time)
        """
        cursor.execute(check_overlap_sql, (doctor_id, appointment_date_str, start_fmt, end_fmt))
        if cursor.fetchone():
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "This time slot was just reserved by another patient. Please choose another slot.", None

        # Step 4: Insert Appointment
        insert_app_sql = """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Confirmed')
        """ if is_mysql else """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Confirmed')
        """
        cursor.execute(insert_app_sql, (patient_id, doctor_id, appointment_date_str, start_fmt, end_fmt, reason))
        appointment_id = cursor.lastrowid

        # Step 5: Automatically create corresponding Initial Bill for this appointment
        insert_bill_sql = """
            INSERT INTO bills (patient_id, appointment_id, consultation_fee, additional_charges, discount, total_amount, amount_paid, payment_status)
            VALUES (%s, %s, %s, 0.00, 0.00, %s, 0.00, 'Unpaid')
        """ if is_mysql else """
            INSERT INTO bills (patient_id, appointment_id, consultation_fee, additional_charges, discount, total_amount, amount_paid, payment_status)
            VALUES (?, ?, ?, 0.00, 0.00, ?, 0.00, 'Unpaid')
        """
        cursor.execute(insert_bill_sql, (patient_id, appointment_id, consultation_fee, consultation_fee))

        # Commit Transaction
        conn.commit()
        return True, "Appointment booked successfully!", appointment_id

    except Exception as e:
        if hasattr(conn, "rollback"):
            conn.rollback()
        return False, f"Failed to book appointment: {str(e)}", None
    finally:
        if hasattr(cursor, "close"):
            cursor.close()


def cancel_appointment(appointment_id: int, user_id: int, role: str, cancellation_reason: str) -> Tuple[bool, str]:
    """Cancels an appointment if authorized.

    Patients can cancel only their own upcoming appointments.
    Doctors can cancel only their own consultations.
    Admins can cancel any.
    """
    app = execute_query(
        "SELECT * FROM appointments WHERE appointment_id = %s",
        (appointment_id,),
        fetch="one"
    )

    if not app:
        return False, "Appointment not found."

    # Authorization verification
    if role == "patient" and app["patient_id"] != user_id:
        return False, "Unauthorized: You may only cancel your own appointments."
    if role == "doctor" and app["doctor_id"] != user_id:
        return False, "Unauthorized: You may only cancel consultations assigned to you."

    if app["status"] in ("Completed", "Cancelled"):
        return False, f"Cannot cancel an appointment that is already {app['status']}."

    execute_query(
        """
        UPDATE appointments 
        SET status = 'Cancelled', cancellation_reason = %s, updated_at = CURRENT_TIMESTAMP
        WHERE appointment_id = %s
        """,
        (cancellation_reason, appointment_id),
        commit=True
    )

    return True, "Appointment has been cancelled successfully."
