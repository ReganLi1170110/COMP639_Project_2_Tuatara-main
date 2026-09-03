import json


from app.utils import get_cursor


def get_groups_by_user_id(user_id):
    """Return a list of groups that a user belongs to."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT g.group_id, g.name, g.description, g.charitable_name, g.charity_registration_number,
                g.is_public, g.status, g.operational_area, gm.role,
                (
                    SELECT STRING_AGG(u.first_name || ' ' || COALESCE(u.last_name, ''), ', ')
                    FROM Group_Members c_gm
                    JOIN Users u ON c_gm.user_id = u.user_id
                    WHERE c_gm.group_id = g.group_id 
                      AND c_gm.role IN ('Coordinator', 'Group Coordinator')
                      AND c_gm.membership_status = 'Active'
                ) as coordinators_names
            FROM Groups g
            JOIN Group_Members gm ON g.group_id = gm.group_id
            WHERE gm.user_id = %s and g.status = 'Active' and gm.membership_status = 'Active';
            """,
            (user_id,)
        )
        groups = cursor.fetchall()
        return groups


def get_active_groups_for_home(page=1, page_size=6):
    """Return active groups shown on the public home page with pagination."""
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size

    with get_cursor() as cursor:
        cursor.execute(
            """
            WITH paged_groups AS (
                SELECT
                    g.group_id,
                    g.name,
                    g.description,
                    g.image_url,
                    g.charitable_name,
                    g.charity_registration_number,
                    g.is_public,
                    g.operational_area,
                    COUNT(*) OVER() AS total_count
                FROM Groups g
                WHERE g.status = 'Active'
                ORDER BY g.name ASC
                LIMIT %s OFFSET %s
            )
            SELECT
                pg.group_id,
                pg.name,
                pg.description,
                pg.image_url,
                pg.charitable_name,
                pg.charity_registration_number,
                pg.is_public,
                pg.operational_area,
                pg.total_count,
                COUNT(gm.id) FILTER (WHERE gm.membership_status = 'Active') AS active_member_count
            FROM paged_groups pg
            LEFT JOIN Group_Members gm ON gm.group_id = pg.group_id
            GROUP BY
                pg.group_id,
                pg.name,
                pg.description,
                pg.image_url,
                pg.charitable_name,
                pg.charity_registration_number,
                pg.is_public,
                pg.operational_area,
                pg.total_count
            ORDER BY pg.name ASC;
            """,
            (page_size, offset)
        )
        groups = cursor.fetchall()

    total_count = groups[0]["total_count"] if groups else 0
    return groups, total_count


def get_public_groups():
    """Return all public, active groups (id and name) for selection lists."""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT group_id, name
            FROM Groups
            WHERE is_public = TRUE AND status = 'Active'
            ORDER BY name ASC
        """)
        return cursor.fetchall()


# ── SA: Group management ───────────────────────────────────────────────────────

def get_all_groups_for_admin():
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT
                g.group_id, g.name, g.description, g.image_url,
                g.is_public, g.status, g.charitable_name,
                g.charity_registration_number, g.donation_description,
                u.first_name || ' ' || u.last_name AS created_by_name
            FROM Groups g
            LEFT JOIN Users u ON u.user_id = g.created_by
            WHERE g.status IN ('Active', 'Pending', 'Inactive')
            ORDER BY
                CASE g.status
                    WHEN 'Pending'  THEN 1
                    WHEN 'Active'   THEN 2
                    WHEN 'Inactive' THEN 3
                END, g.name ASC
        """)
        return cursor.fetchall()


def get_group_by_id(group_id):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT group_id, name, description, image_url, is_public, status,
                   charitable_name, charity_registration_number, donation_description, operational_area, created_by
            FROM Groups WHERE group_id = %s
        """, (group_id,))
        return cursor.fetchone()


def create_group(name, description, image_url, is_public, created_by, operational_area=None):
    operational_area_value = json.dumps(operational_area) if operational_area is not None else None
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO Groups (name, description, image_url, is_public, status, operational_area, created_by)
            VALUES (%s, %s, %s, %s, 'Active', %s, %s)
            RETURNING group_id
        """, (name, description, image_url, is_public, operational_area_value, created_by))
        return cursor.fetchone()['group_id']


