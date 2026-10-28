"""Billing and Payment Ledger Tests for PulseCare HMS."""

from database.connection import execute_query
from services.billing_service import get_bill_by_id, record_simulated_payment


def test_bill_payment_partial_and_full():
    """Verify partial payments update balances correctly and final payment marks bill Paid."""
    # Create test bill directly
    bill_id = execute_query(
        """
        INSERT INTO bills (patient_id, consultation_fee, additional_charges, discount, total_amount, amount_paid, payment_status)
        VALUES (1, 100.00, 50.00, 10.00, 140.00, 0.00, 'Unpaid')
        """,
        commit=True
    )

    # 1. First partial payment: $40.00 via UPI
    ok1, msg1, pay_data1 = record_simulated_payment(bill_id, amount=40.00, payment_method="UPI", patient_id=1)
    assert ok1 is True
    assert pay_data1["payment_status"] == "Partially Paid"
    assert pay_data1["new_balance"] == 100.00

    # 2. Reject payment that exceeds remaining balance ($150.00 > $100.00 balance)
    ok_excess, msg_excess, _ = record_simulated_payment(bill_id, amount=150.00, payment_method="Card", patient_id=1)
    assert ok_excess is False
    assert "exceeds outstanding balance" in msg_excess

    # 3. Second payment for full remaining balance: $100.00 via Card
    ok2, msg2, pay_data2 = record_simulated_payment(bill_id, amount=100.00, payment_method="Card", patient_id=1)
    assert ok2 is True
    assert pay_data2["payment_status"] == "Paid"
    assert pay_data2["new_balance"] == 0.00

    # Verify database state
    bill_db = get_bill_by_id(bill_id)
    assert bill_db["payment_status"] == "Paid"
    assert float(bill_db["amount_paid"]) == 140.00
    assert len(bill_db["payments"]) == 2


def test_admin_bill_adjustment(admin_client):
    """Verify administrator can adjust additional charges and discounts on a bill."""
    bill_id = execute_query(
        """
        INSERT INTO bills (patient_id, consultation_fee, additional_charges, discount, total_amount, amount_paid, payment_status)
        VALUES (1, 100.00, 0.00, 0.00, 100.00, 0.00, 'Unpaid')
        """,
        commit=True
    )

    resp = admin_client.post(f"/admin/billing/update/{bill_id}", data={
        "csrf_token": "test-csrf-token",
        "additional_charges": 35.00,
        "discount": 15.00
    }, follow_redirects=True)

    assert resp.status_code == 200
    bill = execute_query("SELECT * FROM bills WHERE bill_id = %s", (bill_id,), fetch="one")
    # 100 fee + 35 additional - 15 discount = 120
    assert float(bill["total_amount"]) == 120.00
    assert float(bill["additional_charges"]) == 35.00
    assert float(bill["discount"]) == 15.00


def test_reject_invalid_payment_amounts():
    """Verify negative and zero payments are rejected."""
    bill_id = execute_query(
        "INSERT INTO bills (patient_id, total_amount, amount_paid, payment_status) VALUES (1, 100.00, 0.00, 'Unpaid')",
        commit=True
    )
    ok_zero, msg_zero, _ = record_simulated_payment(bill_id, amount=0.00, payment_method="Card")
    assert ok_zero is False
    assert "greater than zero" in msg_zero

    ok_neg, msg_neg, _ = record_simulated_payment(bill_id, amount=-25.00, payment_method="Card")
    assert ok_neg is False
    assert "greater than zero" in msg_neg


def test_prevent_duplicate_transaction_reference():
    """Verify DBMS uniqueness constraint on payments table prevents duplicate transaction reference."""
    import pytest

    bill_id = execute_query(
        "INSERT INTO bills (patient_id, total_amount, amount_paid, payment_status) VALUES (1, 100.00, 0.00, 'Unpaid')",
        commit=True
    )

    execute_query(
        """
        INSERT INTO payments (bill_id, amount, payment_method, transaction_reference, payment_status)
        VALUES (%s, 50.00, 'Card', 'TXN-UNIQUE-TEST-001', 'Success')
        """,
        (bill_id,),
        commit=True
    )

    with pytest.raises(Exception):
        execute_query(
            """
            INSERT INTO payments (bill_id, amount, payment_method, transaction_reference, payment_status)
            VALUES (%s, 25.00, 'Card', 'TXN-UNIQUE-TEST-001', 'Success')
            """,
            (bill_id,),
            commit=True
        )


