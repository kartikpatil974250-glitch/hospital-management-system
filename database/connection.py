"""Database connection manager for PulseCare Hospital Management System.

Supports mysql-connector-python with connection pooling, parameterized queries,
transactions, and an in-memory/sqlite compatibility mode for offline test execution.
"""

from datetime import date, datetime
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import current_app, g, has_app_context

try:
    import mysql.connector
    from mysql.connector import pooling, errors
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    errors = None


_mysql_pool = None
_sqlite_standalone_conn = None


def init_mysql_pool(app_config):
    """Initializes the MySQL connection pool."""
    global _mysql_pool
    if not MYSQL_AVAILABLE:
        return None

    try:
        pool_args = {
            "pool_name": app_config.get("DB_POOL_NAME", "pulsecare_pool"),
            "pool_size": app_config.get("DB_POOL_SIZE", 5),
            "pool_reset_session": True,
            "host": app_config.get("DB_HOST", "localhost"),
            "port": int(app_config.get("DB_PORT", 3306)),
            "database": app_config.get("DB_NAME", "hospital_management_db"),
            "user": app_config.get("DB_USER", "root"),
            "password": app_config.get("DB_PASSWORD", ""),
            "autocommit": False,
            "charset": "utf8mb4",
        }
        _mysql_pool = pooling.MySQLConnectionPool(**pool_args)
        return _mysql_pool
    except Exception:
        return None


def get_db():
    """Gets a database connection for current context or standalone."""
    in_ctx = has_app_context()
    if in_ctx and "db" in g:
        return g.db

    global _mysql_pool
    use_sqlite = os.environ.get("USE_SQLITE_FALLBACK", "0") == "1"

    if not use_sqlite and MYSQL_AVAILABLE:
        if _mysql_pool is None and in_ctx and current_app:
            init_mysql_pool(current_app.config)

        if _mysql_pool:
            try:
                conn = _mysql_pool.get_connection()
                if in_ctx:
                    g.db = conn
                    g.db_type = "mysql"
                return conn
            except Exception:
                pass

    conn = _get_or_create_sqlite_conn()
    if in_ctx:
        g.db = conn
        g.db_type = "sqlite"
    return conn


def _get_or_create_sqlite_conn():
    """Initializes and returns SQLite connection with dict-like rows and MySQL function shims."""
    global _sqlite_standalone_conn
    db_path = os.environ.get("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "hms_fallback.db"))

    if _sqlite_standalone_conn is None:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Register MySQL compatibility functions in SQLite
        conn.create_function("CURDATE", 0, lambda: date.today().strftime("%Y-%m-%d"))
        conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        _ensure_sqlite_tables(conn)
        _sqlite_standalone_conn = conn

    return _sqlite_standalone_conn


def _ensure_sqlite_tables(conn):
    """Ensures fallback tables exist when using SQLite mode."""
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS departments (
            department_id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_name TEXT NOT NULL UNIQUE,
            description TEXT,
            location TEXT,
            contact_number TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            date_of_birth DATE NOT NULL,
            gender TEXT NOT NULL,
            address TEXT,
            emergency_contact TEXT,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            specialization TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            qualification TEXT NOT NULL,
            years_experience INTEGER DEFAULT 0,
            consultation_fee REAL DEFAULT 50.00,
            profile_image TEXT DEFAULT 'default_doctor.png',
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );

        CREATE TABLE IF NOT EXISTS doctor_schedules (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            slot_duration INTEGER DEFAULT 30,
            is_available INTEGER DEFAULT 1,
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
            UNIQUE (doctor_id, day_of_week)
        );

        CREATE TABLE IF NOT EXISTS doctor_unavailability (
            unavailability_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            start_datetime DATETIME NOT NULL,
            end_datetime DATETIME NOT NULL,
            reason TEXT,
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );

        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date DATE NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            reason TEXT,
            booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Scheduled',
            cancellation_reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );

        CREATE TABLE IF NOT EXISTS medical_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_id INTEGER UNIQUE,
            visit_date DATE NOT NULL,
            symptoms TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            treatment_notes TEXT,
            allergies TEXT,
            follow_up_date DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        );

        CREATE TABLE IF NOT EXISTS prescriptions (
            prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
            medical_record_id INTEGER NOT NULL UNIQUE,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            prescription_date DATE NOT NULL,
            instructions TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medical_record_id) REFERENCES medical_records(record_id),
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );

        CREATE TABLE IF NOT EXISTS prescription_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prescription_id INTEGER NOT NULL,
            medication_name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            duration TEXT NOT NULL,
            instructions TEXT,
            FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS bills (
            bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            appointment_id INTEGER UNIQUE,
            consultation_fee REAL DEFAULT 0.00,
            additional_charges REAL DEFAULT 0.00,
            discount REAL DEFAULT 0.00,
            total_amount REAL DEFAULT 0.00,
            amount_paid REAL DEFAULT 0.00,
            payment_status TEXT DEFAULT 'Unpaid',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT NOT NULL,
            transaction_reference TEXT NOT NULL UNIQUE,
            payment_status TEXT DEFAULT 'Success',
            FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
        );

        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_appointment_logs (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            remarks TEXT
        );

        CREATE TRIGGER IF NOT EXISTS trg_appointment_status_update
        AFTER UPDATE ON appointments
        FOR EACH ROW
        WHEN OLD.status <> NEW.status
        BEGIN
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
                DATETIME('now'),
                'Status updated from ' || OLD.status || ' to ' || NEW.status
            );
        END;

        CREATE VIEW IF NOT EXISTS appointment_details_view AS
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
        """)


def get_db_cursor(conn, dictionary=True):
    """Returns a dictionary cursor for MySQL or standard cursor for SQLite."""
    if isinstance(conn, sqlite3.Connection):
        return conn.cursor()
    try:
        return conn.cursor(dictionary=dictionary)
    except (TypeError, AttributeError):
        return conn.cursor()


def close_db(e=None):
    """Closes current request's database connection."""
    if has_app_context():
        db = g.pop("db", None)
        if db is not None:
            db_type = g.pop("db_type", None)
            if db_type == "mysql":
                try:
                    db.close()
                except Exception:
                    pass


