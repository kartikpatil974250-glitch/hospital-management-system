"""Authentication, Security, and Session Extensions for PulseCare HMS."""

import functools
import secrets
from typing import Any, Callable, Dict, List, Optional
from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    """Hashes a password using secure Werkzeug scrypt/pbkdf2."""
    return generate_password_hash(password)


def verify_password(pwhash: str, password: str) -> bool:
    """Verifies a cleartext password against a stored hash."""
    if not pwhash or not password:
        return False
    return check_password_hash(pwhash, password)


def generate_csrf_token() -> str:
    """Generates and stores a secure random CSRF token in the session."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(24)
    return session["_csrf_token"]


def validate_csrf():
    """Validates CSRF token on state-changing requests."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Allow bypassing in test mode if explicitly configured
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected_token = session.get("_csrf_token")
        if not expected_token or token != expected_token:
            abort(400, description="Invalid or missing CSRF token.")


def login_user(user_id: int, role: str, full_name: str, email: str):
    """Sets authenticated session state."""
    session.clear()
    session["user_id"] = user_id
    session["role"] = role  # 'patient', 'doctor', 'admin'
    session["full_name"] = full_name
    session["email"] = email
    session.permanent = True
    generate_csrf_token()


def logout_user():
    """Clears user session."""
    session.clear()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns current user details from session if authenticated."""
    if "user_id" in session and "role" in session:
        return {
            "id": session["user_id"],
            "role": session["role"],
            "name": session.get("full_name", ""),
            "email": session.get("email", ""),
        }
    return None


def login_required(view: Callable) -> Callable:
    """Decorator to enforce that the user is logged in."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_current_user() is None:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped_view


def role_required(*allowed_roles: str) -> Callable:
    """Decorator to enforce specific user role(s)."""
    def decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            user = get_current_user()
            if not user:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if user["role"] not in allowed_roles:
                flash("Access denied: You do not have permission for this section.", "danger")
                if user["role"] == "patient":
                    return redirect(url_for("patient.dashboard"))
                elif user["role"] == "doctor":
                    return redirect(url_for("doctor.dashboard"))
                elif user["role"] == "admin":
                    return redirect(url_for("admin.dashboard"))
                return redirect(url_for("index"))
            return view(**kwargs)
        return wrapped_view
    return decorator
