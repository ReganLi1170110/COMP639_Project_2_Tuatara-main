# Bait Station Record Repository
# Handles database operations for monitoring activity at bait stations, 
# including bait replenishment and consumption tracking.

from app.utils import get_cursor

def get_station_records(station_id):
    query = """
        SELECT
            bsr.record_id,
            bsr.date_recorded AS date,
            bsr.bait_remaining,
            bsr.bait_removed,
            bsr.bait_added,
            bsr.target_species_id,
            s.name AS target_species,
            bsr.active_ingredient,
            bsr.formulation,
            bsr.concentration,
            bsr.notes,
            u.first_name,
            u.last_name
        FROM Bait_Station_Records bsr
        LEFT JOIN Users u ON u.user_id = bsr.recorded_by
        LEFT JOIN Species s ON s.id = bsr.target_species_id
        WHERE bsr.station_id = %s
        ORDER BY bsr.date_recorded DESC;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (station_id,))
        return cursor.fetchall()

def add_station_record(station_id, recorded_by, bait_remaining, bait_added, notes, date=None,
                       bait_removed=0.0, target_species_id=1, active_ingredient='N/A', formulation='N/A', concentration=0.0):
    if date is None:
        from datetime import datetime
        date = datetime.now()
        
    query = """
        INSERT INTO Bait_Station_Records 
        (station_id, recorded_by, date_recorded, bait_remaining, bait_removed, bait_added, target_species_id, active_ingredient, formulation, concentration, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    with get_cursor() as cursor:
        cursor.execute(query, (station_id, recorded_by, date, bait_remaining, bait_removed, bait_added, target_species_id, active_ingredient, formulation, concentration, notes))
        return True

def get_active_ingredients():
    """Get all available active ingredient enum values from PostgreSQL ENUM type."""
    with get_cursor() as cur:
        # PostgreSQL query to get all values from an ENUM type
        cur.execute("""
            SELECT enumlabel as value 
            FROM pg_enum 
            WHERE enumtypid = 'active_ingredient_enum'::regtype
            ORDER BY enumsortorder
        """)
        rows = cur.fetchall()
        return [{"value": row['value'], "label": row['value']} for row in rows]
