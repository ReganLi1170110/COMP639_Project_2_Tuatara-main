# Line Repository
# Manages database operations for monitoring lines (Trap Lines and Bait Station Lines).
# Includes functionality for line details, assets, operator assignments, and line status management.

from flask import session
from app.repository import bait_station_repository, trap_repository
from app.utils import get_cursor

def get_line_by_id(line_id, group_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT line_id, name, type
            FROM Line
            WHERE line_id = %s AND group_id = %s;
            """,
            (line_id, group_id),
        )
        line_row = cursor.fetchone()
    return line_row

def get_lines_with_assigned_users():
    group_id = session.get('group_id')
    where_clauses = []
    query_params = []
    if group_id:
        where_clauses.append("l.group_id = %s")
        query_params.append(group_id)

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    query = f"""
        SELECT
            l.line_id,
            l.name AS line_name,
            l.type AS line_type,
            l.line_status,
            u.user_id,
            u.first_name,
            u.last_name,
            u.account_status,
            gm.role AS role
        FROM Line l
        LEFT JOIN User_Line ul ON ul.line_id = l.line_id
        LEFT JOIN Users u ON u.user_id = ul.user_id
        LEFT JOIN Group_Members gm ON gm.user_id = u.user_id AND gm.group_id = l.group_id
        {where_sql}
        ORDER BY l.line_id, u.first_name, u.last_name;
    """

    with get_cursor() as cursor:
        cursor.execute(query, tuple(query_params))
        rows = cursor.fetchall()

    lines_by_id = {}
    for row in rows:
        line_id = row["line_id"]
        if line_id not in lines_by_id:
            lines_by_id[line_id] = {
                "line_id": line_id,
                "line_name": row["line_name"],
                "line_type": row["line_type"],
                "line_status": row["line_status"],
                "users": []
            }

        if row["user_id"] is not None:
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            lines_by_id[line_id]["users"].append({
                "user_id": row["user_id"],
                "full_name": full_name,
                "role": row["role"],
                "account_status": row["account_status"]
            })

    return list(lines_by_id.values())

def get_lines_with_assigned_users_paginated(page=1, page_size=12):
    group_id = session.get('group_id')
    where_clauses = []
    query_params = []
    if group_id:
        where_clauses = ["l.group_id = %s"]
        query_params = [group_id]
        
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    query = f"""
        WITH paged_lines AS (
            SELECT
                l.line_id,
                l.name AS line_name,
                l.type AS line_type,
                l.line_status,
                l.group_id,
                COUNT(*) OVER() AS total_count
            FROM Line l
            {where_sql}
            ORDER BY l.line_id
            LIMIT %s OFFSET %s
        )
        SELECT
            pl.line_id,
            pl.line_name,
            pl.line_type,
            pl.line_status,
            pl.total_count,
            u.user_id,
            u.first_name,
            u.last_name,
            gm.role AS role,
            u.account_status
        FROM paged_lines pl
        LEFT JOIN User_Line ul ON ul.line_id = pl.line_id
        LEFT JOIN Users u ON u.user_id = ul.user_id
        LEFT JOIN Group_Members gm ON gm.user_id = u.user_id AND gm.group_id = pl.group_id
        ORDER BY pl.line_id, u.first_name, u.last_name;
    """

    with get_cursor() as cursor:
        cursor.execute(query, tuple(query_params) + (page_size, offset))
        rows = cursor.fetchall()

    if not rows:
        return [], 0

    total_count = rows[0]["total_count"] or 0
    lines_by_id = {}
    for row in rows:
        line_id = row["line_id"]
        if line_id not in lines_by_id:
            lines_by_id[line_id] = {
                "line_id": line_id,
                "line_name": row["line_name"],
                "line_type": row["line_type"],
                "line_status": row["line_status"],
                "users": []
            }

        if row["user_id"] is not None:
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            lines_by_id[line_id]["users"].append({
                "user_id": row["user_id"],
                "full_name": full_name,
                "role": row["role"],
                "account_status": row["account_status"]
            })

    return list(lines_by_id.values()), total_count

def get_line_detail(line_id):
    """Return one line with related assets and assigned operators."""
    line_query = """
        SELECT line_id, group_id, name, type, line_status
        FROM Line
        WHERE line_id = %s;
    """
    group_id = session.get('group_id')
    where_clauses = ""
    query_params = [line_id]
    if group_id:
        where_clauses = " AND gm.group_id = %s"
        query_params.append(group_id)

    operators_query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.email, u.phone_number, u.account_status
        FROM User_Line ul
        JOIN Users u ON u.user_id = ul.user_id
        JOIN Group_Members gm ON gm.user_id = u.user_id
        WHERE ul.line_id = %s AND gm.role = 'Operator' {where_clauses}
        ORDER BY u.first_name, u.last_name;
    """

    observations_query = """
        SELECT o.id AS observation_id, o.date_recorded, o.notes, u.first_name, u.last_name
        FROM Observation o
        LEFT JOIN Users u ON u.user_id = o.operator_id
        WHERE o.line_id = %s
        ORDER BY o.date_recorded DESC;
    """

    with get_cursor() as cursor:
        cursor.execute(line_query, (line_id,))
        line_row = cursor.fetchone()

        if line_row is None:
            return None

        cursor.execute(operators_query, tuple(query_params))
        operator_rows = cursor.fetchall()

        if line_row["type"] == "Trap":
            trap_rows = trap_repository.get_traps_by_line(line_id)
            bait_station_rows = []
        else:
            bait_station_rows = bait_station_repository.get_stations_by_line(line_id)
            trap_rows = []

        cursor.execute(observations_query, (line_id,))
        observation_rows = cursor.fetchall()

    line_detail = {
        "line_id": line_row["line_id"],
        "group_id": line_row["group_id"],
        "line_name": line_row["name"],
        "line_type": line_row["type"],
        "line_status": line_row["line_status"],
        "operators": [],
        "traps": trap_rows,
        "bait_stations": bait_station_rows,
        "observations": []
    }

    for operator in operator_rows:
        full_name = f"{operator['first_name']} {operator['last_name'] or ''}".strip()
        line_detail["operators"].append({
            "user_id": operator["user_id"],
            "full_name": full_name,
            "email": operator["email"],
            "phone_number": operator["phone_number"],
            "account_status": operator["account_status"]
        })

    for observation in observation_rows:
        operator_name = "Unknown"
        if observation["first_name"] is not None or observation["last_name"] is not None:
            operator_name = f"{observation['first_name'] or ''} {observation['last_name'] or ''}".strip()

        line_detail["observations"].append({
            "observation_id": observation["observation_id"],
            "date_recorded": observation["date_recorded"],
            "operator_name": operator_name,
            "notes": observation["notes"]
        })

    return line_detail

def create_line(name, line_type='Trap', line_status='Pending'):
    group_id = session.get('group_id')
    if not group_id:
        raise Exception("No group selected for new line.")

    query = """
        INSERT INTO Line (group_id, name, type, line_status)
        VALUES (%s, %s, %s, %s)
        RETURNING line_id;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (group_id, name, line_type, line_status))
        row = cursor.fetchone()
        return row["line_id"] if row else None

def update_line(line_id, name, line_type, line_status):
    query = """
        UPDATE Line
        SET name = %s, type = %s, line_status = %s
        WHERE line_id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (name, line_type, line_status, line_id))
        if line_status == 'Inactive':
            trap_repository.deactivate_traps_by_line(line_id)

