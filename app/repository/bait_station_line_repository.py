# Bait Station Line Repository
# Handles all database operations related to Bait Station Lines.
# These lines are stored in the 'Line' table with type='Bait'.

from app.db import db
from app.utils import get_cursor


def get_bait_station_lines_by_group(group_id):
    """
    Fetch all bait station lines for a specific group.
    """
    query = """
        SELECT line_id, name, line_status
        FROM Line
        WHERE group_id = %s AND type = 'Bait'
        ORDER BY name;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (group_id,))
        return cursor.fetchall()

def create_bait_station_line(name, group_id, status='Active'):
    """
    Create a new bait station line.
    """
    query = """
        INSERT INTO Line (name, group_id, type, line_status)
        VALUES (%s, %s, 'Bait', %s)
        RETURNING line_id;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (name, group_id, status))
        result = cursor.fetchone()
        return result['line_id'] if result else None

def update_bait_station_line(line_id, name, status):
    """
    Update bait station line details.
    """
    query = """
        UPDATE Line
        SET name = %s, line_status = %s
        WHERE line_id = %s AND type = 'Bait';
    """
    with get_cursor() as cursor:
        cursor.execute(query, (name, status, line_id))
        return cursor.rowcount > 0

def delete_bait_station_line(line_id):
    """
    Hard delete a bait station line.
    The database schema has ON DELETE CASCADE for Traps and Bait_Stations.
    """
    query = "DELETE FROM Line WHERE line_id = %s AND type = 'Bait';"
    with get_cursor() as cursor:
        cursor.execute(query, (line_id,))
        return cursor.rowcount > 0

def get_bait_station_line_by_id(line_id):
    """
    Fetch a single bait station line by ID.
    """
    query = """
        SELECT line_id, name, group_id, line_status
        FROM Line
        WHERE line_id = %s AND type = 'Bait';
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id,))
        return cursor.fetchone()
