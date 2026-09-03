from flask_bcrypt import Bcrypt
from flask import session, redirect, url_for, flash, request
from functools import wraps
from contextlib import contextmanager
import re
from app import flask_app as app
from app.db import db
flask_bcrypt = Bcrypt(app)

def generate_password_hash(password):
    return flask_bcrypt.generate_password_hash(password).decode('utf-8')

def check_password_hash(password_hash, password):
    return flask_bcrypt.check_password_hash(password_hash, password)

def check_password_complexity(password, personal_info=None):
    # Enforce a strict policy and optionally reject passwords containing personal identifiers.
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_number = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    if not (has_upper and has_lower and has_number and has_special):
        return False

    if not personal_info:
        return True

    normalized_password = re.sub(r"[^a-z0-9]", "", password.lower())
    for value in personal_info:
        if not value:
            continue
        normalized_value = re.sub(r"[^a-z0-9]", "", str(value).lower())
        if len(normalized_value) >= 3 and normalized_value in normalized_password:
            return False

    return True


def is_valid_email_format(email):
    # Check if the email contains @ and . and no other special characters
    if not email:
        return False
    # Only alphanumeric, @ and . are allowed
    if not re.fullmatch(r"[a-zA-Z0-9@.]+", email):
        return False
    # Must contain at least one @ and at least one .
    return "@" in email and "." in email



def is_valid_nz_phone_number(phone_number):
    """Validate New Zealand phone numbers in either 0X... or +64X... format."""
    if not phone_number:
        return False

    normalized_number = re.sub(r"[\s\-()]", "", phone_number)
    return re.fullmatch(r"(?:\+64|0)[2-9]\d{7,9}", normalized_number) is not None


def normalize_user_role(role):
    """Normalize role strings used in session and authorization checks."""
    if not role:
        return role
    if role.strip().lower() == 'group coordinator':
        return 'Coordinator'
    return role


def is_within_new_zealand(latitude, longitude):
    """Return True if coordinates fall within a practical NZ bounding area."""
    if latitude is None or longitude is None:
        return False

    # Mainland NZ and nearby islands use eastern longitudes (about 166E to 179E).
    mainland_like_bounds = -48.5 <= latitude <= -33.5 and 166.0 <= longitude <= 179.5

    # Chatham Islands are represented with western longitudes around -176.
    chatham_bounds = -45.0 <= latitude <= -43.0 and -177.0 <= longitude <= -175.0

    return mainland_like_bounds or chatham_bounds

def check_role_access(user_role, required_role):
    return user_role in required_role

def isloggedin():
    return 'user_id' in session

def get_dashboard_link_for_role():
    if not isloggedin():
        return url_for("home")
    role = session.get("role", "")
    if role == "Admin":
        return url_for("sa_dashboard")
    elif role == "Coordinator":
        return url_for("admin_dashboard")
    elif role == "Observer":
        return url_for("observer_dashboard")
    elif role == "Operator":
        return url_for("operator_dashboard")
    else:
        return url_for("home")
def login_required_without_group_checking(message="Please log in to access this page."):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash(message, "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def login_required(message="Please log in to access this page."):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash(message, "danger")
                return redirect(url_for("login"))
            elif "selectGroup" in session and request.endpoint not in {"choose_group", "change_group"}:
                flash("Please select a group to continue.", "warning")
                return redirect(url_for("choose_group"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("Unauthorized access.", "danger")
                return redirect(get_dashboard_link_for_role())
            return f(*args, **kwargs)
        return wrapper
    return decorator

@contextmanager
def get_cursor():
    cursor = db.get_cursor()
    try:
        yield cursor
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    finally:
        cursor.close()

@contextmanager
def get_cursor_with_transaction():
    cursor = db.get_cursor()
    try:
        yield cursor
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    finally:
        cursor.close()

