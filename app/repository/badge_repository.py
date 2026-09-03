from enum import Enum

from app.utils import get_cursor
from app.db import db

BADGES_SEED = [
    ("Rimu", "Roots of conservation", 500, "rimu", 1),
    ("Kauri", "Ancient and enduring", 2000, "kauri", 2),
    ("Pōhutukawa", "Coastal guardian", 5000, "pohutukawa", 3),
    ("Kōwhai", "Bright future", 10000, "kowhai", 4),
    ("Mānuka", "Healing the land", 20000, "manuka", 5),
    ("Pounamu", "Treasure of the land", 40000, "pounamu", 6),
    ("Whetū", "Guided by the stars", 60000, "whetu", 7),
    ("Matariki", "New beginnings, remembrance", 100000, "matariki", 8),
]

class BadgeAction(str, Enum):
    DAILY_LOGIN = 'daily_login'
    LIKE = 'like'
    PHOTO_UPLOAD = 'photo_upload'
    ADD_TRAP = 'add_trap'
    ADD_BAIT_STATION = 'add_bait_station'
    LINE_MAINTENANCE = 'line_maintenance'
    CREATE_LINE = 'create_line'
    KNOWLEDGE_POST = 'knowledge_post'
    TRAP_MAINTENANCE = 'trap_maintenance'
    CREATE_GROUP = 'create_group'
    CATCH = 'catch'
    OBSERVATION = 'observation'
    DONATION = 'donation'


BADGE_POINTS = {
    BadgeAction.DAILY_LOGIN: 1,
    BadgeAction.LIKE: 1,
    BadgeAction.PHOTO_UPLOAD: 2,
    BadgeAction.ADD_TRAP: 2,
    BadgeAction.ADD_BAIT_STATION: 2,
    BadgeAction.LINE_MAINTENANCE: 3,
    BadgeAction.CREATE_LINE: 3,
    BadgeAction.KNOWLEDGE_POST: 3,
    BadgeAction.TRAP_MAINTENANCE: 5,
    BadgeAction.CREATE_GROUP: 5,
    BadgeAction.CATCH: 10,
    BadgeAction.OBSERVATION: 10,
    BadgeAction.DONATION: 10,
}


def _to_badge_action(action):
    if isinstance(action, BadgeAction):
        return action

    if isinstance(action, str):
        try:
            return BadgeAction(action)
        except ValueError:
            return None

    return None


def add_user_points(user_id, action, description, ratio = 100):
    action_key = _to_badge_action(action)
    points = BADGE_POINTS.get(action_key)
    if points is None:
        return False

    points *= ratio
    try:
        with get_cursor() as cur:
            cur.execute("INSERT INTO User_Points (user_id, cumulative_points, notes) VALUES (%s, %s, %s)", (user_id, points, description))
        print(f"Awarded {points} points to user_id {user_id} for action '{action}' with description: {description}")
    except Exception as e:
        print(f"Error awarding points to user_id {user_id} for action '{action}': {e}")
    return True

def get_user_points(user_id):
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(cumulative_points), 0) AS total_points FROM User_Points WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        return result['total_points'] if result else 0


def get_user_badge_redemptions(user_id):
    with get_cursor() as cur:
        cur.execute(
            "SELECT redemption_id, badge_name, status, requested_at, shipped_at "
            "FROM Badge_Redemptions "
            "WHERE user_id = %s",
            (user_id,)
        )
        return cur.fetchall() or []


def get_user_badge_redemption(user_id, badge_name):
    with get_cursor() as cur:
        cur.execute(
            "SELECT redemption_id, badge_name, status, requested_at, shipped_at "
            "FROM Badge_Redemptions "
            "WHERE user_id = %s AND badge_name = %s",
            (user_id, badge_name)
        )
        return cur.fetchone()


def add_badge_redemption(user_id, badge_name, recipient_name, shipping_address, city, postcode):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO Badge_Redemptions "
            "(user_id, badge_name, recipient_name, shipping_address, city, postcode) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING redemption_id",
            (user_id, badge_name, recipient_name, shipping_address, city, postcode),
        )
        result = cur.fetchone()
        return result["redemption_id"] if result else None


def get_pending_badge_redemptions():
    with get_cursor() as cur:
        cur.execute(
            "SELECT br.redemption_id, br.user_id, br.badge_name, br.recipient_name, br.shipping_address, br.city, br.postcode, br.status, br.requested_at, br.shipped_at, "
            "u.username, u.first_name, u.last_name, u.email "
            "FROM Badge_Redemptions br "
            "JOIN Users u ON u.user_id = br.user_id "
            "WHERE br.status = 'Pending' "
            "ORDER BY br.requested_at ASC"
        )
        return cur.fetchall() or []


def get_shipped_badge_redemptions():
    with get_cursor() as cur:
        cur.execute(
            "SELECT br.redemption_id, br.user_id, br.badge_name, br.recipient_name, br.shipping_address, br.city, br.postcode, br.status, br.requested_at, br.shipped_at, "
            "u.username, u.first_name, u.last_name, u.email "
            "FROM Badge_Redemptions br "
            "JOIN Users u ON u.user_id = br.user_id "
            "WHERE br.status = 'Shipped' "
            "ORDER BY br.shipped_at DESC"
        )
        return cur.fetchall() or []


def mark_badge_redemption_shipped(redemption_id):
    with get_cursor() as cur:
        cur.execute(
            "UPDATE Badge_Redemptions SET status = 'Shipped', shipped_at = CURRENT_TIMESTAMP "
            "WHERE redemption_id = %s AND status = 'Pending'",
            (redemption_id,)
        )
        return cur.rowcount > 0

