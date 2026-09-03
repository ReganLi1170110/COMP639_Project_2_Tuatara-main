# This script runs automatically when our `app` module is first loaded,
# and handles all the setup for our Flask app.
from flask import Flask, app, flash, request, session, redirect, url_for, g
from app.db import db
from datetime import datetime, timedelta, timezone
from app.db import connect
import os

flask_app = Flask(__name__)
flask_app.secret_key = 'predator-monitoring-secret-key-from-tuatara'
flask_app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
flask_app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
flask_app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB max upload

IDLE_TIMEOUT = timedelta(minutes=30)

@flask_app.before_request
def refresh_session_timeout():
    # Skip static files
    if request.endpoint == 'static':
        return

    session.permanent = True

    now = datetime.now(timezone.utc)
    last_activity = session.get("last_activity")

    if last_activity:
        last_activity = datetime.fromisoformat(last_activity)

        if now - last_activity > IDLE_TIMEOUT:
            session.clear()
            return redirect(url_for("login"))  # change to your login route

    # THIS is the key line — forces cookie refresh
    session["last_activity"] = now.isoformat()

@flask_app.teardown_request
def handle_transaction(exception):
    db = g.get("db", None)
    if not db:
        return
    try:
        if exception:
            db.rollback()
        else:
            db.commit()
    except:
        db.rollback()
        
db.init_db(flask_app, connect.dbuser, connect.dbpass, connect.dbhost, connect.dbname,
           connect.dbport, connect.dbautocommit)


# Error handler for request too large (413)
@flask_app.errorhandler(413)
def request_entity_too_large(error):
    from flask import flash
    flash('File is too large. Maximum file size is 2 MB.', 'danger')
    return redirect(request.referrer or url_for('sa_manage_groups')), 413

@flask_app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("home"))

@flask_app.errorhandler(500)
def handle_exception(e):
    flash("Something went wrong.")
    return redirect(url_for("home"))


# import route modules to register their decorators
from app import common_routes
from app import admin_routes
from app import operator_routes
from app import observer_routes
from app import routes 
from app import bait_station_routes
from app import group_selection_routes
from app import knowhub_route
from app import theme_routes
from app import map_routes
from app import donate_routes


@flask_app.context_processor
def inject_login_notifications():
    # Pop notifications prepared at login and expose to templates as
    # `login_notifications` (list of dicts with message/created_at).
    msgs = session.pop("login_notification_messages", None)
    if msgs:
        return {"login_notifications": msgs}

    # If none were prepared at login, try to fetch any unread notifications
    # for the currently logged-in user (this makes the popup resilient if
    # notifications were created after the login step or the login flow was
    # modified).
    try:
        from app.repository import notification_repository
        user_id = session.get("user_id")
        if user_id:
            unread = notification_repository.get_unread_notifications(user_id)
            if unread:
                msgs = [
                    {"message": n["message"], "created_at": (n["created_at"].isoformat() if hasattr(n["created_at"], "isoformat") else str(n["created_at"]))}
                    for n in unread
                ]
                # mark them read so they do not appear again
                try:
                    notification_repository.mark_notifications_read(user_id)
                except Exception:
                    pass
                return {"login_notifications": msgs}
    except Exception:
        # Non-fatal: if fetching fails, fall back to empty list
        pass

    return {"login_notifications": []}