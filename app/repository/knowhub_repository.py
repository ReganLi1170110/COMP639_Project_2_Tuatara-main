import base64
import json
import os
from datetime import datetime

from app import flask_app as app
from app.utils import get_cursor
from app.repository import user_repository


DRAFT_STATUS = "Draft"
PENDING_STATUS = "Pending"
PUBLISHED_STATUS = "Published"
COORDINATOR_ROLES = ("Coordinator", "Group Coordinator")
ATTACHMENT_PAYLOAD_PREFIX = "DBA1"
KNOWLEDGE_ATTACHMENT_TITLE_PREFIX = "__KH_ATTACH__"
HIDDEN_HISTORY_TITLE_PREFIX = "HISTORY::"


def _utc_now_iso():
    return datetime.utcnow().isoformat() + 'Z'


def _history_carrier_title(kind, source_id):
    return f"{HIDDEN_HISTORY_TITLE_PREFIX}{kind}::{source_id}"


def _hidden_title_prefixes():
    return [
        KNOWLEDGE_ATTACHMENT_TITLE_PREFIX,
        _history_carrier_title("knowledge", ""),
        _history_carrier_title("notice", ""),
    ]


def _hidden_title_condition(alias="gu"):
    prefixes = _hidden_title_prefixes()
    clauses = []
    for prefix in prefixes:
        safe_prefix = prefix.replace("'", "''")
        clauses.append(f"{alias}.title NOT LIKE '{safe_prefix}%%'")
    return " AND ".join(clauses), []


def _is_internal_title(title):
    if not title:
        return False
    return any(
        title.startswith(prefix)
        for prefix in _hidden_title_prefixes()
    )


def _load_history_carrier(kind, source_id):
    title = _history_carrier_title(kind, source_id)
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT update_id, content
            FROM Group_Updates
            WHERE title = %s
            ORDER BY update_id DESC
            LIMIT 1;
            """,
            (title,),
        )
        return cursor.fetchone()


def _store_history_carrier(kind, source_id, author_id, group_id, history):
    title = _history_carrier_title(kind, source_id)
    payload = json.dumps(history, ensure_ascii=False, indent=2)

    carrier = _load_history_carrier(kind, source_id)
    if carrier:
        with get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE Group_Updates
                SET content = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE update_id = %s;
                """,
                (payload, carrier["update_id"]),
            )
            return carrier["update_id"]

    if group_id is None:
        group_id = _resolve_fallback_group_id_for_user(author_id)
    if group_id is None:
        return None

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Group_Updates (group_id, author_id, title, content, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING update_id;
            """,
            (group_id, author_id, title, payload, DRAFT_STATUS),
        )
        row = cursor.fetchone()
        return row["update_id"] if row else None


def _load_history_payload(kind, source_id):
    carrier = _load_history_carrier(kind, source_id)
    if not carrier or not carrier.get("content"):
        return []
    try:
        parsed = json.loads(carrier["content"])
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _encode_attachment_payload(original_filename, mime_type, file_bytes):
    filename = (original_filename or "attachment").encode("utf-8")
    filename_b64 = base64.urlsafe_b64encode(filename).decode("ascii")
    content_b64 = base64.b64encode(file_bytes or b"").decode("ascii")
    safe_mime = mime_type or "application/octet-stream"
    return f"{ATTACHMENT_PAYLOAD_PREFIX}|{filename_b64}|{safe_mime}|{content_b64}"


def _decode_attachment_payload(raw_description):
    if not raw_description:
        return {}
    if not isinstance(raw_description, str):
        return {}
    parts = raw_description.split("|", 3)
    if len(parts) != 4 or parts[0] != ATTACHMENT_PAYLOAD_PREFIX:
        return {}
    try:
        filename = base64.urlsafe_b64decode(parts[1].encode("ascii")).decode("utf-8")
    except Exception:
        filename = "attachment"
    return {
        "filename": filename,
        "mime_type": parts[2] or "application/octet-stream",
        "content_b64": parts[3],
    }


def _knowledge_attachment_carrier_title(entry_id):
    return f"{KNOWLEDGE_ATTACHMENT_TITLE_PREFIX}{entry_id}"


def _extract_entry_id_from_carrier_title(title):
    if not title or not title.startswith(KNOWLEDGE_ATTACHMENT_TITLE_PREFIX):
        return None
    try:
        return int(title[len(KNOWLEDGE_ATTACHMENT_TITLE_PREFIX):])
    except (TypeError, ValueError):
        return None


def _resolve_fallback_group_id_for_user(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT group_id
            FROM Group_Members
            WHERE user_id = %s AND membership_status = 'Active'
            ORDER BY id ASC
            LIMIT 1;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return row["group_id"]

        cursor.execute(
            """
            SELECT group_id
            FROM Groups
            ORDER BY group_id ASC
            LIMIT 1;
            """
        )
        row = cursor.fetchone()
        return row["group_id"] if row else None


def _get_or_create_knowledge_attachment_carrier_update(entry_id, author_id):
    title = _knowledge_attachment_carrier_title(entry_id)
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT update_id
            FROM Group_Updates
            WHERE author_id = %s
              AND title = %s
              AND status = %s
            ORDER BY update_id DESC
            LIMIT 1;
            """,
            (author_id, title, DRAFT_STATUS),
        )
        row = cursor.fetchone()
        if row:
            return row["update_id"]

    group_id = _resolve_fallback_group_id_for_user(author_id)
    if not group_id:
        return None

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Group_Updates (group_id, author_id, title, content, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING update_id;
            """,
            (group_id, author_id, title, "knowledge attachment carrier", DRAFT_STATUS),
        )
        row = cursor.fetchone()
        return row["update_id"] if row else None


def get_knowledge_categories():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT category_id, name
            FROM Knowledge_Categories
            ORDER BY name ASC;
            """
        )
        return cursor.fetchall()


