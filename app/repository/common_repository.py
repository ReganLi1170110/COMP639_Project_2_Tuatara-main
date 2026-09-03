# Common Repository
# Provides shared data access functions for the entire application.
# Handles retrieval of dropdown options (species, statuses, bait types) and management of system parameters.

from app.utils import get_cursor


def get_all_active_groups():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT group_id, name, status, operational_area
            FROM Groups
            WHERE status = 'Active'
            ORDER BY name;
            """
        )
        group_rows = cursor.fetchall()
    return group_rows

def get_all_active_lines():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT l.line_id, l.name, l.type, g.group_id, g.name AS group_name
            FROM Line l
            JOIN Groups g ON g.group_id = l.group_id
            WHERE l.line_status = 'Active' AND g.status = 'Active'
            ORDER BY g.name, l.name;
            """
        )
        lines = cursor.fetchall()
    return lines


def get_all_active_traps():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT t.trap_id AS id, t.code, t.latitude, t.longitude, t.trap_status AS status,
                   tt.name AS trap_type, l.line_id, l.name AS line_name,
                   g.group_id, g.name AS group_name
            FROM Traps t
            JOIN Trap_Types tt ON tt.id = t.trap_type_id
            JOIN Line l ON l.line_id = t.line_id
            JOIN Groups g ON g.group_id = l.group_id
            WHERE l.line_status = 'Active' AND g.status = 'Active'
            ORDER BY g.name, t.code;
            """
        )
        trap_rows = cursor.fetchall()
    return trap_rows

def get_all_active_bait_stations():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT bs.station_id AS id, bs.code, bs.latitude, bs.longitude, bs.status,bs.other_type_details,
                   bst.name AS bait_station_type, l.line_id, l.name AS line_name,
                   g.group_id, g.name AS group_name
            FROM Bait_Stations bs
            JOIN Bait_Station_Types bst ON bst.id = bs.bait_station_type_id
            JOIN Line l ON l.line_id = bs.line_id
            JOIN Groups g ON g.group_id = l.group_id
            WHERE l.line_status = 'Active' AND g.status = 'Active'
            ORDER BY g.name, bs.code;
            """
        )
        bait_rows = cursor.fetchall()
    return bait_rows
#************************************************************************************************************************
# Get all active trap statuses, trap types, bait types, species, bait station types, and general params for dropdowns in the add catch record form
# These are used in the add catch record form to populate dropdown options
#************************************************************************************************************************
def get_trap_status():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM Trap_Status WHERE status = 'Active' ORDER BY name")
        return [{"id": row['id'], "name": row['name']} for row in cur.fetchall()]
    
def get_trap_types():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM Trap_Types WHERE status = 'Active' ORDER BY name")
        return [{"id": row['id'], "name": row['name']} for row in cur.fetchall()]
    
def get_bait_types():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM Bait_Types WHERE status = 'Active' ORDER BY name")
        return [{"id": row['id'], "name": row['name']} for row in cur.fetchall()]
    
def get_species():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM Species WHERE status = 'Active' ORDER BY name")
        return [{"id": row['id'], "name": row['name']} for row in cur.fetchall()]
    
def get_bait_stations_types():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM Bait_Station_Types WHERE status = 'Active' ORDER BY name")
        return [{"id": row['id'], "name": row['name']} for row in cur.fetchall()]


def get_params_by_type(param_type):
    with get_cursor() as cur:
        cur.execute("SELECT id, param_value FROM Params WHERE param_type = %s ORDER BY param_value", (param_type,))
        return [row['param_value'] for row in cur.fetchall()]
    
def get_params_by_type_with_id(param_type):
    with get_cursor() as cur:
        cur.execute("SELECT id, param_value FROM Params WHERE param_type = %s ORDER BY param_value", (param_type,))
        return [{"id": row['id'], "param_value": row['param_value']} for row in cur.fetchall()]

def get_manageable_param_types():
    """Return distinct manageable param types."""
    query = """
        SELECT DISTINCT param_type FROM Params
        WHERE param_type NOT IN ('user_role', 'account_status', 'line_status', 'sex', 'trap_status2','line_type','maturity','general_status','group_status','redemptions_status','update_status','knowledge_status','rebaited','donation_type')
        ORDER BY param_type;
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        return [r["param_type"] for r in cursor.fetchall()]

def get_manageable_param_types_with_counts():
    """Return distinct manageable param types with their value counts."""
    query = """
        SELECT param_type, COUNT(*) AS value_count FROM Params
        WHERE param_type NOT IN ('user_role', 'account_status', 'line_status', 'sex', 'trap_status2','line_type','maturity','general_status','group_status','redemptions_status','update_status','knowledge_status','rebaited','donation_type')
        GROUP BY param_type ORDER BY param_type;
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()