def create_group_application(name, description, is_public, created_by, operational_area=None):
    """Submit a new group application with Pending status, awaiting Super Admin approval."""
    operational_area_value = json.dumps(operational_area) if operational_area is not None else None
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO Groups (name, description, image_url, is_public, status, operational_area, created_by)
            VALUES (%s, %s, NULL, %s, 'Pending', %s, %s)
            RETURNING group_id
        """, (name, description, is_public, operational_area_value, created_by))
        return cursor.fetchone()['group_id']


def update_group(group_id, name, description, image_url, is_public, status,
                 charitable_name, charity_registration_number, donation_description):
    with get_cursor() as cursor:
        cursor.execute("""
            UPDATE Groups SET name=%s, description=%s, image_url=%s, is_public=%s,
                status=%s, charitable_name=%s, charity_registration_number=%s, donation_description=%s
            WHERE group_id=%s
        """, (name, description, image_url, is_public,
              status, charitable_name, charity_registration_number,
              donation_description, group_id))


def set_group_status(group_id, status):
    """Set group status only if the group is currently Pending.

    Returns True if the status was changed, False if no row was updated
    (e.g. it was already processed or did not exist).
    """
    with get_cursor() as cursor:
        cursor.execute("UPDATE Groups SET status=%s WHERE group_id=%s AND status='Pending'", (status, group_id))
        updated = cursor.rowcount > 0
        return updated


def get_pending_group_applications():
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT g.group_id, g.name, g.description, g.is_public,
                   u.first_name || ' ' || u.last_name AS applicant_name,
                   u.email AS applicant_email
            FROM Groups g
            JOIN Users u ON u.user_id = g.created_by
            WHERE g.status = 'Pending'
            ORDER BY g.group_id ASC
        """)
        return cursor.fetchall()


# ── SA: Coordinator appointment ───────────────────────────────────────────────

def get_coordinators_for_group(group_id):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT u.user_id,
                   u.first_name || ' ' || u.last_name AS full_name,
                   u.email, gm.membership_status
            FROM Group_Members gm
            JOIN Users u ON u.user_id = gm.user_id
           WHERE gm.group_id=%s AND gm.role IN ('Coordinator', 'Group Coordinator')
            ORDER BY u.first_name ASC
        """, (group_id,))
        return cursor.fetchall()


def get_active_users_not_in_group(group_id=None):
    with get_cursor() as cursor:
        query = """
            SELECT u.user_id, u.first_name || ' ' || u.last_name AS full_name, u.email
            FROM Users u
            WHERE u.account_status='Active' AND u.is_super_admin=FALSE
        """
        params = []
        if group_id is not None:
            query += " AND u.user_id NOT IN (SELECT user_id FROM Group_Members WHERE group_id=%s AND membership_status='Active')"
            params.append(group_id)
        query += " ORDER BY u.first_name ASC"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()


def appoint_coordinator(group_id, user_id):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT id FROM Group_Members WHERE group_id=%s AND user_id=%s
        """, (group_id, user_id))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE Group_Members SET role='Coordinator', membership_status='Active'
                WHERE group_id=%s AND user_id=%s
            """, (group_id, user_id))
        else:
            cursor.execute("""
                INSERT INTO Group_Members (group_id, user_id, role, membership_status)
                VALUES (%s, %s, 'Coordinator', 'Active')
            """, (group_id, user_id))


def remove_coordinator(group_id, user_id):
    with get_cursor() as cursor:
        cursor.execute("""
            DELETE FROM Group_Members WHERE group_id=%s AND user_id=%s AND role IN ('Coordinator', 'Group Coordinator')
        """, (group_id, user_id))


# ── Coordinator: join requests ────────────────────────────────────────────────

def set_group_visibility(group_id, is_public):
    with get_cursor() as cursor:
        cursor.execute("UPDATE Groups SET is_public=%s WHERE group_id=%s", (is_public, group_id))


def get_pending_join_requests(group_id):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT gm.id AS membership_id, u.user_id,
                   u.first_name || ' ' || u.last_name AS full_name, u.email
            FROM Group_Members gm
            JOIN Users u ON u.user_id = gm.user_id
            WHERE gm.group_id=%s AND gm.membership_status='Pending'
            ORDER BY gm.id ASC
        """, (group_id,))
        return cursor.fetchall()


