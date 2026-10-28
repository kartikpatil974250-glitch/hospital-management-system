"""Billing and Simulated Payment Service for PulseCare HMS.

Handles invoicing, payment recording, balance validation, and financial transaction integrity.
"""

from datetime import datetime
import secrets
from typing import Any, Dict, List, Optional, Tuple
from database.connection import execute_query, get_db, get_db_cursor


def get_bill_by_id(bill_id: int, user_id: Optional[int] = None, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches bill details along with associated patient, doctor, and payment list.

    Enforces patient confidentiality checks.
    """
    bill = execute_query(
        """
        SELECT 
            b.bill_id,
            b.patient_id,
            b.appointment_id,
            b.consultation_fee,
            b.additional_charges,
            b.discount,
            b.total_amount,
            b.amount_paid,
            (b.total_amount - b.amount_paid) AS balance_due,
            b.payment_status,
            b.created_at,
            p.full_name AS patient_name,
            p.email AS patient_email,
            p.phone AS patient_phone,
            a.appointment_date,
            a.start_time,
            d.full_name AS doctor_name,
            d.specialization,
            dept.department_name
        FROM bills b
        JOIN patients p ON b.patient_id = p.patient_id
        LEFT JOIN appointments a ON b.appointment_id = a.appointment_id
        LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
        LEFT JOIN departments dept ON d.department_id = dept.department_id
        WHERE b.bill_id = %s
        """,
        (bill_id,),
        fetch="one"
    )

    if not bill:
        return None

    # Role-based access control
    if role == "patient" and bill["patient_id"] != user_id:
        return None

    # Fetch associated payments
    payments = execute_query(
        """
        SELECT payment_id, amount, payment_date, payment_method, transaction_reference, payment_status
        FROM payments
        WHERE bill_id = %s
        ORDER BY payment_date DESC
        """,
        (bill_id,),
        fetch="all"
    ) or []

    bill["payments"] = payments
    return bill


def record_simulated_payment(
    bill_id: int,
    amount: float,
    payment_method: str,
    patient_id: Optional[int] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Records a simulated payment within a database transaction.

    Verifies amount validity, computes new balance, updates bill status,
    and inserts payment with a unique reference.
    """
    if payment_method not in ("Cash", "Card", "UPI"):
        return False, "Invalid payment method selected. Must be Cash, Card, or UPI.", None

    try:
        amount = float(amount)
        if amount <= 0:
            return False, "Payment amount must be greater than zero.", None
    except (ValueError, TypeError):
        return False, "Invalid payment amount format.", None

    conn = get_db()
    cursor = get_db_cursor(conn)

    try:
        # Step 1: Lock and fetch current bill
        cursor.execute("SELECT * FROM bills WHERE bill_id = %s FOR UPDATE" 
                       if not hasattr(conn, "row_factory") 
                       else "SELECT * FROM bills WHERE bill_id = ?", 
                       (bill_id,))
        bill = cursor.fetchone()

        if not bill:
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "Bill not found.", None

        # Verify patient ownership if invoked by a patient
        b_patient_id = bill.get("patient_id") if isinstance(bill, dict) else bill[1]
        if patient_id and b_patient_id != patient_id:
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "Unauthorized access to this bill.", None

        total_amount = float(bill.get("total_amount") if isinstance(bill, dict) else bill[6])
        amount_paid = float(bill.get("amount_paid") if isinstance(bill, dict) else bill[7])
        balance = round(total_amount - amount_paid, 2)

        if balance <= 0:
            if hasattr(conn, "rollback"): conn.rollback()
            return False, "This bill has already been fully settled.", None

        if round(amount, 2) > balance:
            if hasattr(conn, "rollback"): conn.rollback()
            return False, f"Payment amount (${amount:.2f}) exceeds outstanding balance (${balance:.2f}).", None

        # Step 2: Generate unique transaction reference
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        rand_suffix = secrets.token_hex(4).upper()
        method_prefix = payment_method.upper()
        ref_code = f"SIM-{method_prefix}-{timestamp_str}-{rand_suffix}"

        # Step 3: Insert payment
        insert_pay_sql = """
            INSERT INTO payments (bill_id, amount, payment_method, transaction_reference, payment_status)
            VALUES (%s, %s, %s, %s, 'Success')
        """ if not hasattr(conn, "row_factory") else """
            INSERT INTO payments (bill_id, amount, payment_method, transaction_reference, payment_status)
            VALUES (?, ?, ?, ?, 'Success')
        """
        cursor.execute(insert_pay_sql, (bill_id, amount, payment_method, ref_code))

        # Step 4: Update bill total paid and status
        new_paid = round(amount_paid + amount, 2)
        new_status = "Paid" if new_paid >= total_amount else "Partially Paid"

        update_bill_sql = """
            UPDATE bills 
            SET amount_paid = %s, payment_status = %s
            WHERE bill_id = %s
        """ if not hasattr(conn, "row_factory") else """
            UPDATE bills 
            SET amount_paid = ?, payment_status = ?
            WHERE bill_id = ?
        """
        cursor.execute(update_bill_sql, (new_paid, new_status, bill_id))

        conn.commit()
        return True, "Simulated payment processed successfully!", {
            "transaction_reference": ref_code,
            "amount": amount,
            "new_balance": max(0.0, round(total_amount - new_paid, 2)),
            "payment_status": new_status
        }

    except Exception as e:
        if hasattr(conn, "rollback"):
            conn.rollback()
        return False, f"Transaction error: {str(e)}", None
    finally:
        if hasattr(cursor, "close"):
            cursor.close()
