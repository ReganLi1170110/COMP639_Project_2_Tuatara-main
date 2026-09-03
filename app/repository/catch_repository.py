# Catch Repository
# Handles database operations for trap catch records and monitoring summaries.
# Provides functions for detailed catch history, paginated listings, and data aggregation for charts.

from app.utils import get_cursor

def get_trap_catches(trap_id):
    query = """
        SELECT
            tc.catch_id,
            tc.date,
            tc.species_caught_id,
            tc.sex,
            tc.maturity,
            ts.name AS status,
            tc.rebaited,
            bt.name AS bait_type,
            tc.trap_condition,
            tc.strikes,
            tc.notes,
            s.name AS species_caught,
            u.first_name,
            u.last_name
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Bait_Types bt ON bt.id = tc.bait_type_id
        JOIN USERS u ON u.user_id = tc.recorded_by
        WHERE tc.trap_id = %s
        ORDER BY tc.date DESC;
    """
    with get_cursor() as cursor:
        cursor.execute(query, (trap_id,))
        return cursor.fetchall()

def get_all_catches(filters=None):
    query = """
        SELECT
            tc.catch_id, tc.date, tc.species_caught_id, tc.sex, tc.maturity,
            ts.name AS status, tc.rebaited, bt.name AS bait_type,
            tc.trap_condition, tc.strikes, tc.notes,
            t.trap_id, t.code AS trap_code, t.latitude, t.longitude,
            l.line_id, l.name AS line_name, u.first_name, u.last_name,
            s.name AS species_caught
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Bait_Types bt ON bt.id = tc.bait_type_id
        JOIN Traps t ON t.trap_id = tc.trap_id
        JOIN Line l ON l.line_id = t.line_id
        LEFT JOIN Users u ON u.user_id = tc.recorded_by
        WHERE 1=1
    """
    params = []
    if filters:
        if filters.get('line_id'):
            query += " AND l.line_id = %s"
            params.append(filters['line_id'])
        if filters.get('start_date'):
            query += " AND tc.date >= %s"
            params.append(filters['start_date'])
        if filters.get('end_date'):
            query += " AND tc.date <= %s"
            params.append(filters['end_date'])
        if filters.get('species'):
            query += " AND tc.species_caught_id = %s"
            params.append(filters['species'])
        if filters.get('status'):
            query += " AND tc.trap_status_id = %s"
            params.append(filters['status'])

    query += " ORDER BY tc.date DESC, tc.catch_id DESC"
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

def get_all_catches_paginated(filters=None, page=1, page_size=12):
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size

    query = """
        SELECT
            tc.catch_id, tc.date, tc.species_caught_id, tc.sex, tc.maturity,
            tc.trap_status_id, tc.rebaited, tc.bait_type_id, tc.trap_condition,
            tc.strikes, tc.notes, t.trap_id, t.code AS trap_code, t.latitude, t.longitude,
            l.line_id, l.name AS line_name, u.first_name, u.last_name, tc.recorded_by,
            s.name AS species_caught, ts.name AS status, bt.name AS bait_type,
            COUNT(*) OVER() AS total_count
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Bait_Types bt ON bt.id = tc.bait_type_id
        JOIN Traps t ON t.trap_id = tc.trap_id
        JOIN Line l ON l.line_id = t.line_id
        LEFT JOIN Users u ON u.user_id = tc.recorded_by
        WHERE 1=1
    """
    params = []
    if filters:
        if filters.get('line_id'):
            query += " AND l.line_id = %s"
            params.append(filters['line_id'])
        if filters.get('start_date'):
            query += " AND tc.date >= %s"
            params.append(filters['start_date'])
        if filters.get('end_date'):
            query += " AND tc.date <= %s"
            params.append(filters['end_date'])
        if filters.get('species'):
            query += " AND tc.species_caught_id = %s"
            params.append(filters['species'])
        if filters.get('status'):
            query += " AND tc.trap_status_id = %s"
            params.append(filters['status'])

    query += " ORDER BY tc.date DESC, tc.catch_id DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])

    with get_cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        return [], 0
    return rows, rows[0]["total_count"] or 0

