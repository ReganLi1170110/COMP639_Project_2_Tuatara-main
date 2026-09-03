from flask import abort, render_template, request, redirect, url_for, flash, session
from app.repository import facade_repository, user_repository
from app import flask_app as app
import app.utils as utils


@app.route("/observer_dashboard", methods=["GET"])
@utils.login_required("Please log in to access the observer dashboard.")
@utils.roles_required("Observer")
def observer_dashboard():

    current_user = user_repository.get_user_by_id(session["user_id"])
    if current_user is None:
        session.clear()
        flash("Your account could not be found. Please log in again.", "danger")
        return redirect(url_for("login"))
    group_id = session.get("group_id")
    dashboard = facade_repository.get_observer_dashboard_data(group_id)
    return render_template(
        "observer_dashboard.html",
        title="Observer Dashboard",
        current_user=current_user,
        dashboard=dashboard,
    )