def add_knowledge_category(name):
    """Add a new knowledge category. Raises ValueError on duplicate (case-insensitive)."""
    if not name or not name.strip():
        raise ValueError("empty_name")
    name_clean = name.strip()
    with get_cursor() as cursor:
        # check duplicate case-insensitive
        cursor.execute(
            "SELECT category_id FROM Knowledge_Categories WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s)) LIMIT 1;",
            (name_clean,)
        )
        if cursor.fetchone():
            raise ValueError("duplicate_category")
        cursor.execute(
            "INSERT INTO Knowledge_Categories (name) VALUES (%s) RETURNING category_id;",
            (name_clean,)
        )
        row = cursor.fetchone()
        return row["category_id"] if row else None


def update_knowledge_category(category_id, new_name):
    """Rename a knowledge category. Raises ValueError on duplicate or invalid id."""
    if not new_name or not new_name.strip():
        raise ValueError("empty_name")
    new_clean = new_name.strip()
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT category_id FROM Knowledge_Categories WHERE category_id = %s LIMIT 1;",
            (category_id,)
        )
        if not cursor.fetchone():
            raise ValueError("not_found")
        # check duplicate excluding current
        cursor.execute(
            "SELECT category_id FROM Knowledge_Categories WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s)) AND category_id != %s LIMIT 1;",
            (new_clean, category_id),
        )
        if cursor.fetchone():
            raise ValueError("duplicate_category")
        cursor.execute(
            "UPDATE Knowledge_Categories SET name = %s WHERE category_id = %s;",
            (new_clean, category_id),
        )
        return True


def is_knowledge_category_in_use(category_id):
    """Return True if any Knowledge_Entries reference this category."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM Knowledge_Entries WHERE category_id = %s LIMIT 1;",
            (category_id,)
        )
        return cursor.fetchone() is not None


def delete_knowledge_category(category_id):
    """Delete a knowledge category. Returns True if deleted; raises ValueError if in use."""
    if is_knowledge_category_in_use(category_id):
        raise ValueError("category_in_use")
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Knowledge_Categories WHERE category_id = %s;", (category_id,))
        return cursor.rowcount > 0


def get_knowledge_entries(current_user_id=None, limit=30, category_id=None, q=None):
    """Return published knowledge entries with optional category and keyword filtering.

    Parameters:
    - category_id: integer to filter by Knowledge_Categories.category_id
    - q: keyword string to search in title or content (case-insensitive)
    """
    params = [PUBLISHED_STATUS]
    where_clauses = ["ke.status = %s"]

    if category_id:
        where_clauses.append("ke.category_id = %s")
        params.append(category_id)

    if q:
        # Use ILIKE for case-insensitive match; match against title or content
        where_clauses.append("(ke.title ILIKE %s OR ke.content ILIKE %s)")
        like_q = f"%{q}%"
        params.extend([like_q, like_q])

    where_sql = " AND ".join(where_clauses)

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ke.entry_id,
                ke.category_id,
                kc.name AS category_name,
                ke.title,
                ke.content,
                ke.image_url,
                ke.author_id,
                ke.approved_by,
                ke.status,
                ke.is_featured,
                ke.created_at,
                ke.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE(NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.last_name, '')), ''), a.username, 'Unknown') AS approver_name
            FROM Knowledge_Entries ke
            LEFT JOIN Knowledge_Categories kc ON kc.category_id = ke.category_id
            LEFT JOIN Users u ON u.user_id = ke.author_id
            LEFT JOIN Users a ON a.user_id = ke.approved_by
            WHERE {where_sql}
            ORDER BY ke.is_featured DESC, ke.created_at DESC
            LIMIT %s;
            """,
            tuple(params + [limit]),
        )
        return cursor.fetchall()


def get_featured_knowledge_entries(limit=6):
    """Return published knowledge entries that are marked as featured."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ke.entry_id,
                ke.category_id,
                kc.name AS category_name,
                ke.title,
                ke.content,
                ke.image_url,
                ke.author_id,
                ke.approved_by,
                ke.status,
                ke.is_featured,
                ke.created_at,
                ke.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE(NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.last_name, '')), ''), a.username, 'Unknown') AS approver_name
            FROM Knowledge_Entries ke
            LEFT JOIN Knowledge_Categories kc ON kc.category_id = ke.category_id
            LEFT JOIN Users u ON u.user_id = ke.author_id
            LEFT JOIN Users a ON a.user_id = ke.approved_by
            WHERE ke.status = %s AND ke.is_featured = TRUE
            ORDER BY ke.updated_at DESC
            LIMIT %s;
            """,
            (PUBLISHED_STATUS, limit),
        )
        return cursor.fetchall()


