# Trap Repository
# Manages database operations for individual traps, including CRUD operations,
# trap type retrieval, and line-based trap deactivation.

from app.utils import get_cursor

def get_trap_by_ids(trap_id, group_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT t.code
            FROM Traps t
            JOIN Line l ON l.line_id = t.line_id
            WHERE t.trap_id = %s AND l.group_id = %s;
            """,
            (trap_id, group_id),
        )
        trap_row = cursor.fetchone()
    return trap_row

def update_trap_map(marker_id, code, line_id, trap_type_id, latitude, longitude, trap_status):
     with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Traps
            SET code = %s,
                line_id = %s,
                trap_type_id = %s,
                latitude = %s,
                longitude = %s,
                trap_status = %s
            WHERE trap_id = %s;
            """,
            (code, line_id, trap_type_id, latitude, longitude, trap_status, marker_id),
        )
def get_traps_by_line(line_id):
    """Fetch all traps for a specific line, including type name."""
    query = """
        SELECT
            trap_id,
            code,
            trap_type_id,
            latitude,
            longitude,
            trap_status,
            tt.name AS trap_type
        FROM Traps
        JOIN Trap_Types tt ON tt.id = trap_type_id
        WHERE line_id = %s
        ORDER BY code;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id,))
        return cursor.fetchall()

def get_trap_types():
    """Fetch all trap types."""
    query = "SELECT id, name FROM Trap_Types ORDER BY name;"
    with get_cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()

def trap_code_exists_exact(code):
    """Return True when a trap code already exists (case-insensitive exact match)."""
    query = "SELECT 1 FROM Traps WHERE lower(trim(code)) = lower(trim(%s)) LIMIT 1;"
    with get_cursor() as cursor:
        cursor.execute(query, (code,))
        return cursor.fetchone() is not None

def add_trap_to_line(line_id, code, trap_type_id, latitude, longitude):
    query = """
        INSERT INTO Traps (code, trap_type_id, line_id, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING trap_id;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (code, trap_type_id, line_id, latitude, longitude))
        row = cursor.fetchone()
        return row["trap_id"] if row else None

def update_trap(trap_id, trap_type_id, latitude, longitude, trap_status):
    query = """
        UPDATE Traps
        SET trap_type_id = %s,
            latitude = %s,
            longitude = %s,
            trap_status = %s
        WHERE trap_id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (trap_type_id, latitude, longitude, trap_status, trap_id))
        return cursor.rowcount > 0

def retire_trap(trap_id):
    query = "UPDATE Traps SET trap_status = 'Inactive' WHERE trap_id = %s;"
    with get_cursor() as cursor:
        cursor.execute(query, (trap_id,))
        return cursor.rowcount > 0

def deactivate_traps_by_line(line_id):
    query = """
        UPDATE Traps
        SET trap_status = 'Inactive'
        WHERE line_id = %s AND LOWER(trap_status) <> 'inactive';
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id,))
        return cursor.rowcount > 0

def get_trap_status_by_trap_id(trap_id):
    query = """
        SELECT l.line_status
        FROM Line l
        JOIN Traps t ON t.line_id = l.line_id
        WHERE t.trap_id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (trap_id,))
        return cursor.fetchone()

def get_trap_by_id(trap_id):
    query = """
        SELECT t.trap_id, t.code, t.latitude, t.longitude, t.trap_status,
               tt.name AS trap_type, l.line_id, l.name AS line_name
        FROM Traps t
        JOIN Trap_Types tt ON tt.id = t.trap_type_id
        JOIN Line l ON l.line_id = t.line_id
        WHERE t.trap_id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (trap_id,))
        return cursor.fetchone()
