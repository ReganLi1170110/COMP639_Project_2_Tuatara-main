# Dashboard Repository
# Handles complex summary queries and data aggregation for different user role dashboards.
# Contains functions to fetch metrics for the Observer, Operator, and Admin dashboards.

from app.db import db
from app.utils import get_cursor

def get_observer_dashboard_data(group_id):
    summary_query = """
        SELECT
            (SELECT COUNT(*) FROM Line WHERE line_status = 'Active' AND group_id = %s) AS active_line_count ,
            (SELECT COUNT(*) FROM Traps t join Line l on t.line_id = l.line_id WHERE l.group_id = %s) AS trap_count,
            (SELECT COUNT(*) FROM Trap_Catches tc join Traps t on tc.trap_id = t.trap_id join Line l on t.line_id = l.line_id WHERE l.group_id = %s) AS catch_count,
            (SELECT COUNT(*) FROM Observation o join Line l on o.line_id = l.line_id WHERE l.group_id = %s) AS observation_count,
            (SELECT COUNT(DISTINCT recorded_by) FROM Trap_Catches tc join Traps t on tc.trap_id = t.trap_id join Line l on t.line_id = l.line_id WHERE l.group_id = %s AND recorded_by IS NOT NULL) AS active_operator_count,
            (SELECT COUNT(DISTINCT t.line_id) FROM Trap_Catches tc JOIN Traps t ON t.trap_id = tc.trap_id JOIN Line l ON t.line_id = l.line_id WHERE l.group_id = %s) AS lines_with_catches,
            (SELECT COUNT(DISTINCT l.line_id) FROM Observation o JOIN Line l ON o.line_id = l.line_id WHERE l.group_id = %s) AS lines_with_observations,
            (SELECT MAX(date) FROM Trap_Catches tc JOIN Traps t ON tc.trap_id = t.trap_id JOIN Line l ON t.line_id = l.line_id WHERE l.group_id = %s) AS latest_catch_date,
            (SELECT MAX(date_recorded) FROM Observation o JOIN Line l ON o.line_id = l.line_id WHERE l.group_id = %s) AS latest_observation_date;
    """
    line_activity_query = """
        SELECT l.line_id, l.name AS line_name, l.line_status,
               COALESCE(c.catch_count, 0) AS catch_count,
               COALESCE(o.observation_count, 0) AS observation_count,
               GREATEST(COALESCE(c.latest_catch_date, '1900-01-01'), COALESCE(o.latest_observation_date, '1900-01-01')) AS latest_activity
        FROM Line l
        LEFT JOIN (SELECT t.line_id, COUNT(*) AS catch_count, MAX(tc.date) AS latest_catch_date FROM Trap_Catches tc JOIN Traps t ON t.trap_id = tc.trap_id GROUP BY t.line_id) c ON c.line_id = l.line_id
        LEFT JOIN (SELECT line_id, COUNT(*) AS observation_count, MAX(date_recorded) AS latest_observation_date FROM Observation GROUP BY line_id) o ON o.line_id = l.line_id
        WHERE l.group_id = %s
        ORDER BY latest_activity DESC NULLS LAST, l.name LIMIT 8;
    """
    operator_activity_query = """
        SELECT u.user_id, u.first_name, u.last_name,
               COALESCE(c.catch_count, 0) AS catch_count,
               COALESCE(o.observation_count, 0) AS observation_count,
               COALESCE(c.catch_count, 0) + COALESCE(o.observation_count, 0) AS total_activity
        FROM Users u
        JOIN Group_Members gm ON gm.user_id = u.user_id
        LEFT JOIN (SELECT recorded_by AS user_id, COUNT(*) AS catch_count FROM Trap_Catches WHERE recorded_by IS NOT NULL GROUP BY recorded_by) c ON c.user_id = u.user_id
        LEFT JOIN (SELECT operator_id AS user_id, COUNT(*) AS observation_count FROM Observation WHERE operator_id IS NOT NULL GROUP BY operator_id) o ON o.user_id = u.user_id
        WHERE gm.role = 'Operator' and gm.group_id = %s AND gm.membership_status = 'Active'
        ORDER BY total_activity DESC, u.first_name, u.last_name LIMIT 8;
    """
    recent_catches_query = """
        SELECT tc.catch_id, tc.date, ts.name AS status, tc.strikes, tc.notes, tc.rebaited,
               t.trap_id, t.code AS trap_code, l.line_id, l.name AS line_name,
               u.first_name, u.last_name, s.name AS species_caught
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Traps t ON t.trap_id = tc.trap_id
        JOIN Line l ON l.line_id = t.line_id
        LEFT JOIN Users u ON u.user_id = tc.recorded_by
        WHERE l.group_id = %s
        ORDER BY tc.date DESC, tc.catch_id DESC LIMIT 8;
    """
    recent_observations_query = """
        SELECT o.id AS observation_id, o.date_recorded, o.notes, l.line_id, l.name AS line_name,
               u.first_name, u.last_name
        FROM Observation o
        LEFT JOIN Line l ON l.line_id = o.line_id
        LEFT JOIN Users u ON u.user_id = o.operator_id
        WHERE l.group_id = %s
        ORDER BY o.date_recorded DESC, o.id DESC LIMIT 8;
    """

    with get_cursor() as cursor:
        cursor.execute(summary_query, (group_id, group_id, group_id, group_id, group_id, group_id, group_id, group_id, group_id))
        summary = cursor.fetchone()
        cursor.execute(line_activity_query, (group_id,))
        line_activity = cursor.fetchall()
        cursor.execute(operator_activity_query, (group_id,))
        operator_activity = cursor.fetchall()
        cursor.execute(recent_catches_query, (group_id,))
        recent_catches = cursor.fetchall()
        cursor.execute(recent_observations_query, (group_id,))
        recent_observations = cursor.fetchall()

    return {
        "summary": summary,
        "line_activity": line_activity,
        "operator_activity": operator_activity,
        "recent_catches": recent_catches,
        "recent_observations": recent_observations
    }