def retire_line(line_id):
    line_query = "UPDATE Line SET line_status = 'Inactive' WHERE line_id = %s;"
    with get_cursor() as cursor:
        cursor.execute(line_query, (line_id,))
        trap_repository.deactivate_traps_by_line(line_id)

def get_line_management_options():
    line_status_query = "SELECT param_value FROM Params WHERE param_type = 'line_status' ORDER BY param_value;"
    operators_query = """
        SELECT u.user_id, u.first_name, u.last_name, u.account_status
        FROM Users u
        JOIN Group_Members gm ON gm.user_id = u.user_id
        WHERE gm.role = 'Operator'
        ORDER BY u.first_name, u.last_name;
    """
    with get_cursor() as cursor:
        cursor.execute(line_status_query)
        line_status_rows = cursor.fetchall()
        
        trap_types = trap_repository.get_trap_types()
        bait_station_types = bait_station_repository.get_bait_station_types()

        cursor.execute(operators_query)
        operator_rows = cursor.fetchall()

    return {
        "line_statuses": [row["param_value"] for row in line_status_rows] if line_status_rows else ["Pending", "Active", "Inactive"],
        "trap_types": [row["name"] for row in trap_types],
        # Ensure 'Other' appears exactly once and always at the end of the list
        "bait_station_types": (lambda names: (names[:-1] + [names[-1]]) if names and names[-1] == 'Other' else (lambda n: (n + ['Other'] if 'Other' not in n else [x for x in n if x != 'Other'] + ['Other']))(names))([row["name"] for row in bait_station_types]),
        "operators": [
            {
                "user_id": row["user_id"],
                "full_name": f"{row['first_name']} {row['last_name'] or ''}".strip(),
                "account_status": row["account_status"]
            }
            for row in operator_rows
        ]
    }

