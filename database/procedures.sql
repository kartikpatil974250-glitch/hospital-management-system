-- ==============================================================================
-- HOSPITAL MANAGEMENT SYSTEM (PULSECARE HMS) - PROCEDURES & TRIGGERS
-- Target RDBMS: MySQL 8.0+
-- Database: hospital_management_db
-- ==============================================================================

USE hospital_management_db;

DELIMITER $$

-- ------------------------------------------------------------------------------
-- STORED PROCEDURE 1: sp_get_patient_appointment_history
-- Retrieves full appointment history for a given patient with doctor and department details
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_get_patient_appointment_history$$
CREATE PROCEDURE sp_get_patient_appointment_history(
    IN p_patient_id INT
)
BEGIN
    SELECT 
        a.appointment_id,
        a.appointment_date,
        a.start_time,
        a.end_time,
        a.reason,
        a.status,
        a.cancellation_reason,
        d.doctor_id,
        d.full_name AS doctor_name,
        d.specialization,
        d.consultation_fee,
        dept.department_name,
        b.bill_id,
        b.total_amount,
        b.amount_paid,
        b.payment_status
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.doctor_id
    JOIN departments dept ON d.department_id = dept.department_id
    LEFT JOIN bills b ON a.appointment_id = b.appointment_id
    WHERE a.patient_id = p_patient_id
    ORDER BY a.appointment_date DESC, a.start_time DESC;
END$$

-- ------------------------------------------------------------------------------
-- STORED PROCEDURE 2: sp_get_doctor_schedule_stats
-- Generates aggregate clinical statistics for a doctor's dashboard
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_get_doctor_schedule_stats$$
CREATE PROCEDURE sp_get_doctor_schedule_stats(
    IN p_doctor_id INT
)
BEGIN
    SELECT 
        COUNT(CASE WHEN appointment_date = CURDATE() AND status IN ('Scheduled', 'Confirmed') THEN 1 END) AS today_appointments,
        COUNT(CASE WHEN appointment_date > CURDATE() AND status IN ('Scheduled', 'Confirmed') THEN 1 END) AS upcoming_appointments,
        COUNT(CASE WHEN status = 'Completed' THEN 1 END) AS completed_consultations,
        COUNT(DISTINCT patient_id) AS total_unique_patients
    FROM appointments
    WHERE doctor_id = p_doctor_id;
END$$

-- ------------------------------------------------------------------------------
-- TRIGGER 1: trg_appointment_status_update
-- Automatically records status transition audits whenever an appointment status changes
-- ------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_appointment_status_update$$
CREATE TRIGGER trg_appointment_status_update
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO audit_appointment_logs (
            appointment_id,
            old_status,
            new_status,
            changed_at,
            remarks
        ) VALUES (
            NEW.appointment_id,
            OLD.status,
            NEW.status,
            NOW(),
            CASE 
                WHEN NEW.status = 'Cancelled' THEN CONCAT('Cancelled: ', COALESCE(NEW.cancellation_reason, 'No reason provided'))
                WHEN NEW.status = 'Completed' THEN 'Consultation completed by clinician'
                WHEN NEW.status = 'Confirmed' THEN 'Appointment confirmed'
                WHEN NEW.status = 'No-show' THEN 'Patient did not attend appointment'
                ELSE 'Status updated'
            END
        );
    END IF;
END$$

-- ------------------------------------------------------------------------------
-- TRIGGER 2: trg_appointment_insert_audit
-- Automatically records initial booking creation audit
-- ------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_appointment_insert_audit$$
CREATE TRIGGER trg_appointment_insert_audit
AFTER INSERT ON appointments
FOR EACH ROW
BEGIN
    INSERT INTO audit_appointment_logs (
        appointment_id,
        old_status,
        new_status,
        changed_at,
        remarks
    ) VALUES (
        NEW.appointment_id,
        NULL,
        NEW.status,
        NOW(),
        'Initial appointment scheduled'
    );
END$$

DELIMITER ;
