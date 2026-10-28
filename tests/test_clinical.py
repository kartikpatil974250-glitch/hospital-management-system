"""Clinical EHR and Prescription Management Tests for PulseCare HMS."""

from database.connection import execute_query
from services.medical_record_service import create_medical_record_and_prescription, get_medical_record_by_id


def test_create_medical_record_and_prescription_atomic():
    """Verify medical record and multi-item prescription are saved atomically."""
    # Insert test appointment
    app_id = execute_query(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
        VALUES (1, 1, '2026-10-25', '09:00:00', '09:30:00', 'Persistent cough', 'Confirmed')
        """,
        commit=True
    )

    med_items = [
        {
            "medication_name": "Azithromycin",
            "dosage": "500 mg",
            "frequency": "Once daily",
            "duration": "3 days",
            "instructions": "Take before meals"
        },
        {
            "medication_name": "Dextromethorphan Syrup",
            "dosage": "10 ml",
            "frequency": "Three times daily",
            "duration": "5 days",
            "instructions": "Shake well"
        }
    ]

    ok, msg, rec_id = create_medical_record_and_prescription(
        doctor_id=1,
        patient_id=1,
        appointment_id=app_id,
        visit_date_str="2026-10-25",
        symptoms="Dry barking cough, low grade fever (38C), fatigue",
        diagnosis="Acute Bronchitis",
        treatment_notes="Hydration advised, rest for 3 days",
        allergies="None known",
        follow_up_date_str="2026-11-01",
        prescription_instructions="Complete full antibiotic course",
        medication_items=med_items
    )

    assert ok is True
    assert rec_id is not None

    # Check appointment status was updated to 'Completed'
    app = execute_query("SELECT status FROM appointments WHERE appointment_id = %s", (app_id,), fetch="one")
    assert app["status"] == "Completed"

    # Check record and prescription items
    record = get_medical_record_by_id(rec_id, user_id=1, role="patient")
    assert record is not None
    assert record["diagnosis"] == "Acute Bronchitis"
    assert record["prescription"] is not None
    assert len(record["prescription"]["items"]) == 2


def test_patient_medical_record_confidentiality():
    """Verify Patient 2 is blocked from viewing Patient 1's medical record."""
    # Create record for Patient 1
    app_id = execute_query(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, start_time, end_time, reason, status)
        VALUES (1, 1, '2026-10-20', '10:00:00', '10:30:00', 'Confidential check', 'Completed')
        """,
        commit=True
    )

    ok, _, rec_id = create_medical_record_and_prescription(
        doctor_id=1,
        patient_id=1,
        appointment_id=app_id,
        visit_date_str="2026-10-20",
        symptoms="Private symptom",
        diagnosis="Sensitive Condition",
        treatment_notes="Confidential"
    )
    assert ok is True

    # Patient 2 attempts access -> Must return None
    blocked = get_medical_record_by_id(rec_id, user_id=2, role="patient")
    assert blocked is None

    # Doctor or Admin access -> Allowed
    allowed = get_medical_record_by_id(rec_id, user_id=1, role="doctor")
    assert allowed is not None