def get_knowledge_entry_by_id(entry_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ke.entry_id,
                ke.category_id,
                kc.name AS category_name,
                ke.title,
                ke.content,
                ke.image_url,
                ke.author_id,
                ke.approved_by,
                ke.status,
                ke.is_featured,
                ke.created_at,
                ke.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE(NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.last_name, '')), ''), a.username, 'Unknown') AS approver_name
            FROM Knowledge_Entries ke
            LEFT JOIN Knowledge_Categories kc ON kc.category_id = ke.category_id
            LEFT JOIN Users u ON u.user_id = ke.author_id
            LEFT JOIN Users a ON a.user_id = ke.approved_by
            WHERE ke.entry_id = %s;
            """,
            (entry_id,),
        )
        return cursor.fetchone()


def get_user_knowledge_entries(author_id, statuses=None, limit=20):
    params = [author_id]
    status_clause = ""
    if statuses:
        status_clause = " AND ke.status = ANY(%s)"
        params.append(list(statuses))

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ke.entry_id,
                ke.category_id,
                kc.name AS category_name,
                ke.title,
                ke.content,
                ke.image_url,
                ke.author_id,
                ke.approved_by,
                ke.status,
                ke.is_featured,
                ke.created_at,
                ke.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE(NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.last_name, '')), ''), a.username, 'Unknown') AS approver_name
            FROM Knowledge_Entries ke
            LEFT JOIN Knowledge_Categories kc ON kc.category_id = ke.category_id
            LEFT JOIN Users u ON u.user_id = ke.author_id
            LEFT JOIN Users a ON a.user_id = ke.approved_by
            WHERE ke.author_id = %s
            {status_clause}
            ORDER BY ke.updated_at DESC, ke.created_at DESC
            LIMIT %s;
            """,
            tuple(params + [limit]),
        )
        return cursor.fetchall()


def get_pending_knowledge_entries(can_review=False, limit=20):
    if not can_review:
        return []

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ke.entry_id,
                ke.category_id,
                kc.name AS category_name,
                ke.title,
                ke.content,
                ke.image_url,
                ke.author_id,
                ke.approved_by,
                ke.status,
                ke.is_featured,
                ke.created_at,
                ke.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE(NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.last_name, '')), ''), a.username, 'Unknown') AS approver_name
            FROM Knowledge_Entries ke
            LEFT JOIN Knowledge_Categories kc ON kc.category_id = ke.category_id
            LEFT JOIN Users u ON u.user_id = ke.author_id
            LEFT JOIN Users a ON a.user_id = ke.approved_by
            WHERE ke.status = %s
            ORDER BY ke.updated_at DESC, ke.created_at DESC
            LIMIT %s;
            """,
            (PENDING_STATUS, limit),
        )
        return cursor.fetchall()


def create_knowledge_entry(author_id, title, content, category_id=None, image_url=None, status=PUBLISHED_STATUS):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Knowledge_Entries (category_id, author_id, title, content, image_url, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING entry_id;
            """,
            (category_id, author_id, title, content, image_url, status),
        )
        row = cursor.fetchone()
        return row["entry_id"] if row else None


def update_knowledge_entry(entry_id, author_id, title, content, category_id=None, image_url=None, status=None):
    # save previous version to edit history before updating
    prev = get_knowledge_entry_by_id(entry_id)
    if prev:
        try:
            author = user_repository.get_user_by_id(author_id)
            editor_name = None
            if author:
                editor_name = (
                    (author.get('first_name') or '') + ' ' + (author.get('last_name') or '')
                ).strip() or author.get('username')
        except Exception:
            editor_name = None
        try:
            # pass previous version number if available
            save_knowledge_entry_edit(entry_id, author_id, editor_name, prev.get('title'), prev.get('content'), prev.get('version_number'))
        except Exception:
            # do not fail update if history save fails
            pass

    with get_cursor() as cursor:
        params = [category_id, title, content, image_url]
        status_clause = ""
        if status:
            status_clause = ", status = %s"
            params.append(status)

        cursor.execute(
            """
            UPDATE Knowledge_Entries
            SET category_id = %s,
                title = %s,
                content = %s,
                image_url = %s,
                version_number = COALESCE(version_number, 1) + 1,
                updated_at = CURRENT_TIMESTAMP
            {status_clause}
            WHERE entry_id = %s
            RETURNING entry_id;
            """.format(status_clause=status_clause),
            tuple(params + [entry_id]),
        )
        row = cursor.fetchone()
        return row["entry_id"] if row else None


