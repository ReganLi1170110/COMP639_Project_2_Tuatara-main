"""
Theme Routes – US 2.1 to 2.5, 3.6, 3.7, 3.8
Handles: theme gallery, theme editor (colours/font/layout/images),
preview (client-side), save, rollback, platform-default (Admin).

All routes are ADDITIVE – no existing route is modified.
"""

import os
import json
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename

from app import flask_app as app
from app.repository import theme_repository
import app.utils as utils

# ─── Helpers ─────────────────────────────────────────────────────────────────

ALLOWED_IMG = {'jpg', 'jpeg', 'png'}
MAX_IMG_BYTES = 2 * 1024 * 1024  # 2 MB

THEME_UPLOAD_FOLDER = os.path.join(
    app.config['UPLOAD_FOLDER'], 'themes'
)

FONT_OPTIONS = [
    ("system",    "Default (System UI)",  "system-ui, -apple-system, sans-serif"),
    ("serif",     "Serif",                "Georgia, 'Times New Roman', serif"),
    ("mono",      "Monospace",            "Consolas, 'Courier New', monospace"),
    ("rounded",   "Rounded / Friendly",   "'Trebuchet MS', Tahoma, sans-serif"),
    ("elegant",   "Elegant",              "Palatino, 'Book Antiqua', serif"),
]

LAYOUT_OPTIONS = [
    ("centered",  "Centred",  "Single-column content centred on the page"),
    ("sidebar",   "Sidebar",  "Left navigation with right content area"),
    ("grid",      "Grid",     "Card-based grid layout with wider container"),
]

# Three built-in pre-made themes (used as gallery defaults when DB is empty)
DEFAULT_PREMADE = [
    {
        "theme_name": "Forest Canopy",
        "emoji": "🌿",
        "settings": {
            "colors": {"primary": "#2D5A27", "secondary": "#E8F5BD",
                       "background": "#F9FAF8", "button": "#2D5A27"},
            "visuals": {"font": "system", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "centered"},
        }
    },
    {
        "theme_name": "Coastal Scrub",
        "emoji": "🌊",
        "settings": {
            "colors": {"primary": "#007E6E", "secondary": "#D7C097",
                       "background": "#FFFFFF", "button": "#007E6E"},
            "visuals": {"font": "serif", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "grid"},
        }
    },
    {
        "theme_name": "Alpine Tussock",
        "emoji": "🏔️",
        "settings": {
            "colors": {"primary": "#8A5F41", "secondary": "#CCD67F",
                       "background": "#F3E4C9", "button": "#8A5F41"},
            "visuals": {"font": "elegant", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "sidebar"},
        }
    },
    {
        "theme_name": "Wetland Dusk",
        "emoji": "🦆",
        "settings": {
            "colors": {"primary": "#5C6BC0", "secondary": "#B3C5F4",
                       "background": "#F0F4FF", "button": "#3949AB"},
            "visuals": {"font": "rounded", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "grid"},
        }
    },
]


