# User Repository
# Handles data access for user accounts, profiles, and role management.
# Contains functions for retrieving user details, updating passwords, and managing line assignments.

from app.utils import get_cursor

def get_user_by_username(username):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE username = %s;", (username,))
        return cursor.fetchone()

def get_user_by_email(email):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE email = %s;", (email,))
        return cursor.fetchone()

def get_user_by_id(user_id):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE user_id = %s;", (user_id,))
        return cursor.fetchone()

def get_active_admin_count():
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS admin_count FROM Users WHERE role = 'Admin' AND account_status = 'Active'")
        row = cur.fetchone()
        return row['admin_count'] if row else 0


def get_admin_count():
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS admin_count FROM Users WHERE role = 'Admin'")
        row = cur.fetchone()
        return row['admin_count'] if row else 0


def get_user_assigned_line_count(user_id):
    """Return how many trap lines are assigned to the given user."""
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS assigned_line_count FROM User_Line WHERE user_id = %s;", (user_id,))
        row = cur.fetchone()
        return row["assigned_line_count"] if row else 0
    
def update_user_account_profile(user_id, profile_data):
    """Update editable profile fields for the current logged-in user."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Users
            SET 
                email = %(email)s,
                first_name = %(first_name)s,
                last_name = %(last_name)s,
                phone_number = %(phone_number)s,
                emergency_contact_name = %(emergency_contact_name)s,
                emergency_contact_phone_number = %(emergency_contact_phone_number)s,
                emergency_contact_relationship = %(emergency_contact_relationship)s
            WHERE user_id = %(user_id)s;
            """,
            {
                "user_id": user_id,
                "email": profile_data["email"],
                "first_name": profile_data["first_name"],
                "last_name": profile_data["last_name"],
                "phone_number": profile_data["phone_number"],
                "emergency_contact_name": profile_data["emergency_contact_name"],
                "emergency_contact_phone_number": profile_data["emergency_contact_phone_number"],
                "emergency_contact_relationship": profile_data["emergency_contact_relationship"],
            }
        )
    return True

def create_user(user_data):
    query = """
    INSERT INTO Users (
        username, email, password_hash, first_name, last_name, 
        phone_number, emergency_contact_name, emergency_contact_phone_number, 
        emergency_contact_relationship, account_status
    ) VALUES (
        %(username)s, %(email)s, %(password_hash)s, %(first_name)s, %(last_name)s,
        %(phone_number)s, %(emergency_contact_name)s, %(emergency_contact_phone_number)s,
        %(emergency_contact_relationship)s, %(account_status)s
    ) RETURNING user_id;
    """
    with get_cursor() as cursor:
        cursor.execute(query, user_data)
        result = cursor.fetchone()
        return result['user_id'] if result else None


def get_user_admin_options():
    """Return valid role and account status options from Params."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT param_type, param_value
            FROM Params
            WHERE param_type IN ('user_role', 'account_status')
            ORDER BY param_type, param_value;
            """
        )
        rows = cursor.fetchall()

    options = {
        "roles": [],
        "account_statuses": []
    }

    for row in rows:
        if row["param_type"] == "user_role":
            options["roles"].append(row["param_value"])
        elif row["param_type"] == "account_status":
            options["account_statuses"].append(row["param_value"])

    return options


def update_user_role_and_status(user_id,  account_status):
    """Update a user's role and account status."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Users
            SET account_status = %s
            WHERE user_id = %s;
            """,
            ( account_status, user_id)
        )


def update_user_password(user_id, password_hash):
    """Update the password hash for a user account."""
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET password_hash = %s WHERE user_id = %s;",
            (password_hash, user_id)
        )