def approve_knowledge_entry(entry_id, approver_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Knowledge_Entries
            SET status = %s,
                approved_by = %s,
                updated_at = CURRENT_TIMESTAMP,
                version_number = COALESCE(version_number, 1) + 1
            WHERE entry_id = %s
            RETURNING entry_id;
            """,
            (PUBLISHED_STATUS, approver_id, entry_id),
        )
        row = cursor.fetchone()
        return row["entry_id"] if row else None


def return_knowledge_entry_to_draft(entry_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Knowledge_Entries
            SET status = %s,
                approved_by = NULL,
                updated_at = CURRENT_TIMESTAMP,
                version_number = COALESCE(version_number, 1) + 1
            WHERE entry_id = %s
            RETURNING entry_id;
            """,
            (DRAFT_STATUS, entry_id),
        )
        row = cursor.fetchone()
        return row["entry_id"] if row else None


def delete_knowledge_entry(entry_id):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Knowledge_Entries WHERE entry_id = %s;", (entry_id,))
        return cursor.rowcount > 0


def save_knowledge_entry_edit(entry_id, editor_id, editor_name, previous_title, previous_content, previous_version_number=None):
    source_entry = get_knowledge_entry_by_id(entry_id)
    if not source_entry:
        return False
    history = _load_history_payload("knowledge", entry_id)

    entry = {
        'version_number': previous_version_number if previous_version_number is not None else (len(history) + 1),
        'editor_id': editor_id,
        'editor_name': editor_name,
        'previous_title': previous_title,
        'previous_content': previous_content,
        'edited_at': _utc_now_iso(),
    }

    history.append(entry)
    group_id = _resolve_fallback_group_id_for_user(editor_id)
    _store_history_carrier("knowledge", entry_id, editor_id, group_id, history)
    return True


def get_knowledge_entry_edit_history(entry_id):
    return _load_history_payload("knowledge", entry_id)


def set_knowledge_entry_featured(entry_id, is_featured=True):
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Knowledge_Entries
            SET is_featured = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE entry_id = %s
            RETURNING entry_id;
            """,
            (is_featured, entry_id),
        )
        row = cursor.fetchone()
        return row["entry_id"] if row else None


def get_global_posts(current_user_id, limit=30):
    """Return published hub posts across all groups with summary interaction counts."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                gu.update_id AS entry_id,
                gu.group_id,
                gu.title,
                gu.content,
                gu.author_id,
                gu.created_at,
                gu.updated_at,
                g.name AS group_name,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE((SELECT COUNT(*) FROM Update_Likes ul WHERE ul.update_id = gu.update_id), 0) AS likes_count,
                COALESCE((SELECT COUNT(*) FROM Update_Comments uc WHERE uc.update_id = gu.update_id), 0) AS comments_count,
                EXISTS(
                    SELECT 1
                    FROM Update_Likes ul
                    WHERE ul.update_id = gu.update_id AND ul.user_id = %s
                ) AS user_liked
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE gu.status = %s
            ORDER BY gu.created_at DESC
            LIMIT %s;
            """,
            (current_user_id, PUBLISHED_STATUS, limit),
        )
        rows = cursor.fetchall()

    return [row for row in rows if not _is_internal_title(row.get("title"))]


def get_global_comments_for_entries(entry_ids, current_user_id=None):
    """Return global post comments grouped by entry id."""
    if not entry_ids:
        return {}

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                uc.comment_id,
                uc.update_id AS entry_id,
                uc.user_id,
                uc.comment_text,
                uc.created_at,
                COALESCE((SELECT COUNT(*) FROM Comments_Likes cl WHERE cl.comment_id = uc.comment_id), 0) AS likes_count,
                EXISTS(
                    SELECT 1
                    FROM Comments_Likes cl
                    WHERE cl.comment_id = uc.comment_id AND cl.user_id = %s
                ) AS user_liked,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name
            FROM Update_Comments uc
            LEFT JOIN Users u ON u.user_id = uc.user_id
            WHERE uc.update_id = ANY(%s)
            ORDER BY uc.created_at ASC;
            """,
            (current_user_id, entry_ids),
        )
        rows = cursor.fetchall()

    grouped = {}
    for row in rows:
        grouped.setdefault(row["entry_id"], []).append(row)
    return grouped


def create_global_post(author_id, title, content):
    raise NotImplementedError("Global hub posts must be created through create_group_notice with a group_id.")


def create_global_post_in_group(group_id, author_id, title, content, status=PUBLISHED_STATUS):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Group_Updates (group_id, author_id, title, content, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING update_id;
            """,
            (group_id, author_id, title, content, status),
        )
        row = cursor.fetchone()
        return row["update_id"] if row else None


def update_global_post(update_id, author_id, group_id, title, content, status):
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Group_Updates
            SET group_id = %s,
                title = %s,
                content = %s,
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE update_id = %s AND author_id = %s
            RETURNING update_id;
            """,
            (group_id, title, content, status, update_id, author_id),
        )
        row = cursor.fetchone()
        return row["update_id"] if row else None