def get_operator_dashboard_data(operator_id, group_id):
    summary_query = """
        SELECT
            (SELECT COUNT(*) FROM User_Line ul Join Line l ON l.line_id = ul.line_id WHERE ul.user_id = %s AND l.group_id = %s) AS assigned_line_count,
            (SELECT COUNT(*) 
             FROM (
                SELECT t.trap_id FROM Traps t Join Line l ON l.line_id = t.line_id JOIN User_Line ul ON ul.line_id = l.line_id WHERE ul.user_id = %s AND l.group_id = %s
                UNION ALL
                SELECT bs.station_id FROM Bait_Stations bs Join Line l ON l.line_id = bs.line_id JOIN User_Line ul ON ul.line_id = l.line_id WHERE ul.user_id = %s AND l.group_id = %s
             ) assets) AS assigned_asset_count,
            (SELECT COUNT(*) FROM Trap_Catches tc Join Traps t ON t.trap_id = tc.trap_id Join Line l ON l.line_id = t.line_id WHERE tc.recorded_by = %s AND l.group_id = %s) AS catch_count,
            (SELECT COUNT(*) FROM Observation o Join Line l ON l.line_id = o.line_id WHERE o.operator_id = %s AND l.group_id = %s) AS observation_count,
            (SELECT COALESCE(SUM(cumulative_points), 0) FROM User_Points WHERE user_id = %s) AS cumulative_points
    """
    assigned_lines_query = """
        SELECT l.line_id, l.name AS line_name, l.type AS line_type, l.line_status,
               CASE 
                   WHEN l.type = 'Trap' THEN COUNT(DISTINCT t.trap_id)
                   ELSE COUNT(DISTINCT bs.station_id)
               END AS asset_count
        FROM User_Line ul
        JOIN Line l ON l.line_id = ul.line_id
        LEFT JOIN Traps t ON t.line_id = l.line_id
        LEFT JOIN Bait_Stations bs ON l.line_id = bs.line_id
        WHERE ul.user_id = %s AND l.group_id = %s
        GROUP BY l.line_id, l.name, l.type, l.line_status
        ORDER BY l.name;
    """
    recent_catches_query = """
        SELECT tc.catch_id, tc.date, ts.name AS status, tc.strikes, tc.rebaited, tc.notes,
               t.trap_id, t.code AS trap_code, l.line_id, l.name AS line_name,
               s.name AS species_caught
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Traps t ON t.trap_id = tc.trap_id
        JOIN Line l ON l.line_id = t.line_id
        WHERE tc.recorded_by = %s AND l.group_id = %s
        ORDER BY tc.date DESC, tc.catch_id DESC LIMIT 8;
    """
    recent_observations_query = """
        SELECT o.id AS observation_id, o.date_recorded, o.notes, l.line_id, l.name AS line_name
        FROM Observation o
        LEFT JOIN Line l ON l.line_id = o.line_id
        WHERE o.operator_id = %s AND l.group_id = %s
        ORDER BY o.date_recorded DESC, o.id DESC LIMIT 8;
    """

    with get_cursor() as cursor:
        cursor.execute(summary_query, (operator_id, group_id, operator_id, group_id, operator_id, group_id, operator_id, group_id, operator_id, group_id, operator_id))
        summary = cursor.fetchone()
        cursor.execute(assigned_lines_query, (operator_id, group_id))
        assigned_lines = cursor.fetchall()
        cursor.execute(recent_catches_query, (operator_id, group_id))
        recent_catches = cursor.fetchall()
        cursor.execute(recent_observations_query, (operator_id, group_id))
        recent_observations = cursor.fetchall()

    return {
        "summary": summary,
        "assigned_lines": assigned_lines,
        "recent_catches": recent_catches,
        "recent_observations": recent_observations
    }