def approve_join_request(membership_id):
    with get_cursor() as cursor:
        cursor.execute("""
            UPDATE Group_Members SET membership_status='Active', role='Observer'
            WHERE id=%s AND membership_status='Pending'
        """, (membership_id,))


def reject_join_request(membership_id):
    with get_cursor() as cursor:
        # Fetch the membership to get user_id and group_id
        cursor.execute("""
            SELECT user_id, group_id FROM Group_Members WHERE id=%s
        """, (membership_id,))
        membership = cursor.fetchone()
        
        # Update status to Rejected
        cursor.execute("""
            UPDATE Group_Members SET membership_status='Rejected'
            WHERE id=%s AND membership_status='Pending'
        """, (membership_id,))
        
        # Create notification for the user
        if membership:
            from app.repository import notification_repository
            group = get_group_by_id(membership['group_id'])
            group_name = group['name'] if group else 'the group'
            message = f'Your request to join "{group_name}" was rejected. You can submit a new request anytime.'
            notification_repository.create_user_notification(
                membership['user_id'],
                message,
                membership['group_id']
            )


def get_group_members(group_id):
    """Return all active members of a group with their roles."""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT
                u.user_id,
                u.first_name || ' ' || u.last_name AS full_name,
                u.email,
                u.phone_number,
                u.account_status,
                gm.role,
                gm.membership_status
            FROM Group_Members gm
            JOIN Users u ON u.user_id = gm.user_id
            WHERE gm.group_id = %s AND gm.membership_status = 'Active'
            ORDER BY gm.role, u.first_name ASC
        """, (group_id,))
        return cursor.fetchall()


def get_group_lines(group_id):
    """Return lines for a group with lightweight activity summaries."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                l.line_id,
                l.name AS line_name,
                l.type AS line_type,
                l.line_status,
                COALESCE(c.catch_count, 0) AS catch_count,
                COALESCE(o.observation_count, 0) AS observation_count,
                GREATEST(
                    COALESCE(c.latest_catch_date, DATE '1900-01-01'),
                    COALESCE(o.latest_observation_date, DATE '1900-01-01')
                ) AS latest_activity
            FROM Line l
            LEFT JOIN (
                SELECT
                    t.line_id,
                    COUNT(*) AS catch_count,
                    MAX(tc.date) AS latest_catch_date
                FROM Trap_Catches tc
                JOIN Traps t ON t.trap_id = tc.trap_id
                GROUP BY t.line_id
            ) c ON c.line_id = l.line_id
            LEFT JOIN (
                SELECT
                    line_id,
                    COUNT(*) AS observation_count,
                    MAX(date_recorded) AS latest_observation_date
                FROM Observation
                GROUP BY line_id
            ) o ON o.line_id = l.line_id
            WHERE l.group_id = %s
            ORDER BY l.name ASC;
            """,
            (group_id,)
        )
        return cursor.fetchall()


def get_group_latest_activity(group_id, limit=8):
    """Return the latest catch and observation activity for a group."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM (
                SELECT
                    'Catch' AS activity_type,
                    tc.date AS activity_date,
                    l.line_id,
                    l.name AS line_name,
                    t.code AS asset_code,
                    COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), 'Unknown') AS recorded_by,
                    s.name AS summary,
                    tc.notes
                FROM Trap_Catches tc
                JOIN Traps t ON t.trap_id = tc.trap_id
                JOIN Line l ON l.line_id = t.line_id
                JOIN Species s ON s.id = tc.species_caught_id
                LEFT JOIN Users u ON u.user_id = tc.recorded_by
                WHERE l.group_id = %s

                UNION ALL

                SELECT
                    'Observation' AS activity_type,
                    o.date_recorded AS activity_date,
                    l.line_id,
                    l.name AS line_name,
                    NULL AS asset_code,
                    COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), 'Unknown') AS recorded_by,
                    COALESCE(NULLIF(o.notes, ''), 'Observation recorded') AS summary,
                    o.notes
                FROM Observation o
                JOIN Line l ON l.line_id = o.line_id
                LEFT JOIN Users u ON u.user_id = o.operator_id
                WHERE l.group_id = %s
            ) activity_feed
            ORDER BY activity_date DESC NULLS LAST
            LIMIT %s;
            """,
            (group_id, group_id, limit)
        )
        return cursor.fetchall()


def update_member_role(group_id, user_id, new_role, account_status):
    """Update a member's role in Group_Members and account_status in Users."""
    with get_cursor() as cursor:
        if new_role:
            cursor.execute("""
                UPDATE Group_Members
                SET role = %s
                WHERE group_id = %s AND user_id = %s
            """, (new_role, group_id, user_id))
        if account_status:
            cursor.execute("""
                UPDATE Users SET account_status = %s WHERE user_id = %s
            """, (account_status, user_id))