def get_content_sharing_by_id(update_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                gu.update_id,
                gu.group_id,
                gu.author_id,
                gu.title,
                gu.content,
                gu.status,
                gu.created_at,
                gu.updated_at,
                g.name AS group_name,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE gu.update_id = %s;
            """,
            (update_id,),
        )
        row = cursor.fetchone()
        if row and _is_internal_title(row.get("title")):
            return None
        return row


def get_user_content_sharing(author_id, group_id=None, limit=20):
    params = [author_id, [DRAFT_STATUS, PENDING_STATUS]]
    group_filter = ""
    if group_id:
        group_filter = " AND gu.group_id = %s"
        params.append(group_id)

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                gu.update_id,
                gu.group_id,
                gu.author_id,
                gu.title,
                gu.content,
                gu.status,
                gu.created_at,
                gu.updated_at,
                g.name AS group_name,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                0 AS attachments_count
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE gu.author_id = %s
              AND gu.status = ANY(%s)
              {group_filter}
            ORDER BY gu.updated_at DESC, gu.created_at DESC
            LIMIT %s;
            """,
            tuple(params + [limit]),
        )
        rows = cursor.fetchall()

        return [row for row in rows if not _is_internal_title(row.get("title"))]


def get_pending_content_reviews(group_id=None, is_admin=False, limit=20):
    params = [PENDING_STATUS]
    group_filter = ""
    if group_id:
        group_filter = " AND gu.group_id = %s"
        params.append(group_id)
    elif not is_admin:
        return []

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                gu.update_id,
                gu.group_id,
                gu.author_id,
                gu.title,
                gu.content,
                gu.status,
                gu.created_at,
                gu.updated_at,
                g.name AS group_name,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                0 AS attachments_count
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE gu.status = %s
              {group_filter}
            ORDER BY gu.updated_at DESC, gu.created_at DESC
            LIMIT %s;
            """,
            tuple(params + [limit]),
        )
        rows = cursor.fetchall()

        return [row for row in rows if not _is_internal_title(row.get("title"))]


def get_update_attachments(update_ids):
    if not update_ids:
        return {}

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                attachment_id,
                update_id,
                file_type,
                description,
                file_url
            FROM Update_Attachments
            WHERE update_id = ANY(%s)
            ORDER BY attachment_id ASC;
            """,
            (update_ids,),
        )
        rows = cursor.fetchall()

    grouped = {}
    for row in rows:
        payload = _decode_attachment_payload(row["description"])
        filename = payload.get("filename") or row["file_url"] or f"attachment_{row['attachment_id']}"
        grouped.setdefault(row["update_id"], []).append(
            {
                "attachment_id": row["attachment_id"],
                "update_id": row["update_id"],
                "file_url": f"/knowledge-hub/attachment/update/{row['attachment_id']}",
                "file_type": row["file_type"],
                "description": filename,
            }
        )
    return grouped


def get_knowledge_attachments(entry_ids):
    if not entry_ids:
        return {}

    titles = [_knowledge_attachment_carrier_title(entry_id) for entry_id in entry_ids]
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT update_id, title
            FROM Group_Updates
            WHERE title = ANY(%s)
              AND status = %s;
            """,
            (titles, DRAFT_STATUS),
        )
        carriers = cursor.fetchall()

    update_to_entry = {}
    update_ids = []
    for row in carriers:
        entry_id = _extract_entry_id_from_carrier_title(row.get("title"))
        if not entry_id:
            continue
        update_to_entry[row["update_id"]] = entry_id
        update_ids.append(row["update_id"])

    if not update_ids:
        return {}

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                attachment_id,
                update_id,
                file_type,
                description,
                file_url
            FROM Update_Attachments
            WHERE update_id = ANY(%s)
            ORDER BY attachment_id ASC;
            """,
            (update_ids,),
        )
        rows = cursor.fetchall()

    grouped = {}
    for row in rows:
        entry_id = update_to_entry.get(row["update_id"])
        if not entry_id:
            continue
        payload = _decode_attachment_payload(row["description"])
        filename = payload.get("filename") or row["file_url"] or f"attachment_{row['attachment_id']}"
        grouped.setdefault(entry_id, []).append(
            {
                "attachment_id": row["attachment_id"],
                "entry_id": entry_id,
                "file_url": f"/knowledge-hub/attachment/knowledge/{row['attachment_id']}",
                "file_type": row["file_type"],
                "description": filename,
            }
        )
    return grouped


def add_update_attachment(update_id, file_type, original_filename, file_bytes, mime_type=None, description=None):
    payload_text = _encode_attachment_payload(original_filename, mime_type, file_bytes)
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Update_Attachments (
                update_id,
                file_url,
                file_type,
                description
            )
            VALUES (%s, %s, %s, %s)
            RETURNING attachment_id;
            """,
            (
                update_id,
                original_filename or "attachment",
                file_type,
                payload_text,
            ),
        )
        row = cursor.fetchone()
        return row["attachment_id"] if row else None


def add_knowledge_attachment(entry_id, file_type, original_filename, file_bytes, mime_type=None, description=None):
    entry = get_knowledge_entry_by_id(entry_id)
    if not entry:
        return None
    carrier_update_id = _get_or_create_knowledge_attachment_carrier_update(entry_id, entry["author_id"])
    if not carrier_update_id:
        return None
    return add_update_attachment(
        carrier_update_id,
        file_type,
        original_filename,
        file_bytes,
        mime_type=mime_type,
        description=description,
    )


def delete_knowledge_attachment(attachment_id, entry_id, author_id):
    carrier_title = _knowledge_attachment_carrier_title(entry_id)
    with get_cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM Update_Attachments ua
            USING Group_Updates gu
            WHERE ua.attachment_id = %s
              AND gu.update_id = ua.update_id
              AND gu.title = %s
              AND gu.author_id = %s;
            """,
            (attachment_id, carrier_title, author_id),
        )
        return cursor.rowcount > 0


