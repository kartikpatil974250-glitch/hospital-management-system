-- ==============================================================================
-- HOSPITAL MANAGEMENT SYSTEM (PULSECARE HMS) - SEED DATA
-- Default test credentials:
--   Admin:   admin@pulsecare.com   / Admin@123
--   Doctor:  sarah.jenkins@pulsecare.com / Doctor@123
--   Patient: john.doe@example.com  / Patient@123
-- ==============================================================================

USE hospital_management_db;

-- ------------------------------------------------------------------------------
-- 1. SEED DEPARTMENTS
-- ------------------------------------------------------------------------------
INSERT INTO departments (department_id, department_name, description, location, contact_number, is_active) VALUES
(1, 'Cardiology', 'Comprehensive cardiovascular medicine, cardiac imaging, and post-infarct rehabilitation.', 'Block A, Floor 2', '+1-555-0101', TRUE),
(2, 'Neurology', 'Diagnosis and surgical/non-surgical care for central and peripheral nervous system disorders.', 'Block B, Floor 3', '+1-555-0102', TRUE),
(3, 'Orthopedics', 'Musculoskeletal trauma, arthroplasty, sports medicine, and spinal therapeutics.', 'Block A, Floor 1', '+1-555-0103', TRUE),
(4, 'Pediatrics', 'Specialized medical care and developmental tracking for infants, children, and adolescents.', 'Block C, Floor 1', '+1-555-0104', TRUE),
(5, 'Dermatology', 'Advanced clinical dermatology, cutaneous allergy evaluations, and cosmetic therapeutics.', 'Block B, Floor 2', '+1-555-0105', TRUE),
(6, 'General Medicine', 'Primary outpatient adult care, acute diagnostics, and chronic disease preventative management.', 'Outpatient Wing, Ground Floor', '+1-555-0106', TRUE)
ON DUPLICATE KEY UPDATE department_name=VALUES(department_name);

