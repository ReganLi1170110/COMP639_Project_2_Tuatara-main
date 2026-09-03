# Notification Repository
# Handles notification storage, retrieval, and status management for users.

from app.utils import get_cursor
from app.repository import user_repository, core_repository

def create_line_assignment_notifications(line_id, line_name, admin_name, added_operator_ids=None, removed_operator_ids=None):
    """Create assignment change notifications for added/removed operators."""
    added_operator_ids = set(added_operator_ids or [])
    removed_operator_ids = set(removed_operator_ids or [])
    if not added_operator_ids and not removed_operator_ids:
        return

    insert_query = """
        INSERT INTO Notifications (user_id, message)
        VALUES (%s, %s);
    """

    with get_cursor() as cursor:
        for operator_id in sorted(added_operator_ids):
            message = f'Line "{line_name}" has been assigned to you by admin {admin_name}.'
            cursor.execute(insert_query, (operator_id, message))

        for operator_id in sorted(removed_operator_ids):
            message = f'You have been unassigned from line "{line_name}" by admin {admin_name}.'
            cursor.execute(insert_query, (operator_id, message))

def get_unread_notifications(user_id, group_id=None, limit=10):
    """Return unread notifications ordered by newest first."""
    query = """
        SELECT notification_id, message, created_at
        FROM Notifications
        WHERE user_id = %s AND is_read = FALSE
    """
    params = [user_id]
    if group_id is not None:
        query += " AND (group_id = %s or group_id IS NULL) "
        params.append(group_id)
    # If group_id is None, do not restrict by group so users without a
    # selected group still receive group-scoped notifications (e.g. join
    # request rejections). This ensures rejected users see their rejection
    # notices even if they are not a member of the group.
    query += """
        ORDER BY created_at DESC, notification_id DESC
        LIMIT %s;
    """
    params.append(limit)
    with get_cursor() as cursor:
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

def mark_notifications_read(user_id, group_id=None):
    """Mark all unread notifications as read for a user."""
    query = """
        UPDATE Notifications
        SET is_read = TRUE
        WHERE user_id = %s AND is_read = FALSE
    """
    params = [user_id]
    if group_id is not None:
        query += " AND (group_id = %s OR group_id IS NULL)"
        params.append(group_id)
    else:
        # No group filter when group_id is None — mark all unread for user
        # (including group-scoped notifications) as read.
        pass
    query += ";"
        
    with get_cursor() as cursor:
        cursor.execute(query, tuple(params))

def get_dashboard_notifications(user_id, group_id=None):
    """Fetch unread notifications and mark them read."""
    notifications = get_unread_notifications(user_id, group_id)
    if notifications:
        mark_notifications_read(user_id, group_id)
    return notifications


def create_user_notification(user_id, message, group_id=None):
    """Create a generic notification for a single user."""
    query = """
        INSERT INTO Notifications (user_id, message, group_id)
        VALUES (%s, %s, %s);
    """
    with get_cursor() as cursor:
        cursor.execute(query, (user_id, message, group_id))


def _format_admin_name(admin_user_id):
    if not admin_user_id:
        return "Administrator"
    admin = user_repository.get_user_by_id(admin_user_id)
    if not admin:
        return "Administrator"
    return f"{admin.get('first_name','')} {admin.get('last_name') or ''}".strip()


def notify_user_role_changed(target_user_id, new_role, admin_user_id=None, group_id=None):
    """Create a notification telling a user their role changed.

    This writes a row to Notifications via `create_user_notification`.
    """
    admin_name = _format_admin_name(admin_user_id)
    group_name = None
    if group_id:
        g = core_repository.get_group_by_id(group_id)
        group_name = g['name'] if g else None

    if group_name:
        message = f'Your role in the group "{group_name}" has been updated to "{new_role}" by {admin_name}.'
    else:
        message = f'Your role has been updated to "{new_role}" by {admin_name}.'

    create_user_notification(target_user_id, message, group_id)


def notify_coordinator_appointed(target_user_id, group_id, admin_user_id=None):
    admin_name = _format_admin_name(admin_user_id)
    group_name = None
    if group_id:
        g = core_repository.get_group_by_id(group_id)
        group_name = g['name'] if g else None

    if group_name:
        message = f'You have been appointed as Coordinator for "{group_name}" by {admin_name}.'
    else:
        message = f'You have been appointed as Coordinator by {admin_name}.'

    create_user_notification(target_user_id, message)
