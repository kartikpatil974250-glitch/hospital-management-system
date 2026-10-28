-- ==============================================================================
-- HOSPITAL MANAGEMENT SYSTEM (PULSECARE HMS) - COMPLETE DATABASE DDL SCHEMA
-- Target RDBMS: MySQL 8.0+
-- Database Name: hospital_management_db
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS hospital_management_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE hospital_management_db;

-- ------------------------------------------------------------------------------
-- 1. DEPARTMENTS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    location VARCHAR(100),
    contact_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 2. PATIENTS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    address TEXT,
    emergency_contact VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patient_email (email),
    INDEX idx_patient_phone (phone)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 3. DOCTORS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    department_id INT NOT NULL,
    qualification VARCHAR(100) NOT NULL,
    years_experience INT NOT NULL DEFAULT 0,
    consultation_fee DECIMAL(10,2) NOT NULL DEFAULT 50.00,
    profile_image VARCHAR(255) DEFAULT 'default_doctor.png',
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_doctor_department FOREIGN KEY (department_id) 
        REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_doctor_department (department_id),
    INDEX idx_doctor_specialization (specialization),
    INDEX idx_doctor_active (is_active)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 4. DOCTOR SCHEDULES TABLE (Weekly routine)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctor_schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration INT NOT NULL DEFAULT 30, -- In minutes
    is_available BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_schedule_doctor FOREIGN KEY (doctor_id) 
        REFERENCES doctors(doctor_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_schedule_time CHECK (end_time > start_time),
    CONSTRAINT uq_doctor_day UNIQUE (doctor_id, day_of_week),
    INDEX idx_schedule_doctor_day (doctor_id, day_of_week)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 5. DOCTOR UNAVAILABILITY TABLE (Leaves, emergencies, out-of-office blocks)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctor_unavailability (
    unavailability_id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    reason VARCHAR(255),
    CONSTRAINT fk_unavail_doctor FOREIGN KEY (doctor_id) 
        REFERENCES doctors(doctor_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_unavail_time CHECK (end_datetime > start_datetime),
    INDEX idx_unavail_doctor_dates (doctor_id, start_datetime, end_datetime)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 6. APPOINTMENTS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    reason TEXT,
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Scheduled', 'Confirmed', 'Completed', 'Cancelled', 'No-show') DEFAULT 'Scheduled',
    cancellation_reason VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_app_patient FOREIGN KEY (patient_id) 
        REFERENCES patients(patient_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_app_doctor FOREIGN KEY (doctor_id) 
        REFERENCES doctors(doctor_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_appointment_time CHECK (end_time > start_time),
    INDEX idx_app_doctor_date (doctor_id, appointment_date, status),
    INDEX idx_app_patient (patient_id),
    INDEX idx_app_status (status)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 7. MEDICAL RECORDS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medical_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_id INT UNIQUE,
    visit_date DATE NOT NULL,
    symptoms TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    treatment_notes TEXT,
    allergies VARCHAR(255),
    follow_up_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_record_patient FOREIGN KEY (patient_id) 
        REFERENCES patients(patient_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_record_doctor FOREIGN KEY (doctor_id) 
        REFERENCES doctors(doctor_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_record_appointment FOREIGN KEY (appointment_id) 
        REFERENCES appointments(appointment_id) ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_record_patient (patient_id),
    INDEX idx_record_doctor (doctor_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 8. PRESCRIPTIONS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id INT AUTO_INCREMENT PRIMARY KEY,
    medical_record_id INT NOT NULL UNIQUE,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    prescription_date DATE NOT NULL,
    instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_presc_record FOREIGN KEY (medical_record_id) 
        REFERENCES medical_records(record_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_presc_patient FOREIGN KEY (patient_id) 
        REFERENCES patients(patient_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_presc_doctor FOREIGN KEY (doctor_id) 
        REFERENCES doctors(doctor_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_presc_patient (patient_id),
    INDEX idx_presc_record (medical_record_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 9. PRESCRIPTION ITEMS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescription_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT NOT NULL,
    medication_name VARCHAR(150) NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(100) NOT NULL,
    duration VARCHAR(50) NOT NULL,
    instructions VARCHAR(255),
    CONSTRAINT fk_item_prescription FOREIGN KEY (prescription_id) 
        REFERENCES prescriptions(prescription_id) ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_item_prescription (prescription_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 10. BILLS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bills (
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    appointment_id INT UNIQUE,
    consultation_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    additional_charges DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    amount_paid DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_status ENUM('Unpaid', 'Partially Paid', 'Paid') DEFAULT 'Unpaid',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bill_patient FOREIGN KEY (patient_id) 
        REFERENCES patients(patient_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_bill_appointment FOREIGN KEY (appointment_id) 
        REFERENCES appointments(appointment_id) ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_bill_patient (patient_id),
    INDEX idx_bill_status (payment_status)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 11. PAYMENTS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    payment_method ENUM('Cash', 'Card', 'UPI') NOT NULL,
    transaction_reference VARCHAR(100) NOT NULL UNIQUE,
    payment_status ENUM('Success', 'Failed', 'Pending') DEFAULT 'Success',
    CONSTRAINT fk_payment_bill FOREIGN KEY (bill_id) 
        REFERENCES bills(bill_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_payment_bill (bill_id),
    INDEX idx_payment_ref (transaction_reference)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 12. ADMINS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 13. AUDIT APPOINTMENT LOGS TABLE (For Trigger tracking)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_appointment_logs (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(255),
    INDEX idx_audit_app (appointment_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 14. VIEW: appointment_details_view
-- Combines appointment, patient, doctor, and department information
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW appointment_details_view AS
SELECT 
    a.appointment_id,
    a.patient_id,
    p.full_name AS patient_name,
    p.email AS patient_email,
    p.phone AS patient_phone,
    p.gender AS patient_gender,
    p.date_of_birth AS patient_dob,
    a.doctor_id,
    d.full_name AS doctor_name,
    d.email AS doctor_email,
    d.phone AS doctor_phone,
    d.specialization AS doctor_specialization,
    d.consultation_fee,
    dept.department_id,
    dept.department_name,
    dept.location AS department_location,
    a.appointment_date,
    a.start_time,
    a.end_time,
    a.reason,
    a.booking_date,
    a.status,
    a.cancellation_reason,
    a.created_at,
    a.updated_at,
    b.bill_id,
    b.payment_status AS bill_status,
    b.total_amount AS bill_total,
    b.amount_paid AS bill_paid,
    COALESCE(b.total_amount - b.amount_paid, 0) AS balance_due
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors d ON a.doctor_id = d.doctor_id
JOIN departments dept ON d.department_id = dept.department_id
LEFT JOIN bills b ON a.appointment_id = b.appointment_id;