def get_update_attachment_by_id(attachment_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ua.attachment_id,
                ua.update_id,
                ua.file_type,
                ua.file_url,
                ua.description,
                gu.group_id,
                gu.author_id,
                gu.status
            FROM Update_Attachments ua
            JOIN Group_Updates gu ON gu.update_id = ua.update_id
            WHERE ua.attachment_id = %s;
            """,
            (attachment_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

    payload = _decode_attachment_payload(row.get("description"))
    content_b64 = payload.get("content_b64")
    file_bytes = b""
    if content_b64:
        try:
            file_bytes = base64.b64decode(content_b64.encode("ascii"), validate=False)
        except Exception:
            file_bytes = b""

    row["original_filename"] = payload.get("filename") or row.get("file_url") or f"attachment_{attachment_id}"
    row["mime_type"] = payload.get("mime_type") or "application/octet-stream"
    row["file_content"] = file_bytes
    return row


def get_knowledge_attachment_by_id(attachment_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ua.attachment_id,
                ua.update_id,
                ua.file_type,
                ua.file_url,
                ua.description,
                gu.title,
                gu.author_id
            FROM Update_Attachments ua
            JOIN Group_Updates gu ON gu.update_id = ua.update_id
            WHERE ua.attachment_id = %s
              AND gu.title LIKE %s;
            """,
            (attachment_id, f"{KNOWLEDGE_ATTACHMENT_TITLE_PREFIX}%"),
        )
        row = cursor.fetchone()
        if not row:
            return None

    entry_id = _extract_entry_id_from_carrier_title(row.get("title"))
    if not entry_id:
        return None
    entry = get_knowledge_entry_by_id(entry_id)
    if not entry:
        return None

    payload = _decode_attachment_payload(row.get("description"))
    content_b64 = payload.get("content_b64")
    file_bytes = b""
    if content_b64:
        try:
            file_bytes = base64.b64decode(content_b64.encode("ascii"), validate=False)
        except Exception:
            file_bytes = b""

    row["entry_id"] = entry_id
    row["status"] = entry["status"]
    row["original_filename"] = payload.get("filename") or row.get("file_url") or f"attachment_{attachment_id}"
    row["mime_type"] = payload.get("mime_type") or "application/octet-stream"
    row["file_content"] = file_bytes
    return row


def add_global_comment(entry_id, user_id, comment_text):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Update_Comments (update_id, user_id, comment_text)
            VALUES (%s, %s, %s)
            RETURNING comment_id;
            """,
            (entry_id, user_id, comment_text),
        )
        row = cursor.fetchone()
        return row["comment_id"] if row else None


def get_global_post_by_id(entry_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT update_id AS entry_id, group_id, author_id, status
            FROM Group_Updates
            WHERE update_id = %s;
            """,
            (entry_id,),
        )
        return cursor.fetchone()


def get_global_comment_by_id(comment_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT uc.comment_id, uc.update_id AS entry_id, uc.user_id, gu.group_id
            FROM Update_Comments uc
            JOIN Group_Updates gu ON gu.update_id = uc.update_id
            WHERE comment_id = %s;
            """,
            (comment_id,),
        )
        return cursor.fetchone()


def delete_global_post(entry_id):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Group_Updates WHERE update_id = %s;", (entry_id,))
        return cursor.rowcount > 0


def delete_global_comment(comment_id):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Update_Comments WHERE comment_id = %s;", (comment_id,))
        return cursor.rowcount > 0


def toggle_global_like(entry_id, user_id):
    """Toggle like status for a global post. Returns True if liked after operation."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM Update_Likes
            WHERE update_id = %s AND user_id = %s;
            """,
            (entry_id, user_id),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                DELETE FROM Update_Likes
                WHERE update_id = %s AND user_id = %s;
                """,
                (entry_id, user_id),
            )
            return False

        cursor.execute(
            """
            INSERT INTO Update_Likes (update_id, user_id)
            VALUES (%s, %s);
            """,
            (entry_id, user_id),
        )
        return True


