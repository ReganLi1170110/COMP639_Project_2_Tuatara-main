# Observation Repository
# Handles database operations for line observations.
# Includes functionality for creating, updating, and retrieving operator field notes for monitoring lines.

from app.utils import get_cursor

def get_observations_by_line(line_id):
    query = """
        SELECT o.id AS observation_id, o.date_recorded, o.notes, u.first_name, u.last_name
        FROM Observation o
        LEFT JOIN Users u ON u.user_id = o.operator_id
        WHERE o.line_id = %s
        ORDER BY o.date_recorded DESC;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id,))
        return cursor.fetchall()

def create_observation(line_id, operator_id, date_recorded, notes):
    query = """
        INSERT INTO Observation (line_id, operator_id, date_recorded, notes)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id, operator_id, date_recorded, notes))
        row = cursor.fetchone()
        return row["id"] if row else None

def update_observation(observation_id, line_id, date_recorded, notes):
    query = """
        UPDATE Observation
        SET line_id = %s, date_recorded = %s, notes = %s
        WHERE id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id, date_recorded, notes, observation_id))
        return cursor.rowcount > 0

def get_observation_by_id(observation_id):
    query = """
        SELECT o.id AS observation_id, o.line_id, o.date_recorded, o.notes, 
               o.operator_id, u.first_name, u.last_name
        FROM Observation o
        LEFT JOIN Users u ON u.user_id = o.operator_id
        WHERE o.id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (observation_id,))
        return cursor.fetchone()
