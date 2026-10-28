"""Database Initialization Script for PulseCare HMS.

Executes schema.sql, procedures.sql, and seed.sql against MySQL.
Falls back to initializing SQLite test database if MySQL daemon is not running.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def run_mysql_init():
    import mysql.connector
    
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", 3306))
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME", "hospital_management_db")

    print(f"Connecting to MySQL server at {host}:{port} as user '{user}'...")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            autocommit=True
        )
        cursor = conn.cursor()
        print(f"Ensuring database '{db_name}' exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE {db_name};")
        
        base_dir = os.path.dirname(__file__)
        schema_path = os.path.join(base_dir, "database", "schema.sql")
        proc_path = os.path.join(base_dir, "database", "procedures.sql")
        seed_path = os.path.join(base_dir, "database", "seed.sql")

        # 1. Execute schema.sql
        print(f"Executing {schema_path}...")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)

        # 2. Execute procedures.sql (split by DELIMITER $$)
        print(f"Executing {proc_path}...")
        with open(proc_path, "r", encoding="utf-8") as f:
            proc_sql = f.read()
        # Clean delimiters
        blocks = proc_sql.split("$$")
        for block in blocks:
            cleaned = block.replace("DELIMITER $$", "").replace("DELIMITER ;", "").strip()
            if cleaned:
                cursor.execute(cleaned)

        # 3. Execute seed.sql
        print(f"Executing {seed_path}...")
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_sql = f.read()
        for statement in seed_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)

        cursor.close()
        conn.close()
        print("MySQL database initialization completed successfully!")
        return True

    except Exception as e:
        print(f"MySQL initialization failed: {e}")
        return False


def run_sqlite_init():
    import re
    from database.connection import _get_or_create_sqlite_conn, execute_query
    print("Initializing SQLite fallback database store...")
    conn = _get_or_create_sqlite_conn()
    
    # Run seed data into fallback database if empty or missing doctors
    cnt = execute_query("SELECT COUNT(*) AS c FROM doctors", fetch="one")
    if not cnt or cnt.get("c", 0) < 12:
        base_dir = os.path.dirname(__file__)
        seed_path = os.path.join(base_dir, "database", "seed.sql")
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_content = f.read()
        
        # Remove comment-only lines
        lines = [line for line in seed_content.splitlines() if not line.strip().startswith("--")]
        clean_sql = "\n".join(lines)

        # Split statements by semicolon
        for stmt in clean_sql.split(";"):
            cleaned = stmt.strip()
            if not cleaned or cleaned.upper().startswith("USE"):
                continue
            # Strip MySQL ON DUPLICATE KEY UPDATE clause
            s_clean = re.sub(r'ON\s+DUPLICATE\s+KEY\s+UPDATE.*$', '', cleaned, flags=re.DOTALL | re.IGNORECASE).strip()
            # Replace INSERT INTO with INSERT OR REPLACE INTO for SQLite idempotency
            s_clean = re.sub(r'INSERT\s+INTO', 'INSERT OR REPLACE INTO', s_clean, count=1, flags=re.IGNORECASE)
            try:
                conn.execute(s_clean)
            except Exception as e:
                print(f"Notice on SQLite seed statement: {e}")
        conn.commit()
    print("Fallback database initialized with doctors, departments, and clinical demo data.")


if __name__ == "__main__":
    success = run_mysql_init()
    if not success:
        print("\nNotice: Live MySQL daemon was not reachable on localhost:3306.")
        print("Initializing SQLite fallback mode so application can be tested immediately...")
        run_sqlite_init()
