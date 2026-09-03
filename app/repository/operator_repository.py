# Operator Repository
# Manages database operations related to operator-line assignments and operator-specific data.
# Handles assigning operators to lines, removing assignments, and fetching lines for specific operators.

from app.utils import get_cursor
from app.repository import user_repository, notification_repository

#************************************************************************************************************************
# Get lines assigned to an operator, including line status and trap count, filtered by group    
# This is used in the operator dashboard and My Lines page to show relevant lines to the operator.
#************************************************************************************************************************
def get_operator_assigned_lines(operator_id, group_id=None):
    where_clauses = ["ul.user_id = %s", "l.line_status = 'Active'"]
    params = [operator_id]
    if group_id:
        where_clauses.append("gm.group_id = %s")
        params.append(group_id)
    
    query = f"""
        SELECT l.line_id, l.name, l.type AS line_type, l.line_status, 
               CASE 
                   WHEN l.type = 'Trap' THEN COUNT(DISTINCT t.trap_id)
                   ELSE COUNT(DISTINCT bs.station_id)
               END AS asset_count
        FROM Line l
        JOIN Group_Members gm ON gm.group_id = l.group_id
        LEFT JOIN Traps t ON l.line_id = t.line_id
        LEFT JOIN Bait_Stations bs ON l.line_id = bs.line_id
        JOIN User_Line ul ON l.line_id = ul.line_id
        WHERE {" AND ".join(where_clauses)}
        GROUP BY l.line_id, l.name, l.type, l.line_status
        ORDER BY l.name
    """
    with get_cursor() as cur:
        cur.execute(query, tuple(params))
        return cur.fetchall()

def get_unassigned_operators_for_line(line_id, group_id=None):
    """Return operators not currently assigned to the specified line. 
    If group_id is provided, only return operators from that group."""
    
    where_clause = "WHERE gm.role = 'Operator' AND u.user_id NOT IN (SELECT ul.user_id FROM User_Line ul WHERE ul.line_id = %s)"
    params = [line_id]
    
    if group_id:
        where_clause += " AND gm.group_id = %s"
        params.append(group_id)
    
    query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.account_status
        FROM Users u
        JOIN Group_Members gm ON gm.user_id = u.user_id
        {where_clause}
        ORDER BY u.first_name, u.last_name;
    """
    with get_cursor() as cursor:
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
    
    operators = []
    for row in rows:
        full_name = f"{row['first_name']} {row['last_name'] or ''}".strip()
        operators.append({
            "user_id": row["user_id"],
            "full_name": full_name,
            "account_status": row["account_status"],
        })
    return operators

def assign_operator_to_line(line_id, operator_id):
    """Assign a single operator to a line. Returns True if inserted."""
    validate_query = """
        SELECT 1 FROM Users u JOIN Group_Members gm ON gm.user_id = u.user_id
        WHERE u.user_id = %s AND gm.role = 'Operator';
    """
    insert_query = """
        INSERT INTO User_Line (user_id, line_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, line_id) DO NOTHING;
    """
    with get_cursor() as cursor:
        cursor.execute(validate_query, (operator_id,))
        if cursor.fetchone() is None:
            return False
        cursor.execute(insert_query, (operator_id, line_id))
        return cursor.rowcount > 0

def remove_operator_from_line(line_id, operator_id):
    """Remove a single operator assignment from a line. Returns True if removed."""
    query = "DELETE FROM User_Line WHERE line_id = %s AND user_id = %s;"
    with get_cursor() as cursor:
        cursor.execute(query, (line_id, operator_id))
        return cursor.rowcount > 0

def replace_line_operator_assignments(line_id, operator_ids):
    """Replace all operator assignments for the given line."""
    operator_ids = [int(op_id) for op_id in operator_ids]
    validate_query = """
        SELECT u.user_id FROM Users u JOIN Group_Members gm ON gm.user_id = u.user_id
        WHERE gm.role = 'Operator' AND u.user_id = ANY(%s)
    """
    delete_query = "DELETE FROM User_Line WHERE line_id = %s;"
    insert_query = "INSERT INTO User_Line (user_id, line_id) VALUES (%s, %s) ON CONFLICT (user_id, line_id) DO NOTHING;"
    
    with get_cursor() as cursor:
        valid_operator_ids = []
        if operator_ids:
            cursor.execute(validate_query, (operator_ids,))
            valid_operator_ids = [row["user_id"] for row in cursor.fetchall()]
        cursor.execute(delete_query, (line_id,))
        for operator_id in sorted(set(valid_operator_ids)):
            cursor.execute(insert_query, (operator_id, line_id))

def assign_operator_with_mode(line_id, new_operator_id, action_mode, existing_operators, replace_specific_operator_id=None, replace_all_operators=False):
    """Assign operator with mode ('add' or 'replace'). Returns added/removed IDs."""
    added_operator_ids = set()
    removed_operator_ids = set()
    old_operator_ids = {op["user_id"] for op in existing_operators}
    
    if action_mode == "replace" and old_operator_ids:
        if replace_specific_operator_id:
            if replace_specific_operator_id in old_operator_ids:
                remove_operator_from_line(line_id, replace_specific_operator_id)
                removed_operator_ids.add(replace_specific_operator_id)
        elif replace_all_operators:
            for existing_op_id in old_operator_ids:
                remove_operator_from_line(line_id, existing_op_id)
            removed_operator_ids = old_operator_ids
            
    if assign_operator_to_line(line_id, new_operator_id):
        added_operator_ids.add(new_operator_id)
        return {"assigned": True, "added_operator_ids": added_operator_ids, "removed_operator_ids": removed_operator_ids}
    return {"assigned": False, "added_operator_ids": added_operator_ids, "removed_operator_ids": removed_operator_ids}

def handle_operator_assignment_with_notifications(line_id, line_name, new_operator_id, action_mode, existing_operators, admin_user_id, replace_specific_operator_id=None, replace_all_operators=False):
    """Handle assignment and trigger notifications."""
    result = assign_operator_with_mode(line_id, new_operator_id, action_mode, existing_operators, replace_specific_operator_id, replace_all_operators)
    
    if not result["assigned"]:
        return {"success": False, "message": "Operator could not be assigned."}
    
    if result["removed_operator_ids"] or result["added_operator_ids"]:
        admin_user = user_repository.get_user_by_id(admin_user_id)
        admin_name = f"{admin_user['first_name']} {admin_user['last_name'] or ''}".strip() if admin_user else "Administrator"
        notification_repository.create_line_assignment_notifications(line_id, line_name, admin_name, result["added_operator_ids"], result["removed_operator_ids"])
        
    message = "Operator assigned successfully."
    if result["removed_operator_ids"]:
        message = "Operator replaced successfully." if len(result["removed_operator_ids"]) == 1 else f"Successfully replaced {len(result['removed_operator_ids'])} operator(s)."
        
    return {"success": True, "message": message, "replaced": bool(result["removed_operator_ids"])}
