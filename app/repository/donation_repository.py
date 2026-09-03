from datetime import datetime, timezone
from app.utils import get_cursor


def create_donation(donation):
    """Insert a donation record into the Donations table.

    Expects keys: amount, donation_type, donor_name, contact_email, message,
    anonymous (bool), group_id (optional), donor_id (optional)
    Returns the inserted donation_id.
    """
    # Enforce anonymous logic: do not store donor_id or donor_name when anonymous
    if donation.get('anonymous'):
        donation['donor_name'] = None
        donation['donor_id'] = None

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Donations
                (group_id, donor_id, amount, donation_type, donor_name, donor_email, is_anonymous, message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING donation_id, donation_date, group_id, donor_id, amount, donation_type, donor_name, donor_email, is_anonymous, message, receipt_issued
            """,
            (
                donation.get('group_id'),
                donation.get('donor_id'),
                donation.get('amount'),
                donation.get('donation_type'),
                donation.get('donor_name'),
                donation.get('contact_email'),
                donation.get('anonymous', False),
                donation.get('message')
            )
        )
        row = cursor.fetchone()
        # return full inserted row (dict) so caller can verify donation_date
        return row


def get_all_donations():
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Donations ORDER BY donation_date DESC")
        return cursor.fetchall()


def get_donation_summary_for_group(group_id):
    """Return a summary of donations for a given group_id.

    Returns a dict with keys: total_amount (Decimal), donation_count (int), latest_donation_date (timestamp)
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS total_amount,
                COUNT(*) AS donation_count,
                MAX(donation_date) AS latest_donation_date
            FROM Donations
            WHERE group_id = %s
            """,
            (group_id,)
        )
        return cursor.fetchone()


def get_donations_for_group(group_id, limit=None):
    """Return donation records for a given group ordered by date desc.

    If `limit` is provided, limit the number of records returned.
    """
    with get_cursor() as cursor:
        sql = "SELECT donation_id, amount, donation_date, donation_type, donor_name, donor_email, is_anonymous, message, receipt_issued FROM Donations WHERE group_id = %s ORDER BY donation_date DESC"
        params = (group_id,)
        if limit:
            sql = sql + " LIMIT %s"
            params = (group_id, limit)
        cursor.execute(sql, params)
        return cursor.fetchall()
        

def get_donation_by_id(donation_id):
    """Return a single donation record by donation_id."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT donation_id, group_id, donor_id, amount, donation_date,
                   donation_type, donor_name, donor_email, is_anonymous, message, receipt_issued
            FROM Donations
            WHERE donation_id = %s
            """,
            (donation_id,)
        )
        return cursor.fetchone()


def get_all_groups_for_donate():
    """Return ALL active groups (public and private) for the donation group dropdown."""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT group_id, name, is_public
            FROM Groups
            WHERE status = 'Active'
            ORDER BY name ASC
        """)
        return cursor.fetchall()


def get_all_donations_with_group_names():
    """Return all donation records across all groups, with their group name if applicable."""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT d.donation_id, d.group_id, d.donor_id, d.amount, d.donation_date,
                   d.donation_type, d.donor_name, d.donor_email, d.is_anonymous, d.message, d.receipt_issued,
                   g.name AS group_name
            FROM Donations d
            LEFT JOIN Groups g ON d.group_id = g.group_id
            ORDER BY d.donation_date DESC
        """)
        return cursor.fetchall()