def get_admin_dashboard_data(group_id):
    summary_query = """
        SELECT
            (SELECT COUNT(*) FROM Line WHERE group_id = %s) AS total_line_count,
            (SELECT COUNT(*) FROM Line WHERE line_status = 'Active' AND group_id = %s) AS active_line_count,
            (SELECT (SELECT COUNT(*) FROM Traps t join Line l on t.line_id = l.line_id WHERE l.group_id = %s) + (SELECT COUNT(*) FROM Bait_Stations bs join Line l on bs.line_id = l.line_id WHERE l.group_id = %s)) AS total_asset_count,
            (SELECT COUNT(*) FROM Group_Members WHERE group_id=%s and role = 'Operator' AND membership_status = 'Active') AS total_operator_count,
            (SELECT COUNT(*) FROM Trap_Catches tc join Traps t on tc.trap_id = t.trap_id join Line l on t.line_id = l.line_id WHERE l.group_id = %s) AS total_catch_count,
            (SELECT COUNT(*) FROM Observation o join Line l on o.line_id = l.line_id WHERE l.group_id = %s) AS total_observation_count;
    """
    lines_overview_query = """
        SELECT l.line_id, l.name AS line_name, l.type AS line_type, l.line_status,
               CASE 
                   WHEN l.type = 'Trap' THEN COALESCE(t.trap_count, 0)
                   ELSE COALESCE(bs.station_count, 0)
               END AS asset_count,
               COALESCE(op.operator_count, 0) AS operator_count,
               COALESCE(c.catch_count, 0) AS catch_count,
               COALESCE(o.observation_count, 0) AS observation_count
        FROM Line l
        LEFT JOIN (SELECT line_id, COUNT(*) AS trap_count FROM Traps GROUP BY line_id) t ON t.line_id = l.line_id
        LEFT JOIN (SELECT line_id, COUNT(*) AS station_count FROM Bait_Stations GROUP BY line_id) bs ON bs.line_id = l.line_id
        LEFT JOIN (SELECT ul.line_id, COUNT(DISTINCT ul.user_id) AS operator_count FROM User_Line ul JOIN Group_Members gm ON gm.user_id = ul.user_id WHERE gm.role = 'Operator' GROUP BY ul.line_id) op ON op.line_id = l.line_id
        LEFT JOIN (SELECT t.line_id, COUNT(*) AS catch_count FROM Trap_Catches tc JOIN Traps t ON t.trap_id = tc.trap_id GROUP BY t.line_id) c ON c.line_id = l.line_id
        LEFT JOIN (SELECT line_id, COUNT(*) AS observation_count FROM Observation GROUP BY line_id) o ON o.line_id = l.line_id
        WHERE l.group_id = %s
        ORDER BY catch_count DESC, l.name LIMIT 8;
    """
    operators_overview_query = """
        SELECT u.user_id, u.first_name, u.last_name, u.account_status,
               COALESCE(al.assigned_line_count, 0) AS assigned_line_count,
               COALESCE(ac.catch_count, 0) AS catch_count,
               COALESCE(ao.observation_count, 0) AS observation_count
        FROM Users u
        LEFT JOIN (SELECT user_id, COUNT(*) AS assigned_line_count FROM User_Line GROUP BY user_id) al ON al.user_id = u.user_id
        LEFT JOIN (SELECT recorded_by AS user_id, COUNT(*) AS catch_count FROM Trap_Catches WHERE recorded_by IS NOT NULL GROUP BY recorded_by) ac ON ac.user_id = u.user_id
        LEFT JOIN (SELECT operator_id AS user_id, COUNT(*) AS observation_count FROM Observation WHERE operator_id IS NOT NULL GROUP BY operator_id) ao ON ao.user_id = u.user_id
        JOIN Group_Members gm ON gm.user_id = u.user_id
        WHERE gm.role = 'Operator'
        AND gm.group_id = %s
        AND gm.membership_status = 'Active'
        ORDER BY catch_count DESC, u.first_name, u.last_name LIMIT 8;
    """

    recent_catches_query = """
        SELECT tc.catch_id, tc.date, ts.name AS status, t.code AS trap_code, l.name AS line_name,
               u.first_name, u.last_name, s.name AS species_caught
        FROM Trap_Catches tc
        JOIN Species s ON s.id = tc.species_caught_id
        JOIN Trap_Status ts ON ts.id = tc.trap_status_id
        JOIN Traps t ON t.trap_id = tc.trap_id
        JOIN Line l ON l.line_id = t.line_id
        LEFT JOIN Users u ON u.user_id = tc.recorded_by
        WHERE l.group_id = %s
        ORDER BY tc.date DESC, tc.catch_id DESC LIMIT 8;
    """
    recent_observations_query = """
        SELECT o.id AS observation_id, o.date_recorded, o.notes, l.name AS line_name,
               u.first_name, u.last_name
        FROM Observation o
        LEFT JOIN Line l ON l.line_id = o.line_id
        LEFT JOIN Users u ON u.user_id = o.operator_id
        WHERE l.group_id = %s
        ORDER BY o.date_recorded DESC, o.id DESC LIMIT 8;
    """

    with get_cursor() as cursor:
        cursor.execute(summary_query, (group_id, group_id, group_id, group_id, group_id, group_id, group_id))
        summary = cursor.fetchone()
        cursor.execute(lines_overview_query, (group_id,))
        lines_overview = cursor.fetchall()
        cursor.execute(operators_overview_query, (group_id,))
        operators_overview = cursor.fetchall()
        cursor.execute(recent_catches_query, (group_id,))
        recent_catches = cursor.fetchall()
        cursor.execute(recent_observations_query, (group_id,))
        recent_observations = cursor.fetchall()

    return {
        "summary": summary,
        "lines_overview": lines_overview,
        "operators_overview": operators_overview,
        "recent_catches": recent_catches,
        "recent_observations": recent_observations
    }