def get_users_with_assigned_lines_paginated(page=1, page_size=12, sort_by="username", sort_dir="asc", role_filter="", status_filter="", search_term=""):
    from flask import session
    group_id = session.get('group_id')
    sort_columns = {
        "username": "LOWER(u.username)",
        "email": "LOWER(u.email)",
        "role": "LOWER(gm.role)",
        "account_status": "LOWER(u.account_status)",
    }
    sort_expression = sort_columns.get(sort_by, sort_columns["username"])
    sort_direction = "DESC" if sort_dir == "desc" else "ASC"
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size

    where_clauses = ["1=1"]
    query_params = []
    if group_id:
        where_clauses.append("gm.group_id = %s")
        query_params.append(group_id)
    if role_filter:
        where_clauses.append("gm.role = %s")
        query_params.append(role_filter)
    if status_filter:
        where_clauses.append("u.account_status = %s")
        query_params.append(status_filter)
    if search_term:
        search_value = f"%{search_term}%"
        where_clauses.append("(CONCAT_WS(' ', u.first_name, u.last_name) ILIKE %s OR u.email ILIKE %s)")
        query_params.extend([search_value, search_value])

    where_sql = " WHERE " + " AND ".join(where_clauses)
    query = f"""
        WITH paged_users AS (
            SELECT u.user_id, u.username, u.first_name, u.last_name, u.email, u.phone_number,
                   gm.role, u.account_status, COUNT(*) OVER() AS total_count
            FROM Users u
            JOIN Group_Members gm ON gm.user_id = u.user_id
            {where_sql}
            ORDER BY {sort_expression} {sort_direction}
            LIMIT %s OFFSET %s
        )
        SELECT pu.*, l.line_id, l.name AS line_name
        FROM paged_users pu
        LEFT JOIN User_Line ul ON ul.user_id = pu.user_id
        LEFT JOIN Line l ON l.line_id = ul.line_id
        ORDER BY {sort_expression.replace('u.', 'pu.')} {sort_direction}, l.name;
    """
    with get_cursor() as cursor:
        cursor.execute(query, query_params + [page_size, offset])
        rows = cursor.fetchall()

    if not rows:
        return [], 0
    total_count = rows[0]["total_count"] or 0
    users_by_id = {}
    for row in rows:
        user_id = row["user_id"]
        if user_id not in users_by_id:
            full_name = f"{row['first_name']} {row['last_name'] or ''}".strip()
            users_by_id[user_id] = {
                "user_id": user_id, "full_name": full_name, "username": row["username"],
                "email": row["email"], "phone_number": row["phone_number"], "role": row["role"],
                "account_status": row["account_status"], "lines": []
            }
        if row["line_id"] is not None:
            users_by_id[user_id]["lines"].append({"line_id": row["line_id"], "line_name": row["line_name"]})
    return list(users_by_id.values()), total_count

def get_user_profile(user_id):
    """Return profile details for a single user, including assigned lines and activity counts."""
    user_query = """
        SELECT u.user_id, u.username, u.first_name, u.last_name, u.email, u.phone_number,
               gm.role AS role, u.account_status, u.emergency_contact_name,
               u.emergency_contact_phone_number, u.emergency_contact_relationship
        FROM Users u
        JOIN Group_Members gm ON gm.user_id = u.user_id
        WHERE u.user_id = %s;
    """
    lines_query = """
        SELECT l.line_id, l.name AS line_name, l.type AS line_type, l.line_status
        FROM User_Line ul
        JOIN Line l ON l.line_id = ul.line_id
        WHERE ul.user_id = %s
        ORDER BY l.name;
    """
    observation_count_query = "SELECT COUNT(*) AS count FROM Observation WHERE operator_id = %s;"
    catch_count_query = "SELECT COUNT(*) AS count FROM Trap_Catches WHERE recorded_by = %s;"
    latest_observation_query = "SELECT MAX(date_recorded) AS latest FROM Observation WHERE operator_id = %s;"
    latest_catch_query = "SELECT MAX(date) AS latest FROM Trap_Catches WHERE recorded_by = %s;"

    with get_cursor() as cursor:
        cursor.execute(user_query, (user_id,))
        user_row = cursor.fetchone()
        if user_row is None:
            return None

        cursor.execute(lines_query, (user_id,))
        line_rows = cursor.fetchall()
        cursor.execute(observation_count_query, (user_id,))
        observation_count = cursor.fetchone()["count"]
        cursor.execute(catch_count_query, (user_id,))
        catch_count = cursor.fetchone()["count"]
        cursor.execute(latest_observation_query, (user_id,))
        latest_obs = cursor.fetchone()["latest"]
        cursor.execute(latest_catch_query, (user_id,))
        latest_catch = cursor.fetchone()["latest"]

    last_activity_date = None
    if latest_obs and latest_catch:
        last_activity_date = max(latest_obs, latest_catch)
    elif latest_obs:
        last_activity_date = latest_obs
    elif latest_catch:
        last_activity_date = latest_catch

    full_name = f"{user_row['first_name']} {user_row['last_name'] or ''}".strip()
    user_profile = {
        "user_id": user_row["user_id"], "full_name": full_name, "username": user_row["username"],
        "email": user_row["email"], "phone_number": user_row["phone_number"], "role": user_row["role"],
        "account_status": user_row["account_status"], "emergency_contact_name": user_row["emergency_contact_name"],
        "emergency_contact_phone_number": user_row["emergency_contact_phone_number"],
        "emergency_contact_relationship": user_row["emergency_contact_relationship"],
        "observation_count": observation_count, "catch_count": catch_count,
        "last_activity_date": last_activity_date, "lines": []
    }
    for line in line_rows:
        user_profile["lines"].append({
            "line_id": line["line_id"], "line_name": line["line_name"],
            "line_type": line["line_type"], "line_status": line["line_status"]
        })
    return user_profile

def is_accessible_group_member(user_id, group_id):
    """Check if the user is an active member of the specified group."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT membership_status
            FROM Group_Members
            WHERE user_id = %s AND group_id = %s;
            """,
            (user_id, group_id)
        )
        row = cursor.fetchone()
        return row and row["membership_status"] == "Active"