def get_group_notice_by_id(update_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                update_id,
                group_id,
                author_id,
                title,
                content,
                status,
                created_at,
                updated_at
            FROM Group_Updates
            WHERE update_id = %s;
            """,
            (update_id,),
        )
        row = cursor.fetchone()
        if row and _is_internal_title(row.get("title")):
            return None
        return row


def get_group_notice_detail(update_id, current_user_id=None):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                gu.update_id,
                gu.group_id,
                g.name AS group_name,
                gu.author_id,
                gu.title,
                gu.content,
                gu.created_at,
                gu.updated_at,
                gu.status,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE((SELECT COUNT(*) FROM Update_Likes ul WHERE ul.update_id = gu.update_id), 0) AS likes_count,
                COALESCE((SELECT COUNT(*) FROM Update_Comments uc WHERE uc.update_id = gu.update_id), 0) AS comments_count,
                EXISTS(
                    SELECT 1
                    FROM Update_Likes ul
                    WHERE ul.update_id = gu.update_id AND ul.user_id = %s
                ) AS user_liked
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE gu.update_id = %s;
            """,
            (current_user_id, update_id),
        )
        row = cursor.fetchone()
        if row and _is_internal_title(row.get("title")):
            return None
        return row


def get_group_notices(group_id=None, current_user_id=None, is_admin=False, limit=30):
    """Return group updates. Admin can query across groups by leaving group_id as None."""
    params = [current_user_id, PUBLISHED_STATUS]
    where_clauses = ["gu.status = %s"]

    if group_id:
        where_clauses.append("gu.group_id = %s")
        params.append(group_id)
    elif not is_admin:
        # Non-admin users must always be scoped to a selected group.
        return []

    where_sql = " AND ".join(where_clauses)

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                gu.update_id,
                gu.group_id,
                g.name AS group_name,
                gu.author_id,
                gu.title,
                gu.content,
                gu.created_at,
                gu.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name,
                COALESCE((SELECT COUNT(*) FROM Update_Likes ul WHERE ul.update_id = gu.update_id), 0) AS likes_count,
                COALESCE((SELECT COUNT(*) FROM Update_Comments uc WHERE uc.update_id = gu.update_id), 0) AS comments_count,
                EXISTS(
                    SELECT 1
                    FROM Update_Likes ul
                    WHERE ul.update_id = gu.update_id AND ul.user_id = %s
                ) AS user_liked
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE {where_sql}
            ORDER BY gu.created_at DESC
            LIMIT %s;
            """.format(where_sql=where_sql),
            tuple(params + [limit]),
        )
        rows = cursor.fetchall()

    return [row for row in rows if not _is_internal_title(row.get("title"))]


def get_user_group_notice_drafts(author_id, group_id=None, limit=20):
    params = [author_id, DRAFT_STATUS]
    group_filter = ""
    if group_id:
        group_filter = " AND gu.group_id = %s"
        params.append(group_id)

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                gu.update_id,
                gu.group_id,
                g.name AS group_name,
                gu.author_id,
                gu.title,
                gu.content,
                gu.status,
                gu.created_at,
                gu.updated_at,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name
            FROM Group_Updates gu
            JOIN Groups g ON g.group_id = gu.group_id
            LEFT JOIN Users u ON u.user_id = gu.author_id
            WHERE gu.author_id = %s
              AND gu.status = %s
              {group_filter}
            ORDER BY gu.updated_at DESC, gu.created_at DESC
            LIMIT %s;
            """,
            tuple(params + [limit]),
        )
        rows = cursor.fetchall()

        return [row for row in rows if not _is_internal_title(row.get("title"))]


def get_group_notice_comments_for_updates(update_ids, current_user_id=None):
    if not update_ids:
        return {}

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                uc.comment_id,
                uc.update_id,
                uc.user_id,
                uc.comment_text,
                uc.created_at,
                COALESCE((SELECT COUNT(*) FROM Comments_Likes cl WHERE cl.comment_id = uc.comment_id), 0) AS likes_count,
                EXISTS(
                    SELECT 1
                    FROM Comments_Likes cl
                    WHERE cl.comment_id = uc.comment_id AND cl.user_id = %s
                ) AS user_liked,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, 'Unknown') AS author_name
            FROM Update_Comments uc
            LEFT JOIN Users u ON u.user_id = uc.user_id
            WHERE uc.update_id = ANY(%s)
            ORDER BY uc.created_at ASC;
            """,
            (current_user_id, update_ids),
        )
        rows = cursor.fetchall()

    grouped = {}
    for row in rows:
        grouped.setdefault(row["update_id"], []).append(row)
    return grouped


def create_group_notice(group_id, author_id, title, content, status=PUBLISHED_STATUS):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Group_Updates (group_id, author_id, title, content, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING update_id;
            """,
            (group_id, author_id, title, content, status),
        )
        row = cursor.fetchone()
        return row["update_id"] if row else None


def add_group_notice_comment(update_id, user_id, comment_text):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Update_Comments (update_id, user_id, comment_text)
            VALUES (%s, %s, %s)
            RETURNING comment_id;
            """,
            (update_id, user_id, comment_text),
        )
        row = cursor.fetchone()
        return row["comment_id"] if row else None


def get_group_comment_by_id(comment_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT uc.comment_id, uc.update_id, uc.user_id, gu.group_id, uc.comment_text
            FROM Update_Comments uc
            JOIN Group_Updates gu ON gu.update_id = uc.update_id
            WHERE uc.comment_id = %s;
            """,
            (comment_id,),
        )
        return cursor.fetchone()