-- ------------------------------------------------------------------------------
-- 2. SEED ADMINS
-- Password: Admin@123
-- ------------------------------------------------------------------------------
INSERT INTO admins (admin_id, full_name, email, password_hash, role) VALUES
(1, 'System Administrator', 'admin@pulsecare.com', 'scrypt:32768:8:1$7bYrOUrSSts8Mtv1$2cebc08bb6143bc8cffc83b16dfdde7de5b3c5c0d1da90c3bfdd1a777e0b8a6340b4cbed8729df43a0e63c8e77f21ac20c250cc70913a6f8922b4e959674601c', 'Super Admin')
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- ------------------------------------------------------------------------------
-- 3. SEED DOCTORS
-- Password for all doctors: Doctor@123
-- ------------------------------------------------------------------------------
INSERT INTO doctors (doctor_id, full_name, email, phone, specialization, department_id, qualification, years_experience, consultation_fee, profile_image, password_hash, is_active) VALUES
(1, 'Dr. Sarah Jenkins', 'sarah.jenkins@pulsecare.com', '+1-555-0201', 'Interventional Cardiologist', 1, 'MD, FACC, FSCAI', 14, 120.00, 'doctor1.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(2, 'Dr. Marcus Vance', 'marcus.vance@pulsecare.com', '+1-555-0202', 'Consultant Neurologist', 2, 'MD, PhD (Neuroscience), FAAN', 16, 150.00, 'doctor2.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(3, 'Dr. Priya Sharma', 'priya.sharma@pulsecare.com', '+1-555-0203', 'Orthopedic Surgeon', 3, 'MS (Ortho), MCh, FRCS', 11, 95.00, 'doctor3.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(4, 'Dr. David Chen', 'david.chen@pulsecare.com', '+1-555-0204', 'Consultant Pediatrician', 4, 'MD (Pediatrics), FAAP', 9, 85.00, 'doctor4.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(5, 'Dr. Elena Gomez', 'elena.gomez@pulsecare.com', '+1-555-0205', 'Clinical Dermatologist', 5, 'MD (Dermatology), FAAD', 12, 90.00, 'doctor5.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(6, 'Dr. Robert Taylor', 'robert.taylor@pulsecare.com', '+1-555-0206', 'Chief Internal Medicine', 6, 'MD (Int. Med), FACP', 18, 75.00, 'doctor6.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(7, 'Dr. Maya Patel', 'maya.patel@pulsecare.com', '+1-555-0207', 'Clinical Cardiac Electrophysiologist', 1, 'MD, FHRS, FACC', 13, 135.00, 'doctor7.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(8, 'Dr. James Wilson', 'james.wilson@pulsecare.com', '+1-555-0208', 'Cerebrovascular Neurosurgeon', 2, 'MD, FACS, FAANS', 15, 175.00, 'doctor8.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(9, 'Dr. Chloe Bennett', 'chloe.bennett@pulsecare.com', '+1-555-0209', 'Sports Medicine & Joint Reconstruction', 3, 'MD, FAAOS', 10, 110.00, 'doctor9.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(10, 'Dr. Samuel Kim', 'samuel.kim@pulsecare.com', '+1-555-0210', 'Pediatric Critical Care Specialist', 4, 'MD (Pediatrics), FAAP', 12, 95.00, 'doctor10.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(11, 'Dr. Fatima Al-Mansoor', 'fatima.mansoor@pulsecare.com', '+1-555-0211', 'Pediatric & Aesthetic Dermatologist', 5, 'MD, FAAD', 8, 100.00, 'doctor11.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE),
(12, 'Dr. Lucas Meyer', 'lucas.meyer@pulsecare.com', '+1-555-0212', 'Family Physician & Preventive Care', 6, 'MD, FAAFP', 14, 80.00, 'doctor12.jpg', 'scrypt:32768:8:1$pvgxISq0eLoNPAE9$b626bcc1bc5ee61ad21e09e4a5a93c8be3d5fe24360d851b3d1a5aa49c923a42ca70c269605d885e1ed5114ef1ba75f62da12bdfd8fa459be495fe40224823ef', TRUE)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- ------------------------------------------------------------------------------
-- 4. SEED DOCTOR SCHEDULES (Weekly slots)
-- ------------------------------------------------------------------------------
INSERT INTO doctor_schedules (doctor_id, day_of_week, start_time, end_time, slot_duration, is_available) VALUES
-- Dr. Sarah Jenkins (Cardiology) - Mon, Wed, Fri
(1, 'Monday', '09:00:00', '13:00:00', 30, TRUE),
(1, 'Wednesday', '09:00:00', '13:00:00', 30, TRUE),
(1, 'Friday', '14:00:00', '18:00:00', 30, TRUE),

-- Dr. Marcus Vance (Neurology) - Tue, Thu, Sat
(2, 'Tuesday', '10:00:00', '16:00:00', 30, TRUE),
(2, 'Thursday', '10:00:00', '16:00:00', 30, TRUE),
(2, 'Saturday', '09:00:00', '13:00:00', 30, TRUE),

-- Dr. Priya Sharma (Orthopedics) - Mon, Tue, Thu
(3, 'Monday', '09:00:00', '14:00:00', 30, TRUE),
(3, 'Tuesday', '09:00:00', '14:00:00', 30, TRUE),
(3, 'Thursday', '13:00:00', '17:00:00', 30, TRUE),

-- Dr. David Chen (Pediatrics) - Mon, Wed, Fri
(4, 'Monday', '08:30:00', '12:30:00', 30, TRUE),
(4, 'Wednesday', '08:30:00', '12:30:00', 30, TRUE),
(4, 'Friday', '08:30:00', '12:30:00', 30, TRUE),

-- Dr. Elena Gomez (Dermatology) - Tue, Wed, Fri
(5, 'Tuesday', '11:00:00', '17:00:00', 30, TRUE),
(5, 'Wednesday', '11:00:00', '17:00:00', 30, TRUE),
(5, 'Friday', '11:00:00', '16:00:00', 30, TRUE),

-- Dr. Robert Taylor (General Medicine) - Mon thru Fri
(6, 'Monday', '08:00:00', '16:00:00', 30, TRUE),
(6, 'Tuesday', '08:00:00', '16:00:00', 30, TRUE),
(6, 'Wednesday', '08:00:00', '16:00:00', 30, TRUE),
(6, 'Thursday', '08:00:00', '16:00:00', 30, TRUE),
(6, 'Friday', '08:00:00', '16:00:00', 30, TRUE),

-- Dr. Maya Patel (Cardiology) - Tue, Thu, Sat
(7, 'Tuesday', '09:00:00', '14:00:00', 30, TRUE),
(7, 'Thursday', '09:00:00', '14:00:00', 30, TRUE),
(7, 'Saturday', '10:00:00', '15:00:00', 30, TRUE),

-- Dr. James Wilson (Neurology) - Mon, Wed, Fri
(8, 'Monday', '10:00:00', '17:00:00', 30, TRUE),
(8, 'Wednesday', '10:00:00', '17:00:00', 30, TRUE),
(8, 'Friday', '10:00:00', '16:00:00', 30, TRUE),

-- Dr. Chloe Bennett (Orthopedics) - Tue, Wed, Fri
(9, 'Tuesday', '09:00:00', '13:00:00', 30, TRUE),
(9, 'Wednesday', '13:00:00', '18:00:00', 30, TRUE),
(9, 'Friday', '09:00:00', '13:00:00', 30, TRUE),

-- Dr. Samuel Kim (Pediatrics) - Mon, Tue, Thu
(10, 'Monday', '08:00:00', '13:00:00', 30, TRUE),
(10, 'Tuesday', '08:00:00', '13:00:00', 30, TRUE),
(10, 'Thursday', '08:00:00', '13:00:00', 30, TRUE),

-- Dr. Fatima Al-Mansoor (Dermatology) - Mon, Wed, Thu
(11, 'Monday', '11:00:00', '16:00:00', 30, TRUE),
(11, 'Wednesday', '11:00:00', '16:00:00', 30, TRUE),
(11, 'Thursday', '11:00:00', '16:00:00', 30, TRUE),

-- Dr. Lucas Meyer (General Medicine) - Mon thru Fri
(12, 'Monday', '08:30:00', '15:30:00', 30, TRUE),
(12, 'Tuesday', '08:30:00', '15:30:00', 30, TRUE),
(12, 'Wednesday', '08:30:00', '15:30:00', 30, TRUE),
(12, 'Thursday', '08:30:00', '15:30:00', 30, TRUE),
(12, 'Friday', '08:30:00', '15:30:00', 30, TRUE)
ON DUPLICATE KEY UPDATE start_time=VALUES(start_time), end_time=VALUES(end_time);

-- ------------------------------------------------------------------------------
-- 5. SEED PATIENTS
-- Password for all patients: Patient@123
-- ------------------------------------------------------------------------------
INSERT INTO patients (patient_id, full_name, email, phone, date_of_birth, gender, address, emergency_contact, password_hash) VALUES
(1, 'John Doe', 'john.doe@example.com', '+1-555-1001', '1985-06-15', 'Male', '742 Evergreen Terrace, Springfield', '+1-555-9001 (Wife)', 'scrypt:32768:8:1$OlboNiOaRy0h0pNE$05fd1578a6b36c6cfeaa8ed89f671ed2739cc47658fd8bf0430300da37460e616e8c99e3f3e6acf8662e9bda53367fa2c27f111717d76fc15fd914d497d6eb23'),
(2, 'Jane Smith', 'jane.smith@example.com', '+1-555-1002', '1992-11-20', 'Female', '128 Baker Street, Seattle, WA', '+1-555-9002 (Mother)', 'scrypt:32768:8:1$OlboNiOaRy0h0pNE$05fd1578a6b36c6cfeaa8ed89f671ed2739cc47658fd8bf0430300da37460e616e8c99e3f3e6acf8662e9bda53367fa2c27f111717d76fc15fd914d497d6eb23'),
(3, 'Michael Brown', 'michael.brown@example.com', '+1-555-1003', '1978-03-30', 'Male', '45 Ocean View Ave, San Diego, CA', '+1-555-9003 (Brother)', 'scrypt:32768:8:1$OlboNiOaRy0h0pNE$05fd1578a6b36c6cfeaa8ed89f671ed2739cc47658fd8bf0430300da37460e616e8c99e3f3e6acf8662e9bda53367fa2c27f111717d76fc15fd914d497d6eb23'),
(4, 'Emily Davis', 'emily.davis@example.com', '+1-555-1004', '2001-08-14', 'Female', '902 Elmwood Lane, Austin, TX', '+1-555-9004 (Father)', 'scrypt:32768:8:1$OlboNiOaRy0h0pNE$05fd1578a6b36c6cfeaa8ed89f671ed2739cc47658fd8bf0430300da37460e616e8c99e3f3e6acf8662e9bda53367fa2c27f111717d76fc15fd914d497d6eb23')
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- ------------------------------------------------------------------------------
-- 6. SEED APPOINTMENTS
-- ------------------------------------------------------------------------------
INSERT INTO appointments (appointment_id, patient_id, doctor_id, appointment_date, start_time, end_time, reason, status, cancellation_reason) VALUES
-- Past completed consultations
(1, 1, 1, '2026-10-12', '09:30:00', '10:00:00', 'Routine cardiac stress evaluation & elevated BP checkup', 'Completed', NULL),
(2, 2, 2, '2026-10-13', '10:00:00', '10:30:00', 'Persistent unilateral migraine with visual aura', 'Completed', NULL),
(3, 3, 3, '2026-10-15', '11:00:00', '11:30:00', 'Right knee pain following athletic activity', 'Completed', NULL),

-- Recent & Upcoming bookings
(4, 1, 6, '2026-10-23', '09:00:00', '09:30:00', 'Annual metabolic blood panel review and general health checkup', 'Confirmed', NULL),
(5, 4, 5, '2026-10-27', '11:30:00', '12:00:00', 'Eczematous skin lesion on forearm and contact allergy test', 'Scheduled', NULL),
(6, 2, 1, '2026-10-28', '10:30:00', '11:00:00', 'Echocardiogram follow-up consultation', 'Scheduled', NULL),

-- Cancelled appointment example
(7, 3, 6, '2026-10-18', '14:00:00', '14:30:00', 'Seasonal allergy follow-up', 'Cancelled', 'Patient had urgent work travel schedule conflict')
ON DUPLICATE KEY UPDATE status=VALUES(status);

-- ------------------------------------------------------------------------------
-- 7. SEED MEDICAL RECORDS
-- ------------------------------------------------------------------------------
INSERT INTO medical_records (record_id, patient_id, doctor_id, appointment_id, visit_date, symptoms, diagnosis, treatment_notes, allergies, follow_up_date) VALUES
(1, 1, 1, 1, '2026-10-12', 'Intermittent chest tightness during vigorous exercise, mild dizziness, resting BP 142/90 mmHg.', 'Stage 1 Essential Hypertension with mild exertional angina symptoms.', 'Resting ECG demonstrated normal sinus rhythm with no ST changes. Recommended low-sodium DASH diet, daily aerobic walking, and started ACE inhibitor therapy.', 'Penicillin', '2026-11-12'),
(2, 2, 2, 2, '2026-10-13', 'Severe throbbing left temporal headache recurring 3x/week, photophobia, nausea.', 'Episodic Migraine with Aura without intractable status.', 'Cranial nerve exam normal. Recommended lifestyle sleep routine tracking, avoidance of dietary triggers, and prescribed triptan abortive therapy.', 'Sulfa drugs', '2026-11-20'),
(3, 3, 3, 3, '2026-10-15', 'Swelling and joint line tenderness along medial right knee, unable to fully bear weight.', 'Grade II Medial Meniscal Sprain, Right Knee.', 'Joint aspiration not required. Prescribed non-steroidal anti-inflammatory, compressive sleeve, and referred for 6 sessions of physical therapy.', 'None known', '2026-11-05')
ON DUPLICATE KEY UPDATE diagnosis=VALUES(diagnosis);

-- ------------------------------------------------------------------------------
-- 8. SEED PRESCRIPTIONS & PRESCRIPTION ITEMS
-- ------------------------------------------------------------------------------
INSERT INTO prescriptions (prescription_id, medical_record_id, patient_id, doctor_id, prescription_date, instructions) VALUES
(1, 1, 1, 1, '2026-10-12', 'Take antihypertensive medications with a glass of water every morning. Monitor daily resting blood pressure.'),
(2, 2, 2, 2, '2026-10-13', 'Take abortive migraine tablets immediately at symptom onset. Stay hydrated and rest in a dark room.'),
(3, 3, 3, 3, '2026-10-15', 'Take oral anti-inflammatories strictly after food. Apply topical ice packs for 15 minutes three times daily.')
ON DUPLICATE KEY UPDATE instructions=VALUES(instructions);

INSERT INTO prescription_items (item_id, prescription_id, medication_name, dosage, frequency, duration, instructions) VALUES
-- For John Doe (Hypertension)
(1, 1, 'Lisinopril', '10 mg', 'Once daily (Morning)', '30 days', 'Take at 8:00 AM daily with breakfast'),
(2, 1, 'Amlodipine Besylate', '5 mg', 'Once daily (Night)', '30 days', 'Take before bedtime'),

-- For Jane Smith (Migraine)
(3, 2, 'Sumatriptan', '50 mg', 'As needed at aura onset', '10 tablets', 'Do not exceed 100 mg in a 24-hour period'),
(4, 2, 'Magnesium Glycinate', '400 mg', 'Once daily at bedtime', '60 days', 'Prophylactic neurological support'),

-- For Michael Brown (Knee Sprain)
(5, 3, 'Naproxen Sodium', '500 mg', 'Twice daily after meals', '10 days', 'Discontinue if gastric discomfort arises'),
(6, 3, 'Paracetamol', '650 mg', 'Every 8 hours as needed', '5 days', 'For breakthrough pain')
ON DUPLICATE KEY UPDATE dosage=VALUES(dosage);

-- ------------------------------------------------------------------------------
-- 9. SEED BILLS
-- ------------------------------------------------------------------------------
INSERT INTO bills (bill_id, patient_id, appointment_id, consultation_fee, additional_charges, discount, total_amount, amount_paid, payment_status) VALUES
-- John Doe (App #1 - Paid)
(1, 1, 1, 120.00, 45.00, 15.00, 150.00, 150.00, 'Paid'),

-- Jane Smith (App #2 - Paid)
(2, 2, 2, 150.00, 20.00, 0.00, 170.00, 170.00, 'Paid'),

-- Michael Brown (App #3 - Partially Paid)
(3, 3, 3, 95.00, 35.00, 10.00, 120.00, 60.00, 'Partially Paid'),

-- John Doe (App #4 - Upcoming / Unpaid)
(4, 1, 4, 75.00, 0.00, 0.00, 75.00, 0.00, 'Unpaid')
ON DUPLICATE KEY UPDATE total_amount=VALUES(total_amount);

-- ------------------------------------------------------------------------------
-- 10. SEED PAYMENTS
-- ------------------------------------------------------------------------------
INSERT INTO payments (payment_id, bill_id, amount, payment_date, payment_method, transaction_reference, payment_status) VALUES
(1, 1, 150.00, '2026-10-12 10:15:22', 'Card', 'TXN-CARD-20261012-001', 'Success'),
(2, 2, 170.00, '2026-10-13 10:45:10', 'UPI', 'TXN-UPI-20261013-002', 'Success'),
(3, 3, 60.00, '2026-10-15 11:42:00', 'Cash', 'TXN-CASH-20261015-003', 'Success')
ON DUPLICATE KEY UPDATE amount=VALUES(amount);