def execute_query(
    query: str,
    params: Optional[Union[tuple, list, dict]] = None,
    fetch: Optional[str] = None,
    commit: bool = False,
    dictionary: bool = True
) -> Any:
    """Executes a parameterized SQL query with automatic cursor management."""
    conn = get_db()
    db_type = getattr(g, "db_type", "mysql") if has_app_context() else ("mysql" if hasattr(conn, "pool_name") else "sqlite")
    params = params or ()

    if db_type == "mysql" and hasattr(conn, "cursor"):
        cursor = conn.cursor(dictionary=dictionary)
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()

            if fetch == "one":
                return cursor.fetchone()
            elif fetch == "all":
                return cursor.fetchall()
            else:
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                return last_id if last_id else row_count
        except Exception:
            if commit:
                conn.rollback()
            raise
        finally:
            cursor.close()

    else:
        # SQLite adapter: translate %s to ?
        sqlite_query = query.replace("%s", "?")
        sqlite_query = re.sub(r"\s+FOR\s+UPDATE", "", sqlite_query, flags=re.IGNORECASE)

        cursor = conn.cursor()
        try:
            cursor.execute(sqlite_query, params)
            if commit:
                conn.commit()

            if fetch == "one":
                row = cursor.fetchone()
                return dict(row) if row else None
            elif fetch == "all":
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            else:
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                return last_id if last_id else row_count
        except Exception:
            if commit:
                conn.rollback()
            raise
        finally:
            cursor.close()


def execute_stored_procedure(proc_name: str, args: tuple = ()) -> List[Dict[str, Any]]:
    """Calls a stored procedure or executes the equivalent query."""
    conn = get_db()
    db_type = getattr(g, "db_type", "mysql") if has_app_context() else ("mysql" if hasattr(conn, "pool_name") else "sqlite")

    if db_type == "mysql" and hasattr(conn, "cursor"):
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc(proc_name, args)
            results = []
            for result in cursor.stored_results():
                results.extend(result.fetchall())
            return results
        finally:
            cursor.close()
    else:
        # Fallback implementation of stored procedures
        if proc_name == "sp_get_patient_appointment_history":
            patient_id = args[0]
            query = """
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
            WHERE a.patient_id = ?
            ORDER BY a.appointment_date DESC, a.start_time DESC
            """
            return execute_query(query, (patient_id,), fetch="all")

        elif proc_name == "sp_get_doctor_schedule_stats":
            doctor_id = args[0]
            query = """
            SELECT 
                COUNT(CASE WHEN appointment_date = CURDATE() AND status IN ('Scheduled', 'Confirmed') THEN 1 END) AS today_appointments,
                COUNT(CASE WHEN appointment_date > CURDATE() AND status IN ('Scheduled', 'Confirmed') THEN 1 END) AS upcoming_appointments,
                COUNT(CASE WHEN status = 'Completed' THEN 1 END) AS completed_consultations,
                COUNT(DISTINCT patient_id) AS total_unique_patients
            FROM appointments
            WHERE doctor_id = ?
            """
            return execute_query(query, (doctor_id,), fetch="all")
        return []
