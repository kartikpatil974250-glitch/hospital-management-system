"""Billing and Simulated Payment Routes for PulseCare HMS."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from extensions import get_current_user, login_required, validate_csrf
from services.billing_service import get_bill_by_id, record_simulated_payment

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.route("/<int:bill_id>")
@login_required
def detail(bill_id: int):
    """Renders professional healthcare invoice with fee breakdown and payment ledger."""
    user = get_current_user()
    bill = get_bill_by_id(bill_id, user_id=user["id"], role=user["role"])

    if not bill:
        flash("Invoice not found or access denied.", "danger")
        if user["role"] == "patient":
            return redirect(url_for("patient.bills"))
        return redirect(url_for("admin.billing"))

    return render_template("billing/detail.html", bill=bill)


@billing_bp.route("/pay/<int:bill_id>", methods=["POST"])
@login_required
def pay(bill_id: int):
    """Processes simulated payment transaction with method selection."""
    validate_csrf()
    user = get_current_user()

    amount = request.form.get("amount", type=float)
    payment_method = request.form.get("payment_method", "Card")

    # If invoked by a patient, verify they own the bill
    patient_id = user["id"] if user["role"] == "patient" else None

    success, msg, pay_info = record_simulated_payment(
        bill_id=bill_id,
        amount=amount,
        payment_method=payment_method,
        patient_id=patient_id
    )

    if success:
        flash(f"{msg} Ref: {pay_info['transaction_reference']}", "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("billing.detail", bill_id=bill_id))