def get_catch_by_id(catch_id):
    query = """
        SELECT tc.*, t.code AS trap_code, l.line_id, l.name AS line_name,
               s.name AS species_caught, ts.name AS status, bt.name AS bait_type
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Bait_Types bt ON bt.id = tc.bait_type_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Traps t ON t.trap_id = tc.trap_id
        JOIN Line l ON l.line_id = t.line_id
        WHERE tc.catch_id = %s
    """
    with get_cursor() as cursor:
        cursor.execute(query, (catch_id,))
        return cursor.fetchone()

def update_catch(catch_id, data):
    query = """
        UPDATE Trap_Catches
        SET date = %s, species_caught_id = %s, sex = %s, maturity = %s,
            trap_status_id = %s, rebaited = %s, bait_type_id = %s,
            trap_condition = %s, strikes = %s, notes = %s
        WHERE catch_id = %s
    """
    with get_cursor() as cursor:
        cursor.execute(query, (
            data['date'], data['species_caught'], data['sex'], data['maturity'],
            data['status'], data['rebaited'], data['bait_type'],
            data['trap_condition'], data['strikes'], data['notes'], catch_id
        ))
        return cursor.rowcount > 0

def add_catch(user_id, data):
     with get_cursor() as cur:
        cur.execute("""
            INSERT INTO Trap_Catches
            (trap_id, recorded_by, date, species_caught_id, sex, maturity,
                trap_status_id, rebaited, bait_type_id, trap_condition, strikes, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (data['trap_id'], user_id, data['date'], data['species_caught_id'], data['sex'], data['maturity'],
                data['trap_status_id'], data['rebaited'], data['bait_type_id'], data['trap_condition'], data['strikes'], data['notes']))

def get_trap_catches_summary_data(start_date=None, end_date=None, group_by='week', operator_id=None, trap_type=None, species=None, group_id=None):
    if group_by not in ('day', 'week', 'month', 'year'):
        group_by = 'week'
    conditions = ""
    params = []
    if start_date:
        conditions += " AND tc.date >= %s"
        params.append(start_date)
    if end_date:
        conditions += " AND tc.date <= %s"
        params.append(end_date)
    if operator_id:
        conditions += " AND EXISTS (SELECT 1 FROM User_Line ul WHERE ul.line_id = t.line_id AND ul.user_id = %s)"
        params.append(operator_id)
    if trap_type:
        conditions += " AND t.trap_type_id = %s"
        params.append(trap_type)
    if species:
        conditions += " AND tc.species_caught_id = %s"
        params.append(species)
    if group_id:
        conditions += " AND l.group_id = %s"
        params.append(group_id)
    query = f"""
        WITH CatchData AS (
            SELECT l.name AS line_name, tc.date AS catch_date, tc.strikes
            FROM Trap_Catches tc
            JOIN Traps t ON tc.trap_id = t.trap_id
            JOIN Line l ON t.line_id = l.line_id
            WHERE 1=1{conditions}
        )
        SELECT line_name, DATE_TRUNC('{group_by}', catch_date) AT TIME ZONE 'UTC' AS time_period, SUM(strikes) AS total_catches
        FROM CatchData
        GROUP BY line_name, time_period
        ORDER BY time_period ASC;
    """
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

def get_chart_operators(group_id=None):
    query = """
        SELECT u.user_id, u.first_name, u.last_name
        FROM Users u
        INNER JOIN Group_Members gm ON u.user_id = gm.user_id
        WHERE gm.role = 'Operator' AND u.account_status = 'Active' AND gm.membership_status = 'Active'
    """
    params = []
    if group_id:
        query += " AND gm.group_id = %s"
        params.append(group_id)
    query += " ORDER BY u.first_name, u.last_name;"

    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()
