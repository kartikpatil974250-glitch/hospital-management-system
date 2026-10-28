"""Medical Record and Clinical Prescription Service for PulseCare HMS.

Handles diagnosis recording, clinical notes, multi-item prescriptions,
and patient confidentiality validation.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from database.connection import execute_query, get_db, get_db_cursor


def create_medical_record_and_prescription(
    doctor_id: int,
    patient_id: int,
    appointment_id: int,
    visit_date_str: str,
    symptoms: str,
    diagnosis: str,
    treatment_notes: str,
    allergies: Optional[str] = None,
    follow_up_date_str: Optional[str] = None,
    prescription_instructions: Optional[str] = None,
    medication_items: Optional[List[Dict[str, str]]] = None
) -> Tuple[bool, str, Optional[int]]:
    """Creates a medical record, associated prescription, and medication items

    in a single atomic database transaction. Also marks the appointment as 'Completed'.
    """
    if not diagnosis or not symptoms:
        return False, "Symptoms and diagnosis are mandatory clinical fields.", None

    conn = get_db()
    cursor = get_db_cursor(conn)

    try:
        # Step 1: Insert Medical Record
        insert_rec_sql = """
            INSERT INTO medical_records (patient_id, doctor_id, appointment_id, visit_date, symptoms, diagnosis, treatment_notes, allergies, follow_up_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """ if not hasattr(conn, "row_factory") else """
            INSERT INTO medical_records (patient_id, doctor_id, appointment_id, visit_date, symptoms, diagnosis, treatment_notes, allergies, follow_up_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        follow_up = follow_up_date_str if follow_up_date_str else None
        cursor.execute(insert_rec_sql, (
            patient_id, doctor_id, appointment_id, visit_date_str,
            symptoms, diagnosis, treatment_notes, allergies, follow_up
        ))
        record_id = cursor.lastrowid

        # Step 2: Update Appointment Status to 'Completed'
        update_app_sql = """
            UPDATE appointments SET status = 'Completed', updated_at = CURRENT_TIMESTAMP
            WHERE appointment_id = %s
        """ if not hasattr(conn, "row_factory") else """
            UPDATE appointments SET status = 'Completed', updated_at = CURRENT_TIMESTAMP
            WHERE appointment_id = ?
        """
        cursor.execute(update_app_sql, (appointment_id,))

        # Step 3: Insert Prescription if medications or instructions are present
        if prescription_instructions or (medication_items and len(medication_items) > 0):
            insert_presc_sql = """
                INSERT INTO prescriptions (medical_record_id, patient_id, doctor_id, prescription_date, instructions)
                VALUES (%s, %s, %s, %s, %s)
            """ if not hasattr(conn, "row_factory") else """
                INSERT INTO prescriptions (medical_record_id, patient_id, doctor_id, prescription_date, instructions)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_presc_sql, (
                record_id, patient_id, doctor_id, visit_date_str, prescription_instructions or ""
            ))
            prescription_id = cursor.lastrowid

            # Step 4: Insert Prescription Items
            if medication_items:
                for item in medication_items:
                    name = item.get("medication_name", "").strip()
                    if name:
                        insert_item_sql = """
                            INSERT INTO prescription_items (prescription_id, medication_name, dosage, frequency, duration, instructions)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """ if not hasattr(conn, "row_factory") else """
                            INSERT INTO prescription_items (prescription_id, medication_name, dosage, frequency, duration, instructions)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """
                        cursor.execute(insert_item_sql, (
                            prescription_id,
                            name,
                            item.get("dosage", "As directed"),
                            item.get("frequency", "Once daily"),
                            item.get("duration", "5 days"),
                            item.get("instructions", "")
                        ))

        conn.commit()
        return True, "Clinical medical record and prescription saved successfully.", record_id

    except Exception as e:
        if hasattr(conn, "rollback"):
            conn.rollback()
        return False, f"Database transaction failed: {str(e)}", None
    finally:
        if hasattr(cursor, "close"):
            cursor.close()


def get_medical_record_by_id(record_id: int, user_id: int, role: str) -> Optional[Dict[str, Any]]:
    """Fetches a detailed medical record with its prescription and prescription items,

    enforcing patient/doctor authorization.
    """
    record = execute_query(
        """
        SELECT 
            r.record_id,
            r.patient_id,
            r.doctor_id,
            r.appointment_id,
            r.visit_date,
            r.symptoms,
            r.diagnosis,
            r.treatment_notes,
            r.allergies,
            r.follow_up_date,
            r.created_at,
            p.full_name AS patient_name,
            p.email AS patient_email,
            p.phone AS patient_phone,
            p.date_of_birth AS patient_dob,
            p.gender AS patient_gender,
            d.full_name AS doctor_name,
            d.specialization,
            dept.department_name
        FROM medical_records r
        JOIN patients p ON r.patient_id = p.patient_id
        JOIN doctors d ON r.doctor_id = d.doctor_id
        JOIN departments dept ON d.department_id = dept.department_id
        WHERE r.record_id = %s
        """,
        (record_id,),
        fetch="one"
    )

    if not record:
        return None

    # Confidentiality check: Patients may only see their own records
    if role == "patient" and record["patient_id"] != user_id:
        return None

    # Fetch associated prescription if any
    prescription = execute_query(
        """
        SELECT prescription_id, prescription_date, instructions
        FROM prescriptions
        WHERE medical_record_id = %s
        """,
        (record_id,),
        fetch="one"
    )

    if prescription:
        items = execute_query(
            """
            SELECT item_id, medication_name, dosage, frequency, duration, instructions
            FROM prescription_items
            WHERE prescription_id = %s
            """,
            (prescription["prescription_id"],),
            fetch="all"
        ) or []
        prescription["items"] = items
        prescription["medication_items"] = items
        record["prescription"] = prescription
    else:
        record["prescription"] = None

    return record
