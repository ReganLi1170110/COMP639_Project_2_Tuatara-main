import json
import os

# Simple file-based settings store to avoid DB changes.
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'group_settings.json')


def _ensure_store():
    folder = os.path.dirname(SETTINGS_PATH)
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f)


def _read_store():
    _ensure_store()
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def _write_store(data):
    _ensure_store()
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def get_group_setting(group_id, key, default=None):
    data = _read_store()
    gid = str(group_id)
    if gid in data and key in data[gid]:
        return data[gid][key]
    return default


def set_group_setting(group_id, key, value):
    data = _read_store()
    gid = str(group_id)
    if gid not in data:
        data[gid] = {}
    data[gid][key] = value
    _write_store(data)


def get_site_setting(key, default=None):
    """Retrieve a global/site-wide setting by key."""
    data = _read_store()
    if 'site' in data and key in data['site']:
        return data['site'][key]
    return default


def set_site_setting(key, value):
    """Save a global/site-wide setting."""
    data = _read_store()
    if 'site' not in data:
        data['site'] = {}
    data['site'][key] = value
    _write_store(data)