def delete_group_notice(update_id):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Group_Updates WHERE update_id = %s;", (update_id,))
        return cursor.rowcount > 0


def log_deleted_comment(original_comment_id, update_id, author_id, moderator_id, content_snapshot, deletion_reason):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Deleted_Comments_Log (
                original_comment_id,
                update_id,
                author_id,
                moderator_id,
                content_snapshot,
                deletion_reason,
                deleted_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """,
            (
                original_comment_id,
                update_id,
                author_id,
                moderator_id,
                content_snapshot,
                deletion_reason,
            ),
        )
        return cursor.rowcount > 0


def update_group_notice(update_id, user_id, group_id, title, content, status=None):
    # save previous version to edit history before updating
    prev = get_group_notice_by_id(update_id)
    if prev:
        try:
            author = user_repository.get_user_by_id(user_id)
            editor_name = None
            if author:
                editor_name = (
                    (author.get('first_name') or '') + ' ' + (author.get('last_name') or '')
                ).strip() or author.get('username')
        except Exception:
            editor_name = None
        try:
            save_group_notice_edit(update_id, user_id, editor_name, prev.get('title'), prev.get('content'))
        except Exception:
            # don't fail update if history save fails
            pass

    with get_cursor() as cursor:
        params = [title, content]
        status_clause = ""
        if status:
            status_clause = ", status = %s"
            params.append(status)
        cursor.execute(
            """
            UPDATE Group_Updates
            SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP
            {status_clause}
            WHERE update_id = %s;
            """.format(status_clause=status_clause),
            tuple(params + [update_id]),
        )
        return cursor.rowcount > 0


def save_group_notice_edit(update_id, editor_id, editor_name, previous_title, previous_content):
    notice = get_group_notice_by_id(update_id)
    if not notice:
        return False
    history = _load_history_payload("notice", update_id)

    entry = {
        'version_number': len(history) + 1,
        'editor_id': editor_id,
        'editor_name': editor_name,
        'previous_title': previous_title,
        'previous_content': previous_content,
        'edited_at': _utc_now_iso(),
    }

    history.append(entry)
    _store_history_carrier("notice", update_id, editor_id, notice.get("group_id"), history)
    return True


def get_group_notice_edit_history(update_id):
    return _load_history_payload("notice", update_id)


def get_edit_histories_for_updates(update_ids):
    result = {}
    if not update_ids:
        return result
    for uid in update_ids:
        try:
            result[uid] = get_group_notice_edit_history(uid)
        except Exception:
            result[uid] = []
    return result


def delete_group_notice_comment(comment_id, moderator_id, deletion_reason):
    deletion_reason = (deletion_reason or "").strip()
    if not deletion_reason:
        return False

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                uc.comment_id,
                uc.update_id,
                uc.user_id,
                uc.comment_text
            FROM Update_Comments uc
            WHERE uc.comment_id = %s;
            """,
            (comment_id,),
        )
        comment = cursor.fetchone()
        if not comment:
            return False

        log_deleted_comment(
            comment["comment_id"],
            comment["update_id"],
            comment["user_id"],
            moderator_id,
            comment["comment_text"],
            deletion_reason,
        )

        cursor.execute("DELETE FROM Update_Comments WHERE comment_id = %s;", (comment_id,))
        return cursor.rowcount > 0


def toggle_group_comment_like(comment_id, user_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM Comments_Likes
            WHERE comment_id = %s AND user_id = %s;
            """,
            (comment_id, user_id),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                DELETE FROM Comments_Likes
                WHERE comment_id = %s AND user_id = %s;
                """,
                (comment_id, user_id),
            )
            return False

        cursor.execute(
            """
            INSERT INTO Comments_Likes (comment_id, user_id)
            VALUES (%s, %s);
            """,
            (comment_id, user_id),
        )
        return True


def toggle_group_notice_like(update_id, user_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM Update_Likes
            WHERE update_id = %s AND user_id = %s;
            """,
            (update_id, user_id),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                DELETE FROM Update_Likes
                WHERE update_id = %s AND user_id = %s;
                """,
                (update_id, user_id),
            )
            return False

        cursor.execute(
            """
            INSERT INTO Update_Likes (update_id, user_id)
            VALUES (%s, %s);
            """,
            (update_id, user_id),
        )
        return True


def get_active_membership(user_id, group_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT role, membership_status
            FROM Group_Members
            WHERE user_id = %s AND group_id = %s;
            """,
            (user_id, group_id),
        )
        return cursor.fetchone()


def is_active_group_member(user_id, group_id):
    membership = get_active_membership(user_id, group_id)
    return bool(membership and membership["membership_status"] == "Active")


def is_group_coordinator(user_id, group_id):
    membership = get_active_membership(user_id, group_id)
    if not membership or membership["membership_status"] != "Active":
        return False
    return membership["role"] in COORDINATOR_ROLES