def get_params_by_type_paginated(param_type, page=1, page_size=10):
    page = max(1, int(page))
    offset = (page - 1) * page_size
    query = """
        SELECT param_id, param_value, COUNT(*) OVER() AS total_count
        FROM Params WHERE param_type = %s
        ORDER BY param_value LIMIT %s OFFSET %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (param_type, page_size, offset))
        rows = cursor.fetchall()
    if not rows: return [], 0
    return rows, rows[0]["total_count"]

def add_param(param_type, param_value):
    query = "INSERT INTO Params (param_type, param_value) VALUES (%s, %s);"
    with get_cursor() as cursor:
        cursor.execute(query, (param_type, param_value))


def delete_param(param_id):
    query = "DELETE FROM Params WHERE id = %s;"
    with get_cursor() as cursor:
        cursor.execute(query, (param_id,))
        return cursor.rowcount > 0

# --- Parameter Integrity Logic (Legacy/Shared) ---

PARAM_USAGE_QUERIES = {
    "line_type": [
        "SELECT 1 FROM Line WHERE type = (SELECT param_value FROM Params WHERE id = %s) LIMIT 1;",
    ],
    "trap_status": [
        "SELECT 1 FROM Trap_Catches WHERE trap_status_id = %s LIMIT 1;",
    ],
    "trap_status2": [
        "SELECT 1 FROM Traps WHERE trap_status = %s LIMIT 1;",
    ],
    "bait": [
        "SELECT 1 FROM Trap_Catches WHERE bait_type_id = %s LIMIT 1;",
    ],
    "species": [
        "SELECT 1 FROM Trap_Catches WHERE species_caught_id = %s LIMIT 1;"
    ],
}

def is_param_value_in_use(param_type, param_id):
    """Check if a parameter ID is referenced by existing monitoring records."""
    queries = PARAM_USAGE_QUERIES.get(param_type, [])
    if not queries:
        return False
    with get_cursor() as cursor:
        for query in queries:
            cursor.execute(query, (param_id,))
            if cursor.fetchone() is not None:
                return True
    return False


#************************************************************************************************************************
# Lookup Table Management Functions (for Super Admin parameter management)
# These handle CRUD operations on lookup tables: Trap_Status, Trap_Types, Bait_Types, Species, Bait_Station_Types
#************************************************************************************************************************

def get_lookup_table_all_records(table_name):
    """Fetch all records from a lookup table (both active and inactive)."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types']
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    query = f"SELECT id, name, status FROM {table_name} ORDER BY name;"
    with get_cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()

def get_lookup_table_active_records(table_name):
    """Fetch only active records from a lookup table."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types']
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    query = f"SELECT id, name, status FROM {table_name} WHERE status = 'Active' ORDER BY name;"
    with get_cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()

def add_lookup_table_record(table_name, name):
    """Add a new record to a lookup table."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types']
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    # Check if name already exists (case-insensitive)
    check_query = f"SELECT id FROM {table_name} WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s)) LIMIT 1;"
    with get_cursor() as cursor:
        cursor.execute(check_query, (name,))
        if cursor.fetchone() is not None:
            raise ValueError("Record with this name already exists (case-insensitive)")
    
    # Insert new record with Active status
    insert_query = f"INSERT INTO {table_name} (name, status) VALUES (%s, 'Active') RETURNING id;"
    with get_cursor() as cursor:
        cursor.execute(insert_query, (name,))
        row = cursor.fetchone()
        return row['id'] if row else None

def update_lookup_table_record(table_name, record_id, new_name):
    """Update a lookup table record name."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types']
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    # Check if new name already exists (case-insensitive, excluding current record)
    check_query = f"SELECT id FROM {table_name} WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s)) AND id != %s LIMIT 1;"
    with get_cursor() as cursor:
        cursor.execute(check_query, (new_name, record_id))
        if cursor.fetchone() is not None:
            raise ValueError("A record with this name already exists (case-insensitive)")
    
    # Update the record
    update_query = f"UPDATE {table_name} SET name = %s WHERE id = %s;"
    with get_cursor() as cursor:
        cursor.execute(update_query, (new_name, record_id))
        return cursor.rowcount > 0

def toggle_lookup_table_record_status(table_name, record_id, new_status):
    """Toggle a lookup table record status between Active and Inactive."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types']
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    valid_statuses = ['Active', 'Inactive']
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}")
    
    update_query = f"UPDATE {table_name} SET status = %s WHERE id = %s;"
    with get_cursor() as cursor:
        cursor.execute(update_query, (new_status, record_id))
        return cursor.rowcount > 0

def delete_lookup_table_record(table_name, record_id):
    """Permanently delete a lookup table record (admin use only)."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types']
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    delete_query = f"DELETE FROM {table_name} WHERE id = %s;"
    with get_cursor() as cursor:
        cursor.execute(delete_query, (record_id,))
        return cursor.rowcount > 0

def is_lookup_table_record_in_use(table_name, record_id):
    """Check if a lookup table record is referenced by existing data."""
    usage_queries = {
        'Trap_Status': [
            "SELECT 1 FROM Trap_Catches WHERE trap_status_id = %s LIMIT 1;",
        ],
        'Trap_Types': [
            "SELECT 1 FROM Traps WHERE trap_type_id = %s LIMIT 1;",
        ],
        'Bait_Types': [
            "SELECT 1 FROM Trap_Catches WHERE bait_type_id = %s LIMIT 1;",
        ],
        'Species': [
            "SELECT 1 FROM Trap_Catches WHERE species_caught_id = %s LIMIT 1;",
            "SELECT 1 FROM Bait_Station_Records WHERE target_species_id = %s LIMIT 1;"
        ],
        'Bait_Station_Types': [
            "SELECT 1 FROM Bait_Stations WHERE bait_station_type_id = %s LIMIT 1;",
        ],
    }
    
    queries = usage_queries.get(table_name, [])
    if not queries:
        return False
    
    with get_cursor() as cursor:
        for query in queries:
            cursor.execute(query, (record_id,))
            if cursor.fetchone() is not None:
                return True
    return False
