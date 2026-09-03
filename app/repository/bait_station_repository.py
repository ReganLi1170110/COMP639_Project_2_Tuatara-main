# Bait Station Repository
# Manages database operations for individual bait stations and bait station types.
# Includes functionality for adding stations, updating coordinates, and retrieving station details by line.

from app.utils import get_cursor

def update_bait_station_map( marker_id, code, line_id, bait_station_type_id, latitude, longitude, bait_status, other_type_details=None):
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Bait_Stations
            SET code = %s,
                line_id = %s,
                bait_station_type_id = %s,
                latitude = %s,
                longitude = %s,
                status = %s,
                other_type_details = %s
            WHERE station_id = %s;
            """,
            (code, line_id, bait_station_type_id, latitude, longitude, bait_status, other_type_details, marker_id),
        )

def get_bait_station_by_id(station_id, group_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT bs.code
            FROM Bait_Stations bs
            JOIN Line l ON l.line_id = bs.line_id
            WHERE bs.station_id = %s AND l.group_id = %s;
            """,
            (station_id, group_id),
        )
        station_row = cursor.fetchone()
    return station_row

def add_bait_station(code, line_id, latitude, longitude, bait_station_type_id, other_type_details=None):
    """
    Insert a new bait station record.
    """
    query = """
        INSERT INTO Bait_Stations (code, line_id, latitude, longitude, bait_station_type_id, other_type_details)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING station_id;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (code, line_id, latitude, longitude, bait_station_type_id, other_type_details))
        result = cursor.fetchone()
        return result['station_id'] if result else None

def get_stations_by_line(line_id):
    """
    Fetch all bait stations for a specific line, including type name.
    """
    query = """
        SELECT bs.station_id, bs.code, bs.latitude, bs.longitude, bs.status, 
               bst.name as bait_station_type, bs.other_type_details
        FROM Bait_Stations bs
        JOIN Bait_Station_Types bst ON bs.bait_station_type_id = bst.id
        WHERE bs.line_id = %s
        ORDER BY bs.code;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (line_id,))
        return cursor.fetchall()

def is_station_code_unique(code):
    """
    Check if a station code is unique across all bait stations.
    """
    query = "SELECT 1 FROM Bait_Stations WHERE code = %s LIMIT 1;"
    with get_cursor() as cursor:
        cursor.execute(query, (code,))
        return cursor.fetchone() is None

def get_station_by_id(station_id):
    """
    Fetch a single bait station by its ID.
    """
    query = """
        SELECT bs.station_id, bs.code, bs.latitude, bs.longitude, bs.status, 
               bs.line_id, l.name as line_name,
               bst.name as bait_station_type, bs.other_type_details
        FROM Bait_Stations bs
        JOIN Line l ON bs.line_id = l.line_id
        JOIN Bait_Station_Types bst ON bs.bait_station_type_id = bst.id
        WHERE bs.station_id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (station_id,))
        return cursor.fetchone()

def update_bait_station(station_id, bait_station_type_id, latitude, longitude, status, other_type_details=None):
    """
    Update an existing bait station record.
    """
    query = """
        UPDATE Bait_Stations
        SET bait_station_type_id = %s, latitude = %s, longitude = %s, status = %s, other_type_details = %s
        WHERE station_id = %s;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (bait_station_type_id, latitude, longitude, status, other_type_details, station_id))
        return cursor.rowcount > 0

def retire_bait_station(station_id):
    """
    Set a bait station status to Inactive.
    """
    query = "UPDATE Bait_Stations SET status = 'Inactive' WHERE station_id = %s;"
    with get_cursor() as cursor:
        cursor.execute(query, (station_id,))
        return cursor.rowcount > 0

def get_bait_station_types():
    """
    Fetch all active bait station types.
    """
    query = """
        SELECT name, id
        FROM Bait_Station_Types
        WHERE status = 'Active'
        ORDER BY name;
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()