def get_super_admin_dashboard_data():
    summary_query = """
        SELECT
            (SELECT COUNT(*) FROM Groups) AS total_group_count,
            (SELECT COUNT(*) FROM Groups WHERE status = 'Active') AS active_group_count,
            (SELECT COUNT(*) FROM Groups WHERE status = 'Pending') AS pending_group_count,
            (SELECT COUNT(*) FROM Users WHERE account_status = 'Active' AND is_super_admin = FALSE) AS active_user_count,
            (SELECT COUNT(*)
             FROM Group_Members
             WHERE membership_status = 'Active' AND role IN ('Coordinator', 'Group Coordinator')) AS active_coordinator_count,
            (SELECT COUNT(*) FROM Donations) AS total_donation_count,
            (SELECT COALESCE(SUM(amount), 0) FROM Donations) AS total_donation_amount;
    """

    recent_groups_query = """
        SELECT
            g.group_id,
            g.name,
            g.status,
            g.is_public,
            g.charitable_name,
            u.first_name || ' ' || u.last_name AS created_by_name
        FROM Groups g
        LEFT JOIN Users u ON u.user_id = g.created_by
        ORDER BY g.group_id DESC
        LIMIT 8;
    """

    pending_applications_query = """
        SELECT
            g.group_id,
            g.name,
            g.is_public,
            u.first_name || ' ' || u.last_name AS applicant_name,
            u.email AS applicant_email
        FROM Groups g
        JOIN Users u ON u.user_id = g.created_by
        WHERE g.status = 'Pending'
        ORDER BY g.group_id DESC
        LIMIT 8;
    """

    recent_donations_query = """
        SELECT
            d.donation_id,
            d.amount,
            d.donation_date,
            d.donation_type,
            d.donor_name,
            d.donor_email,
            d.is_anonymous,
            g.name AS group_name
        FROM Donations d
        LEFT JOIN Groups g ON g.group_id = d.group_id
        ORDER BY d.donation_date DESC, d.donation_id DESC
        LIMIT 8;
    """

    with get_cursor() as cursor:
        cursor.execute(summary_query)
        summary = cursor.fetchone()
        cursor.execute(recent_groups_query)
        recent_groups = cursor.fetchall()
        cursor.execute(pending_applications_query)
        pending_applications = cursor.fetchall()
        cursor.execute(recent_donations_query)
        recent_donations = cursor.fetchall()

    return {
        "summary": summary,
        "recent_groups": recent_groups,
        "pending_applications": pending_applications,
        "recent_donations": recent_donations,
    }
