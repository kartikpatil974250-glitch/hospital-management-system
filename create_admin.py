"""CLI Utility to securely provision Administrator accounts with hashed credentials."""

import os
import sys
from dotenv import load_dotenv
from database.connection import execute_query
from extensions import hash_password

load_dotenv()

def create_admin(name="System Administrator", email="admin@pulsecare.com", password="Admin@123", role="Super Admin"):
    print(f"Provisioning administrator: {name} <{email}>")
    pwhash = hash_password(password)
    
    # Check if exists
    existing = execute_query("SELECT admin_id FROM admins WHERE email = %s", (email,), fetch="one")
    if existing:
        execute_query(
            "UPDATE admins SET full_name = %s, password_hash = %s, role = %s WHERE email = %s",
            (name, pwhash, role, email),
            commit=True
        )
        print("Existing administrator account credentials updated.")
    else:
        execute_query(
            "INSERT INTO admins (full_name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, pwhash, role),
            commit=True
        )
        print("New administrator account created successfully.")

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        create_admin(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        create_admin()
