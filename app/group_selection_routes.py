"""
GROUP SELECTION 
Handles user group selection when they have roles in multiple groups.
"""

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
from app.repository import core_repository
import app.utils as utils


@app.route("/choose_group", methods=["GET", "POST"])
@utils.login_required()
def choose_group():
    """
    Displays available groups for the logged-in user and handles group selection.
    
    GET: Display the group selection page with all groups the user belongs to
    POST: Process the selected group and redirect to appropriate dashboard
    
    Returns:
        GET: Rendered choose_group.html template with available groups
        POST: Redirect to dashboard after group selection
    """
    user_id = session.get("user_id")
    
    if not user_id:
        flash("Please log in to select a group.", "danger")
        return redirect(url_for("login"))
    
    # Fetch all groups the user belongs to
    groups = core_repository.get_groups_by_user_id(user_id)
    
    # If user has no groups, redirect to home
    if not groups:
        flash("You are not assigned to any active groups.", "warning")
        return redirect(url_for("home"))

    # If the user only has one active group, restore it immediately so
    # downstream pages keep the current group context after a change-group action.
    if len(groups) == 1 and request.method == "GET":
        group = groups[0]
        session["group_id"] = group["group_id"]
        session["group_name"] = group["name"]
        session["role"] = group["role"]
        session.pop("select_group", None)
        flash(f"Using your only active group: {group['name']}.", "success")
        return redirect(utils.get_dashboard_link_for_role())
    
    # Handle group selection submission
    if request.method == "POST":
        selected_group_id = request.form.get("group_id")
        
        # Validate the selected group exists and user belongs to it
        group = next((g for g in groups if str(g["group_id"]) == selected_group_id), None)
        
        if selected_group_id and group:
            # Store group selection in session
            session["group_id"] = selected_group_id  # For compatibility with existing code
            session["group_name"] = group["name"]  # Store group name for display purposes
            # Update user role based on their role in the selected group
            raw_role = group["role"]
            session["role"] = raw_role
            
            # Clear the "needs to select group" flag
            session.pop("select_group", None)
            
            flash(f"Successfully selected {group['name']}!", "success")
            
            # Redirect to the appropriate dashboard for the user's role
            dashboard_url = utils.get_dashboard_link_for_role()
            return redirect(dashboard_url)
        else:
            flash("Invalid group selection. Please try again.", "danger")
    
    # GET request: Display group selection page
    return render_template("choose_group.html", title="Choose Group", groups=groups)


@app.route("/change_group", methods=["GET", "POST"])
@utils.login_required()
def change_group():
    """
    Allows a logged-in user to change their group selection.
    Useful when a user wants to switch between groups they belong to.
    Super admins cannot change groups as they don't belong to any.
    
    Returns:
        Redirects to choose_group for group reselection, or admin dashboard if super admin
    """
    # Super admins cannot change groups
    if session.get("role") == "Admin":
        flash("Super admins do not belong to groups.", "warning")
        return redirect(utils.get_dashboard_link_for_role())
    
    # Mark the user as actively changing groups, but keep the current group
    # until they actually choose a new one.
    session["select_group"] = True
    
    return redirect(url_for("choose_group"))


def get_user_groups(user_id):
    """
    Retrieves all groups a user belongs to.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        list: List of group dictionaries with group_id, name, role, etc.
    """
    return core_repository.get_groups_by_user_id(user_id)


def get_current_group_id():
    """
    Gets the currently selected group ID from the session.
    
    Returns:
        int or None: The group ID if selected, None otherwise
    """
    return session.get("group_id")


def is_group_selected():
    """
    Checks if a group has been selected in the current session.
    
    Returns:
        bool: True if a group is selected, False otherwise
    """
    return bool(get_current_group_id())


def ensure_group_selected():
    """
    Decorator to ensure a group has been selected before accessing a route.
    If no group is selected, redirects to group selection page.
    
    Usage:
        @app.route('/some/protected/route')
        @ensure_group_selected()
        def my_route():
            # This route will only be accessible after group selection
            pass
    """
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not is_group_selected():
                flash("Please select a group first.", "warning")
                return redirect(url_for("choose_group"))
            return f(*args, **kwargs)
        return wrapper
    return decorator