def get_lines_by_group_organized_by_type(group_id):
    """
    Get all lines for a specific group, organized by type (Trap vs Bait Station).
    Includes trap/bait station counts and assigned operators.
    
    AC1: Only lines for the specified group are shown.
    AC2: Lines are separated by type.
    AC3: Each line clearly shows its type.
    AC4: Each line displays name, type, status, asset count, and assigned operators.
    
    Returns:
        dict: {
            "trap_lines": [line1, line2, ...],
            "bait_station_lines": [line1, line2, ...],
            "total_lines": int
        }
        Each line object contains:
        {
            "line_id": int,
            "name": str,
            "type": str ("Trap" or "Bait Station"),
            "status": str,
            "asset_count": int (number of traps or bait stations),
            "operators": [{"user_id": int, "full_name": str}, ...]
        }
    """
    # First, get all lines with their asset counts
    lines_query = """
        SELECT
            l.line_id,
            l.name,
            l.type,
            l.line_status,
            CASE WHEN l.type = 'Trap' THEN
                COALESCE(COUNT(DISTINCT t.trap_id), 0)
            ELSE
                COALESCE(COUNT(DISTINCT bs.station_id), 0)
            END AS asset_count
        FROM Line l
        LEFT JOIN Traps t ON l.line_id = t.line_id
        LEFT JOIN Bait_Stations bs ON l.line_id = bs.line_id
        WHERE l.group_id = %s
        GROUP BY l.line_id, l.name, l.type, l.line_status
        ORDER BY l.type, l.name;
    """
    
    # Then, get all operators for each line
    operators_query = """
        SELECT
            ul.line_id,
            u.user_id,
            u.first_name,
            u.last_name
        FROM User_Line ul
        JOIN Users u ON ul.user_id = u.user_id
        JOIN Line l ON ul.line_id = l.line_id
        WHERE ul.line_id = %s AND l.group_id = %s
        ORDER BY u.first_name, u.last_name;
    """
    
    with get_cursor() as cursor:
        cursor.execute(lines_query, (group_id,))
        line_rows = cursor.fetchall()
    
    lines_by_id = {}
    for line_row in line_rows:
        line_id = line_row["line_id"]
        
        # Fetch operators for this line
        with get_cursor() as cursor: 
            cursor.execute(operators_query, (line_id, group_id))
            operator_rows = cursor.fetchall()
        
        operators = []
        for op_row in operator_rows:
            full_name = f"{op_row['first_name']} {op_row['last_name'] or ''}".strip()
            operators.append({
                "user_id": op_row["user_id"],
                "full_name": full_name
            })
        
        lines_by_id[line_id] = {
            "line_id": line_id,
            "name": line_row["name"],
            "type": line_row["type"],
            "status": line_row["line_status"],
            "asset_count": line_row["asset_count"],
            "operators": operators
        }
    
    # Organize by type
    trap_lines = []
    bait_station_lines = []
    
    for line in lines_by_id.values():
        if line["type"] == "Trap":
            trap_lines.append(line)
        else:
            bait_station_lines.append(line)
    
    return {
        "trap_lines": sorted(trap_lines, key=lambda x: x["name"]),
        "bait_station_lines": sorted(bait_station_lines, key=lambda x: x["name"]),
        "total_lines": len(lines_by_id)
    }
