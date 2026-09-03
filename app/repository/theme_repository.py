"""
Theme Repository – all DB operations for Group_Themes.
Covers: pre-made gallery (group_id IS NULL), group custom themes,
platform default (created_by = 1 / Admin), version history, rollback.
"""

import json
from app.db import db


def _cursor():
    return db.get_cursor()


# ─── Pre-made gallery themes (group_id IS NULL) ──────────────────────────────

def get_premade_themes():
    """Return all pre-made gallery themes (group_id IS NULL, is_active TRUE)."""
    with _cursor() as cur:
        cur.execute("""
            SELECT theme_id, theme_name, settings
            FROM Group_Themes
            WHERE group_id IS NULL AND is_active = TRUE
            ORDER BY theme_id
        """)
        return cur.fetchall()


# ─── Active theme for a specific group ───────────────────────────────────────

def get_active_theme_for_group(group_id):
    """Return the currently active theme for a group, or None."""
    with _cursor() as cur:
        cur.execute("""
            SELECT theme_id, theme_name, settings, version_number, created_at
            FROM Group_Themes
            WHERE group_id = %s AND is_active = TRUE
            ORDER BY version_number DESC
            LIMIT 1
        """, (group_id,))
        return cur.fetchone()


def get_platform_default_theme():
    """Return the platform-wide default theme (group_id IS NULL, created_by = 1)."""
    with _cursor() as cur:
        cur.execute("""
            SELECT theme_id, theme_name, settings
            FROM Group_Themes
            WHERE group_id IS NULL AND is_active = TRUE
            ORDER BY theme_id
            LIMIT 1
        """)
        return cur.fetchone()


def get_effective_theme(group_id):
    """
    Return the effective theme settings dict for a group.
    Priority: group custom theme > platform default > None
    """
    theme = get_active_theme_for_group(group_id)
    if theme:
        s = theme['settings']
        return s if isinstance(s, dict) else json.loads(s)
    default = get_platform_default_theme()
    if default:
        s = default['settings']
        return s if isinstance(s, dict) else json.loads(s)
    return None


# ─── Save / update theme for a group ─────────────────────────────────────────

def save_theme_for_group(group_id, theme_name, settings_dict, created_by):
    """
    Deactivate all existing themes for the group, then insert a new active one.
    Returns the new theme_id.
    settings_dict is a Python dict – stored as JSONB.
    """
    with _cursor() as cur:
        # Find the current max version for this group
        cur.execute("""
            SELECT COALESCE(MAX(version_number), 0) AS max_ver
            FROM Group_Themes
            WHERE group_id = %s
        """, (group_id,))
        row = cur.fetchone()
        next_version = (row['max_ver'] if row else 0) + 1

        # Deactivate all current active themes for this group
        cur.execute("""
            UPDATE Group_Themes
            SET is_active = FALSE
            WHERE group_id = %s AND is_active = TRUE
        """, (group_id,))

        # Insert new active theme
        cur.execute("""
            INSERT INTO Group_Themes
                (group_id, theme_name, settings, is_active, version_number, created_by)
            VALUES (%s, %s, %s, TRUE, %s, %s)
            RETURNING theme_id
        """, (group_id, theme_name, json.dumps(settings_dict), next_version, created_by))
        row = cur.fetchone()
        db.get_db().commit()
        return row['theme_id']


# ─── Version history / rollback ───────────────────────────────────────────────

def get_theme_history_for_group(group_id, limit=10):
    """
    Return up to `limit` previous (inactive) themes for a group,
    newest first.  Excludes the currently active one.
    """
    with _cursor() as cur:
        cur.execute("""
            SELECT theme_id, theme_name, settings, version_number, created_at
            FROM Group_Themes
            WHERE group_id = %s AND is_active = FALSE
            ORDER BY version_number DESC
            LIMIT %s
        """, (group_id, limit))
        return cur.fetchall()


def rollback_to_theme(group_id, theme_id, created_by):
    """
    Restore a previous theme by:
    1. Deactivating the current active theme.
    2. Copying the target theme's settings into a new active row with next version.
    Returns the new theme_id, or None if target not found.
    """
    with _cursor() as cur:
        # Fetch the target theme
        cur.execute("""
            SELECT theme_name, settings
            FROM Group_Themes
            WHERE theme_id = %s AND group_id = %s
        """, (theme_id, group_id))
        target = cur.fetchone()
        if not target:
            return None

        settings = target['settings']
        if isinstance(settings, str):
            settings = json.loads(settings)

        # Deactivate current
        cur.execute("""
            UPDATE Group_Themes SET is_active = FALSE
            WHERE group_id = %s AND is_active = TRUE
        """, (group_id,))

        # Next version
        cur.execute("""
            SELECT COALESCE(MAX(version_number), 0) AS max_ver
            FROM Group_Themes WHERE group_id = %s
        """, (group_id,))
        row = cur.fetchone()
        next_version = (row['max_ver'] if row else 0) + 1

        cur.execute("""
            INSERT INTO Group_Themes
                (group_id, theme_name, settings, is_active, version_number, created_by)
            VALUES (%s, %s, %s, TRUE, %s, %s)
            RETURNING theme_id
        """, (group_id, target['theme_name'] + ' (Restored)', json.dumps(settings),
              next_version, created_by))
        row = cur.fetchone()
        db.get_db().commit()
        return row['theme_id']


# ─── Admin: platform-wide default theme ──────────────────────────────────────

def save_platform_default_theme(theme_name, settings_dict, created_by):
    """
    Save (or update) the platform-wide default theme.
    group_id = NULL, deactivate old platform defaults first.
    """
    with _cursor() as cur:
        cur.execute("""
            UPDATE Group_Themes
            SET is_active = FALSE
            WHERE group_id IS NULL AND is_active = TRUE
        """)
        cur.execute("""
            INSERT INTO Group_Themes
                (group_id, theme_name, settings, is_active, version_number, created_by)
            VALUES (NULL, %s, %s, TRUE, 1, %s)
            RETURNING theme_id
        """, (theme_name, json.dumps(settings_dict), created_by))
        row = cur.fetchone()
        db.get_db().commit()
        return row['theme_id']