def submit_join_request(group_id, user_id, is_public):
    """Submit a join request for a user to join a group.
    
    Returns:
        'Joined'     - User immediately joined (public group)
        'NewPending' - New request submitted for approval (private group)
        'Pending'    - User already has a pending request
        'Active'     - User is already an active member
        'Rejected'   - Previous request was rejected
    """
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT id, membership_status FROM Group_Members
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        existing = cursor.fetchone()
        if existing:
            if existing['membership_status'] in ('Rejected', 'Inactive'):
                if is_public:
                    cursor.execute("""
                        UPDATE Group_Members
                        SET role='Observer', membership_status='Active'
                        WHERE id=%s
                    """, (existing['id'],))
                    return 'Joined'
                cursor.execute("""
                    UPDATE Group_Members
                    SET role='Observer', membership_status='Pending'
                    WHERE id=%s
                """, (existing['id'],))
                return 'NewPending'
            return existing['membership_status']  # Already exists (Active, Pending, etc.)
        if is_public:
            cursor.execute("""
                INSERT INTO Group_Members (group_id, user_id, role, membership_status)
                VALUES (%s, %s, 'Observer', 'Active')
            """, (group_id, user_id))
            return 'Joined'
        else:
            cursor.execute("""
                INSERT INTO Group_Members (group_id, user_id, role, membership_status)
                VALUES (%s, %s, 'Observer', 'Pending')
            """, (group_id, user_id))
            return 'NewPending'


def leave_group(group_id, user_id):
    """Mark an Observer membership as inactive instead of deleting it."""
    with get_cursor() as cursor:
        cursor.execute("""
            UPDATE Group_Members
            SET membership_status = 'Inactive'
            WHERE group_id = %s AND user_id = %s AND role = 'Observer' AND membership_status = 'Active'
        """, (group_id, user_id))
        return cursor.rowcount > 0


def cancel_join_request(group_id, user_id):
    """Cancel a pending join request for a private group.

    Removes the Group_Members row AND cleans up any unread coordinator
    notifications for this user's join request in the same group.  This
    ensures that if the user joins → cancels → joins again the coordinator
    sees exactly ONE fresh notification rather than stale duplicates.
    """
    with get_cursor() as cursor:
        # Fetch the requesting user's name so we can match the notification message.
        cursor.execute("""
            SELECT u.first_name, u.last_name
            FROM Users u
            WHERE u.user_id = %s
        """, (user_id,))
        user_row = cursor.fetchone()

        # Remove the pending membership row.
        cursor.execute("""
            DELETE FROM Group_Members
            WHERE group_id = %s AND user_id = %s AND membership_status = 'Pending'
        """, (group_id, user_id))
        removed = cursor.rowcount > 0

        # If we actually removed a request, clean up the unread coordinator
        # notification(s) for this user + group so they don't stack up.
        if removed and user_row:
            user_name = f"{user_row['first_name']} {user_row['last_name'] or ''}".strip()
            cursor.execute("""
                DELETE FROM Notifications
                WHERE group_id = %s
                  AND is_read = FALSE
                  AND message LIKE %s
            """, (group_id, f'{user_name} has requested to join%'))

        return removed


def get_user_group_statuses(user_id):
    """Return all group memberships for a user including pending ones."""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT group_id, membership_status, role
            FROM Group_Members
            WHERE user_id = %s
        """, (user_id,))
        return cursor.fetchall()