def _allowed_img(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG


def _ensure_upload_dir():
    os.makedirs(THEME_UPLOAD_FOLDER, exist_ok=True)


def _save_image(file_field_name, old_path=""):
    """
    Try to save an uploaded image from the given form field.
    Returns (url_path, error_message).  url_path is '' if no upload attempted.
    """
    f = request.files.get(file_field_name)
    if not f or f.filename == '':
        return old_path, None

    if not _allowed_img(f.filename):
        return old_path, f"Only JPG / PNG files are accepted for {file_field_name}."

    # Check size
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > MAX_IMG_BYTES:
        return old_path, f"Image for {file_field_name} exceeds 2 MB limit."

    _ensure_upload_dir()
    filename = secure_filename(f.filename)
    # Prefix with group_id to avoid collisions
    group_id = session.get('group_id', 'admin')
    filename = f"{group_id}_{field_slug(file_field_name)}_{filename}"
    filepath = os.path.join(THEME_UPLOAD_FOLDER, filename)
    f.save(filepath)
    return f"/static/uploads/themes/{filename}", None


def field_slug(name):
    return name.replace('_file', '').replace('_', '-')


def _get_font_css(font_key):
    for k, label, css in FONT_OPTIONS:
        if k == font_key:
            return css
    return FONT_OPTIONS[0][2]


def _settings_from_form():
    """Build settings dict from a submitted theme editor form."""
    return {
        "colors": {
            "primary":    request.form.get("primary_color",    "#2e7d32"),
            "secondary":  request.form.get("secondary_color",  "#a5d6a7"),
            "background": request.form.get("bg_color",         "#f4f8f4"),
            "button":     request.form.get("button_color",     "#2e7d32"),
        },
        "visuals": {
            "font":      request.form.get("font",       "system"),
            "banner":    request.form.get("banner_url", ""),
            "logo":      request.form.get("logo_url",   ""),
            "bg_image":  request.form.get("bg_image_url", ""),
        },
        "layout": {
            "template": request.form.get("layout", "centered"),
        },
    }


def _merge_images_into_settings(settings, old_settings):
    """
    Handle image uploads and merge paths into settings.
    Priority: newly uploaded file > URL typed in form > previously saved path.
    Empty form URL fields do NOT overwrite a previously saved path.
    """
    errors = []
    for field, key in [("banner_file", "banner"), ("logo_file", "logo"),
                       ("bg_image_file", "bg_image")]:
        old_path = ((old_settings or {}).get("visuals", {}).get(key) or "").strip()
        form_url = (settings["visuals"].get(key) or "").strip()

        # Try to save a newly uploaded file first
        upload_path, err = _save_image(field, old_path)
        if err:
            errors.append(err)
            settings["visuals"][key] = old_path  # keep old on error
        elif upload_path and upload_path != old_path:
            # A new file was uploaded
            settings["visuals"][key] = upload_path
        elif form_url:
            # User typed / kept a URL – use it
            settings["visuals"][key] = form_url
        else:
            # Nothing new – preserve whatever was previously saved
            settings["visuals"][key] = old_path
    return errors


# ─── Theme Settings page (gallery + quick actions) ───────────────────────────

@app.route("/theme", methods=["GET"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def theme_settings():
    """
    US 2.1 AC1, AC5, 3.7 AC1/AC4:
    Show the pre-made gallery and the group's current theme.
    Admin sees a platform-wide view; Coordinator sees their group.
    """
    role = session.get("role")
    group_id = session.get("group_id") if role == "Coordinator" else None

    # Gallery: pull from DB, fall back to built-ins
    # Always show the built-in DEFAULT_PREMADE gallery.
    # These 4 themes are hardcoded and never affected by DB operations.
    premade = DEFAULT_PREMADE

    # Current active theme for this group
    active_theme = None
    history = []
    if group_id:
        active_theme = theme_repository.get_active_theme_for_group(group_id)
        if active_theme:
            s = active_theme['settings']
            if isinstance(s, str):
                s = json.loads(s)
            active_theme = dict(active_theme)
            active_theme['settings'] = s
        history = theme_repository.get_theme_history_for_group(group_id, limit=8)

    return render_template(
        "theme_settings.html",
        premade=premade,
        active_theme=active_theme,
        history=history,
        role=role,
        font_options=FONT_OPTIONS,
        layout_options=LAYOUT_OPTIONS,
    )


# ─── Apply a pre-made theme directly ─────────────────────────────────────────

@app.route("/theme/apply-premade", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def theme_apply_premade():
    """US 2.1 AC2: Apply a pre-made theme instantly."""
    role = session.get("role")
    group_id = session.get("group_id") if role == "Coordinator" else None

    theme_source = request.form.get("theme_source")  # 'db' or 'builtin'
    theme_idx    = request.form.get("theme_idx", type=int)
    theme_id_db  = request.form.get("theme_id",  type=int)

    if theme_source == 'db' and theme_id_db:
        db_premade = theme_repository.get_premade_themes()
        target = next((r for r in db_premade if r['theme_id'] == theme_id_db), None)
        if not target:
            flash("Theme not found.", "danger")
            return redirect(url_for("theme_settings"))
        settings = target['settings']
        if isinstance(settings, str):
            settings = json.loads(settings)
        name = target['theme_name']
    else:
        if theme_idx is None or theme_idx < 0 or theme_idx >= len(DEFAULT_PREMADE):
            flash("Invalid theme selection.", "danger")
            return redirect(url_for("theme_settings"))
        t = DEFAULT_PREMADE[theme_idx]
        settings = t['settings']
        name = t['theme_name']

    if group_id:
        theme_repository.save_theme_for_group(
            group_id, name, settings, session['user_id'])
        flash(f'Theme "{name}" applied successfully!', "success")
    else:
        # Admin applying platform default
        theme_repository.save_platform_default_theme(
            name, settings, session['user_id'])
        flash(f'Platform default theme set to "{name}".', "success")

    return redirect(url_for("theme_settings"))


# ─── Theme editor (open) ──────────────────────────────────────────────────────

@app.route("/theme/editor", methods=["GET"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def theme_editor():
    """
    US 2.1 AC3/AC4, 2.2, 2.3, 2.4, 2.5, 3.6:
    Open the theme editor.  Optional ?from_premade=<idx>&source=db|builtin
    pre-fills from that premade; otherwise loads current saved theme or defaults.
    """
    role     = session.get("role")
    group_id = session.get("group_id") if role == "Coordinator" else None

    # Source: premade to customise, or current group theme
    from_premade = request.args.get("from_premade", type=int)
    source       = request.args.get("source", "builtin")
    theme_id_db  = request.args.get("theme_id",  type=int)

    settings = None

    if from_premade is not None and source == "builtin":
        if 0 <= from_premade < len(DEFAULT_PREMADE):
            active = DEFAULT_PREMADE[from_premade]
            settings = DEFAULT_PREMADE[from_premade]['settings']
    elif source == "db" and theme_id_db:
        rows = theme_repository.get_premade_themes()
        row  = next((r for r in rows if r['theme_id'] == theme_id_db), None)
        if row:
            settings = row['settings']
            if isinstance(settings, str):
                settings = json.loads(settings)
    else:
        theme = theme_repository.get_platform_default_theme()  # ensure platform default is loaded for non-group users
        active = theme if theme else DEFAULT_PREMADE[0]
        settings = active['settings']
   

    if settings is None and group_id:
        active = theme_repository.get_active_theme_for_group(group_id)
        if active:
            settings = active['settings']
            if isinstance(settings, str):
                settings = json.loads(settings)

    if settings is None:
        # US 2.1 AC4: from scratch defaults
        settings = {
            "colors": {"primary": "#2e7d32", "secondary": "#a5d6a7",
                       "background": "#f4f8f4", "button": "#2e7d32"},
            "visuals": {"font": "system", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "centered"},
        }

    return render_template(
        "theme_editor.html",
        settings=settings,
        font_options=FONT_OPTIONS,
        layout_options=LAYOUT_OPTIONS,
        role=role,
        group_id=group_id,
        theme_name=active['theme_name'] if settings else "My Custom Theme",
    )


# ─── Save theme ───────────────────────────────────────────────────────────────

@app.route("/theme/save", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def theme_save():
    """
    US 2.2 AC3, 2.3 AC3, 2.4 AC3, 2.5 AC2/AC3, 3.6 AC2:
    Save / update theme for the group (or platform default for Admin).
    """
    role     = session.get("role")
    group_id = session.get("group_id") if role == "Coordinator" else None

    theme_name = request.form.get("theme_name", "Custom Theme").strip() or "Custom Theme"

    # Build settings from form
    settings = _settings_from_form()

    # Handle image uploads (merge with old paths)
    old_settings = None
    if group_id:
        active = theme_repository.get_active_theme_for_group(group_id)
        if active:
            old_settings = active['settings']
            if isinstance(old_settings, str):
                old_settings = json.loads(old_settings)

    errors = _merge_images_into_settings(settings, old_settings)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("theme_editor"))

    if group_id:
        theme_repository.save_theme_for_group(
            group_id, theme_name, settings, session['user_id'])
        flash("Theme saved and applied to your group pages!", "success")
    else:
        theme_repository.save_platform_default_theme(
            theme_name, settings, session['user_id'])
        flash("Platform-wide default theme updated!", "success")

    return redirect(url_for("theme_settings"))


# ─── Rollback ────────────────────────────────────────────────────────────────

@app.route("/theme/rollback", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def theme_rollback():
    """US 3.7 AC3: Roll back to a selected previous theme version."""
    role     = session.get("role")
    group_id = session.get("group_id") if role == "Coordinator" else None

    if not group_id:
        flash("Rollback is only available for group themes.", "danger")
        return redirect(url_for("theme_settings"))

    theme_id = request.form.get("theme_id", type=int)
    if not theme_id:
        flash("No theme selected for rollback.", "danger")
        return redirect(url_for("theme_settings"))

    new_id = theme_repository.rollback_to_theme(group_id, theme_id, session['user_id'])
    if new_id:
        flash("Theme restored successfully!", "success")
    else:
        flash("Could not restore that theme.", "danger")
    return redirect(url_for("theme_settings"))


# ─── Admin: override a specific group's theme ────────────────────────────────

@app.route("/admin/group/<int:target_group_id>/theme", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_group_theme(target_group_id):
    """US 3.8 AC3: Admin views/edits the theme for a specific group."""
    active = theme_repository.get_active_theme_for_group(target_group_id)
    settings = None
    if active:
        settings = active['settings']
        if isinstance(settings, str):
            settings = json.loads(settings)

    if settings is None:
        settings = {
            "colors": {"primary": "#2e7d32", "secondary": "#a5d6a7",
                       "background": "#f4f8f4", "button": "#2e7d32"},
            "visuals": {"font": "system", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "centered"},
        }

    return render_template(
        "theme_editor.html",
        settings=settings,
        font_options=FONT_OPTIONS,
        layout_options=LAYOUT_OPTIONS,
        role="Admin",
        group_id=target_group_id,
        admin_override=True,
        theme_name= active['theme_name'] if active else "Admin Override",
    )


@app.route("/admin/group/<int:target_group_id>/theme/save", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_group_theme_save(target_group_id):
    """US 3.8 AC3: Admin saves an overridden theme for a specific group."""
    theme_name = request.form.get("theme_name", "Admin Override").strip() or "Admin Override"
    settings   = _settings_from_form()

    active = theme_repository.get_active_theme_for_group(target_group_id)
    old_settings = None
    if active:
        old_settings = active['settings']
        if isinstance(old_settings, str):
            old_settings = json.loads(old_settings)

    errors = _merge_images_into_settings(settings, old_settings)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("admin_group_theme", target_group_id=target_group_id))

    theme_repository.save_theme_for_group(
        target_group_id, theme_name, settings, session['user_id'])
    flash(f"Theme for group {target_group_id} overridden successfully.", "success")
    return redirect(url_for("sa_manage_groups"))


# ─── Context processor: inject active theme CSS vars into every page ──────────

@app.context_processor
def inject_theme():
    """
    US 3.9: Makes `theme_vars` available in every template.
    Returns CSS custom properties string if a theme is active for the session group.
    Also returns theme settings dict as `active_theme_settings`.
    """
    settings = None

    group_id = session.get("group_id")
    if group_id:
        settings = theme_repository.get_effective_theme(group_id)
    if not settings:
        default_theme = theme_repository.get_platform_default_theme()
        if default_theme:
             settings = default_theme['settings']
             if isinstance(settings, str):
                 settings = json.loads(settings)
    if not settings:        # Fall back to hardcoded default if no platform default in DB
        settings = {
            "colors": {"primary": "#2e7d32", "secondary": "#a5d6a7",
                       "background": "#f4f8f4", "button": "#2e7d32"},
            "visuals": {"font": "system", "banner": "", "logo": "", "bg_image": ""},
            "layout": {"template": "centered"},
        }

    colors  = settings.get("colors", {})
    visuals = settings.get("visuals", {})
    layout  = settings.get("layout", {})

    font_key = visuals.get("font", "system")
    font_css = _get_font_css(font_key)

    css_vars = f"""
    --theme-primary: {colors.get('primary', '#2e7d32')};
    --theme-secondary: {colors.get('secondary', '#a5d6a7')};
    --theme-bg: {colors.get('background', '#f4f8f4')};
    --theme-btn: {colors.get('button', '#2e7d32')};
    --theme-font: {font_css};
    """.strip()

    def _clean(val):
        """Return URL only if non-empty.
        For any /static/... path, verify the file actually exists on disk.
        This prevents broken images from old/seeded DB data.
        External http/https URLs are always passed through."""
        import os as _os
        v = (val or "").strip()
        if not v:
            return None
        if v.startswith('http://') or v.startswith('https://'):
            return v  # external URL, trust it
        if v.startswith('/static/') or v.startswith('static/'):
            # Resolve relative to the app package directory
            rel = v.lstrip('/')  # strip leading slash
            abs_path = _os.path.join(_os.path.dirname(__file__), rel)
            if not _os.path.isfile(abs_path):
                return None  # file not on disk -> don't render broken img
        return v

    return {
        "theme_vars": css_vars,
        "active_theme_settings": settings,
        "active_layout": layout.get("template", "centered"),
        "active_theme_bg_image": _clean(visuals.get("bg_image")),
        "active_theme_banner":   _clean(visuals.get("banner")),
        "active_theme_logo":     _clean(visuals.get("logo")),
    }
