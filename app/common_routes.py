# Common Routes
# Handles public and shared application routes including registration, login, 
# profile management, and general data viewing.

from flask import abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app import map_routes_helper
from app.repository import (
    core_repository,
    facade_repository,
    user_repository,
    notification_repository,
    common_repository,
    donation_repository, 
    group_settings_repository,
    dashboard_repository,
)
from app.repository import  badge_repository
from app import flask_app as app
import app.utils as utils
import csv
from io import StringIO
from datetime import datetime, timezone, timedelta
import json
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



#This is the Home page 
@app.route("/", methods=["GET"])
def home():
    page_size = 6
    page = request.args.get("page", 1, type=int)
    if page is None or page < 1:
        page = 1

    groups, total_count = core_repository.get_active_groups_for_home(page=page, page_size=page_size)
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0

    if total_pages > 0 and page > total_pages:
        page = total_pages
        groups, total_count = core_repository.get_active_groups_for_home(page=page, page_size=page_size)

    # Convert group list to dictionaries and inject donation_enabled flag
    groups = [dict(g) for g in groups]
    for g in groups:
        gid = g.get('group_id')
        try:
            g['donation_enabled'] = group_settings_repository.get_group_setting(gid, 'donation_enabled', True)
        except Exception:
            g['donation_enabled'] = True

    start_index = (page - 1) * page_size + 1 if total_count else 0
    end_index = start_index + len(groups) - 1 if groups else 0

    user_group_ids = []
    user_pending_group_ids = []
    user_group_roles = {}
    if session.get("user_id"):
        statuses = core_repository.get_user_group_statuses(session["user_id"])
        user_group_ids = [s["group_id"] for s in statuses if s["membership_status"] == "Active"]
        user_pending_group_ids = [s["group_id"] for s in statuses if s["membership_status"] == "Pending"]
        user_group_roles = {s["group_id"]: s["role"] for s in statuses if s["membership_status"] == "Active"}

    return render_template(
        "home.html",
        title="Home",
        groups=groups,
        user_group_ids=user_group_ids,
        user_group_roles=user_group_roles,
        user_pending_group_ids=user_pending_group_ids,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_page=page - 1,
        next_page=page + 1,
        start_index=start_index,
        end_index=end_index,
    )


@app.route("/groups/<int:group_id>", methods=["GET"])
def group_view(group_id):
    group = core_repository.get_group_by_id(group_id)
    if not group:
        abort(404)

    if not group['is_public']:
        if not session.get("user_id"):
            flash("Please log in to view this group.", "danger")
            return redirect(url_for("login"))
        user_id = session["user_id"]
        if not user_repository.is_accessible_group_member(user_id, group_id):
            flash("You do not have access to view this group.", "danger")
            return redirect(url_for("home"))

    group["operational_area_display"] = map_routes_helper.format_operational_area(group.get("operational_area"))
    group_members = core_repository.get_group_members(group_id)
    group_lines = core_repository.get_group_lines(group_id)
    latest_activity = core_repository.get_group_latest_activity(group_id)
    # Donation summary for this group (total amount, count, latest date)
    try:
        donation_summary = donation_repository.get_donation_summary_for_group(group_id)
    except Exception:
        donation_summary = None
    # donation enabled flag from group settings (defaults to True)
    try:
        donation_enabled = group_settings_repository.get_group_setting(group_id, 'donation_enabled', True)
    except Exception:
        donation_enabled = True

    user_group_ids = []
    user_pending_group_ids = []
    if session.get("user_id"):
        statuses = core_repository.get_user_group_statuses(session["user_id"])
        user_group_ids = [s["group_id"] for s in statuses if s["membership_status"] == "Active"]
        user_pending_group_ids = [s["group_id"] for s in statuses if s["membership_status"] == "Pending"]

    return render_template(
        "group_view.html",
        title=group["name"],
        group=group,
        group_members=group_members,
        group_lines=group_lines,
        latest_activity=latest_activity,
        user_group_ids=user_group_ids,
        user_pending_group_ids=user_pending_group_ids,
        can_edit_group=session.get("role") == "Admin",
        donation_summary=donation_summary,
        donation_enabled=donation_enabled,
    )


@app.route("/groups/<int:group_id>/join", methods=["POST"])
def join_group(group_id):
    if not session.get("user_id"):
        flash("Please log in to join a group.", "danger")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    group = core_repository.get_group_by_id(group_id)
    if not group:
        abort(404)

    status = core_repository.submit_join_request(group_id, user_id, group["is_public"])

    if status == "Active":
        flash("You are already a member of this group.", "info")
    elif status == "NewPending":
        # Only notify coordinators for NEW requests, not existing ones
        try:
            members = core_repository.get_group_members(group_id)
            user = user_repository.get_user_by_id(user_id)
            user_name = f"{user['first_name']} {user['last_name'] or ''}".strip()
            for m in members:
                if m['role'] in ('Coordinator'):
                    notification_repository.create_user_notification(
                        m['user_id'],
                        f'{user_name} has requested to join your group "{group["name"]}".',
                        group_id
                    )
        except Exception:
            pass
        flash(f'Your request to join "{group["name"]}" has been submitted. Please wait for approval.', "success")
    elif status == "Pending":
        # User already has a pending request
        flash(f'You already have a pending request for this group. Please wait for the coordinator\'s response.', "info")
    elif status == "Joined":
        # Update session so the user can immediately access role-protected pages
        # For public groups, default to Observer role on join
        if "group_id" not in session:
            session["group_id"] = group_id
            session["role"] = "Observer"
            session.pop("select_group", None)
        flash(f'You have joined "{group["name"]}"!', "success")
    else:
        # Fallback for any unexpected status
        flash(f'Your request to join "{group["name"]}" has been submitted. Please wait for approval.', "success")

    return redirect(url_for("home"))

@app.route("/groups/<int:group_id>/cancel-join-request", methods=["POST"])
@utils.login_required()
def cancel_join_request(group_id):
    user_id = session["user_id"]
    group = core_repository.get_group_by_id(group_id)
    if not group:
        abort(404)

    removed = core_repository.cancel_join_request(group_id, user_id)
    if removed:
        flash(f'Your join request to "{group["name"]}" has been cancelled.', "success")
    else:
        flash('No pending join request was found for this group.', 'info')

    return redirect(request.referrer or url_for("home"))

@app.route("/groups/<int:group_id>/leave", methods=["POST"])
@utils.login_required()
def leave_group(group_id):
    user_id = session["user_id"]
    group = core_repository.get_group_by_id(group_id)
    if not group:
        abort(404)

    # Only Observers can leave via this route; Coordinators cannot self-leave
    statuses = core_repository.get_user_group_statuses(user_id)
    membership = next((s for s in statuses if s["group_id"] == group_id), None)
    if not membership or membership["role"] not in ("Observer",):
        flash("You cannot leave this group.", "warning")
        if session.get("role") == "Observer":
            return redirect(url_for("observer_dashboard"))
        elif session.get("role") == "Operator":
            return redirect(url_for("operator_dashboard"))
        else:
            return redirect(url_for("home"))

    removed = core_repository.leave_group(group_id, user_id)
    if removed:
        session.pop("role", None)
        session.pop("groupId", None)
        flash(f'You have left "{group["name"]}".', "success")
    else:
        flash("Could not leave group.", "danger")
    
    if session.get("role") == "Observer":
        return redirect(url_for("observer_dashboard"))
    elif session.get("role") == "Operator":
        return redirect(url_for("operator_dashboard"))
    else:
        return redirect(url_for("home"))

#***********************************************************************************************************************
# Register an account, only observer role can be registered through this page, admin can change accounts to other roles through admin user management page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        first_name = request.form.get("first_name", "")
        last_name = request.form.get("last_name", "")
        phone_number = request.form.get("phone_number", "")
        emergency_contact_name = request.form.get("emergency_contact_name", "")
        emergency_contact_phone_number = request.form.get("emergency_contact_phone_number", "")
        emergency_contact_relationship = request.form.get("emergency_contact_relationship", "")

        errors = False

        # password matching
        if password != confirm_password:
            flash("Passwords do not match. Please enter the password again.", "danger")
            errors = True
        else:
            # password complexity
            if utils.check_password_complexity(password) == False:
                flash("Password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.", "danger")
                errors = True

        if user_repository.get_user_by_username(username):
            flash("The username is already in use. Please supply a different username.", "danger")
            errors = True
            
        if user_repository.get_user_by_email(email):
            flash("The email address is already in use. Please supply a different email.", "danger")
            errors = True
        elif not utils.is_valid_email_format(email):
            flash("Email address must contain @ and . and no other special characters.", "danger")
            errors = True

        if not utils.is_valid_nz_phone_number(phone_number):
            flash("Phone number must be a valid New Zealand number (for example 0212345678 or +64212345678).", "danger")
            errors = True

        if not utils.is_valid_nz_phone_number(emergency_contact_phone_number):
            flash("Emergency contact phone number must be a valid New Zealand number (for example 0212345678 or +64212345678).", "danger")
            errors = True

        if errors:
            return render_template("register.html", 
                                   username=username, email=email, first_name=first_name, 
                                   last_name=last_name, phone_number=phone_number,
                                   emergency_contact_name=emergency_contact_name,
                                   emergency_contact_phone_number=emergency_contact_phone_number,
                                   emergency_contact_relationship=emergency_contact_relationship)

        user_data = {
            "username": username,
            "email": email,
            "password_hash": utils.generate_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_phone_number": emergency_contact_phone_number,
            "emergency_contact_relationship": emergency_contact_relationship,
            "account_status": "Active"
        }

        try:
            user_repository.create_user(user_data)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")

    return render_template("register.html")

#***********************************************************************************************************************
# Change password for logged in users
@app.route("/account/change-password", methods=["GET", "POST"])
def change_password():
    if not utils.isloggedin():
        flash("Please log in to change your password.", "danger")
        return redirect(url_for("login"))

    current_user = user_repository.get_user_by_id(session["user_id"])
    if current_user is None:
        session.clear()
        flash("Your account could not be found. Please log in again.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        has_errors = False

        if not utils.check_password_hash(current_user["password_hash"], current_password):
            flash("Current password is incorrect.", "danger")
            has_errors = True

        if utils.check_password_hash(current_user["password_hash"], new_password):
            flash("New password cannot be the same as your current password.", "danger")
            has_errors = True

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            has_errors = True
        elif not utils.check_password_complexity(new_password):
            flash("New password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.", "danger")
            has_errors = True

        if not has_errors:
            user_repository.update_user_password(session["user_id"], utils.generate_password_hash(new_password))
            flash("Password changed successfully.", "success")
            return redirect(url_for("account_profile"))

    return render_template("change_password.html", title="Change Password")

#*********************************************************************************************************************** 
# Login entry point, also redirect to dashboard after login and check account status
@app.route("/login", methods=["GET", "POST"])
def login():
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = user_repository.get_user_by_username(username)
        
        if user:
            # Check password first
            if not utils.check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.", "danger")
            # Check account status
            elif user["account_status"] != "Active":
                flash("Your account is inactive. Please contact an administrator.", "danger")
            else:
                session["user_id"] = user["user_id"]
                if user["is_super_admin"]:
                    session["role"] = "Admin"
                    try:
                        badge_repository.add_user_points(user["user_id"], badge_repository.BadgeAction.DAILY_LOGIN, 'Daily login')
                    except Exception:
                        pass
                    flash("Login successful!", "success")
                    return redirect(utils.get_dashboard_link_for_role())
                else:
                    groups = core_repository.get_groups_by_user_id(user["user_id"])
                    if len(groups) == 1:
                        session["group_id"] = groups[0]["group_id"]
                        session["group_name"] = groups[0]["name"]
                        raw_role = groups[0]["role"]
                        session["role"] = raw_role
                        try:
                            badge_repository.add_user_points(user["user_id"], badge_repository.BadgeAction.DAILY_LOGIN, 'Daily login')
                        except Exception:
                            pass
                        flash("Login successful!", "success")
                        return redirect(utils.get_dashboard_link_for_role())
                    elif len(groups) > 1:
                        session["select_group"] = True
                        return redirect(url_for("choose_group"))
                    else:
                        flash("Your account is not associated with any active groups. Please consider choosing a group first.", "success")
                        return redirect(url_for("home"))
                    
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template("login.html", username=username)

# Badge introduction page
@app.route('/badges/intro')
def badges_intro():
    """Display badge gamification introduction page."""
    # If user is logged in, pass badge progress data; otherwise show static page
    total_points = 0
    badges = []
    if session.get('user_id'):
        total_points, badges, _, _ = _build_profile_badge_progress(session['user_id'])
    
    return render_template('badges_intro.html', total_points=total_points, badges=badges)

#***********************************************************************************************************************
# Dashboard redirect based on role
@app.route("/dashboard")
def dashboard():
    return redirect(utils.get_dashboard_link_for_role())


#***********************************************************************************************************************
# Lines list page - view trap lines and bait station lines for selected group
# US: View trap lines and bait station lines within my selected conservation group
@app.route("/lines", methods=["GET"])
@utils.login_required("Please log in to view lines.")
def lines():
    """
    Display trap lines and bait station lines for the currently selected group.
    
    AC1: Only lines for the currently selected group (session['group_id']) are shown.
    AC2: Trap lines and bait station lines are displayed as separate sections.
    AC3: Each line card clearly shows "Trap Line" or "Bait Station Line".
    AC4: Each line displays: name, type, status, number of traps/bait stations, assigned operator.
    AC5: Edit/management buttons visible only to Operators and Group Coordinators.
    AC6: If user is not a member of the group, redirect to home with flash message.
    AC7: If no lines exist, show "No lines available" message.
    """
    group_id = session.get("group_id")
    user_id = session.get("user_id")
    
    # AC6: Check if user is a member of the selected group
    if not group_id:
        flash("Please select a group first.", "warning")
        return redirect(url_for("choose_group"))
    
    if not user_repository.is_accessible_group_member(user_id, group_id):
        flash("You do not have access to this group. Please select a different group.", "danger")
        return redirect(url_for("home"))
    
    # Get user's role in the selected group
    user_role = session.get("role", "")
    
    # AC5: Determine if user can manage lines (Operators or Coordinators)
    can_manage_lines = utils.check_role_access(user_role, ["Coordinator", "Operator"])
    
    # Get lines organized by type with asset counts and operators
    # AC1: Only lines for the selected group
    # AC2: Trap and bait station lines separated
    lines_data = facade_repository.get_lines_by_group_organized_by_type(group_id)
    
    trap_lines = lines_data.get("trap_lines", [])
    bait_station_lines = lines_data.get("bait_station_lines", [])
    total_lines = lines_data.get("total_lines", 0)
    
    return render_template(
        "group_lines.html",
        title="Group Lines",
        trap_lines=trap_lines,
        bait_station_lines=bait_station_lines,
        total_lines=total_lines,
        can_manage_lines=can_manage_lines,
        user_role=user_role,
        group_id=group_id,
    )




#***********************************************************************************************************************
# Account profile page for logged in user to view and edit their own profile
def _build_profile_badge_progress(user_id):
    total_points = int(badge_repository.get_user_points(user_id) or 0)
    user_redemptions = {r["badge_name"]: r for r in badge_repository.get_user_badge_redemptions(user_id)}
    badges = []
    for name, meaning, points_required, slug, badge_id in badge_repository.BADGES_SEED:
        redemption = user_redemptions.get(name)
        badges.append({
            "badge_id": badge_id,
            "name": name,
            "meaning": meaning,
            "points_required": int(points_required),
            "slug": slug,
            "earned": total_points >= int(points_required),
            "claimed": bool(redemption),
            "claim_status": redemption["status"] if redemption else None,
            "claim_requested_at": redemption["requested_at"] if redemption else None,
        })

    current_badge = None
    for badge in badges:
        if badge["earned"]:
            current_badge = badge

    next_badge = next((badge for badge in badges if not badge["earned"]), None)
    if next_badge:
        current_points_required = current_badge["points_required"] if current_badge else 0
        next_points_required = next_badge["points_required"]
        segment_total = next_points_required - current_points_required
        if segment_total > 0:
            segment_points = total_points - current_points_required
            if segment_points < 0:
                segment_points = 0
            if segment_points > segment_total:
                segment_points = segment_total
            progress_percent = int((segment_points / segment_total) * 100)
        else:
            progress_percent = 100
    else:
        progress_percent = 100

    return total_points, badges, next_badge, progress_percent


@app.route("/account/profile", methods=["GET", "POST"])
@utils.login_required("Please log in to view your profile.")
def account_profile():
    current_user = user_repository.get_user_by_id(session["user_id"])
    if current_user is None:
        session.clear()
        flash("Your account could not be found. Please log in again.", "danger")
        return redirect(url_for("login"))

    current_user["role"] = session.get("role", "")
    if request.method == "POST":
        claim_action = request.form.get("claim_action", "").strip()
        dashboard_url = utils.get_dashboard_link_for_role()

        if claim_action == "claim_physical":
            badge_id = request.form.get("claim_badge_id", "").strip()
            recipient_name = request.form.get("claim_full_name", "").strip()
            street_address = request.form.get("claim_street_address", "").strip()
            suburb = request.form.get("claim_suburb", "").strip()
            city = request.form.get("claim_city", "").strip()
            postcode = request.form.get("claim_postcode", "").strip()

            has_errors = False
            total_points = int(badge_repository.get_user_points(session["user_id"]) or 0)
            badge = None
            if not badge_id or not badge_id.isdigit():
                flash("Invalid badge selection.", "danger")
                has_errors = True
            else:
                badge = next((b for b in badge_repository.BADGES_SEED if str(b[4]) == badge_id), None)
                if badge is None:
                    flash("Invalid badge selection.", "danger")
                    has_errors = True

            if not recipient_name:
                flash("Full Name is required.", "danger")
                has_errors = True
            if not street_address:
                flash("Street Address is required.", "danger")
                has_errors = True
            if not suburb:
                flash("Suburb is required.", "danger")
                has_errors = True
            if not city:
                flash("City is required.", "danger")
                has_errors = True
            if not postcode or not postcode.isdigit() or len(postcode) != 4:
                flash("Please enter a valid 4-digit NZ postcode", "danger")
                has_errors = True

            if badge and total_points < int(badge[2]):
                flash("You have not unlocked this badge yet.", "danger")
                has_errors = True

            if not has_errors:
                existing = badge_repository.get_user_badge_redemption(session["user_id"], badge[0])
                if existing:
                    flash("You have already claimed this badge physically.", "danger")
                    has_errors = True

            if not has_errors:
                shipping_address = f"{street_address}\n{suburb}\n{city} {postcode}"
                try:
                    badge_repository.add_badge_redemption(
                        session["user_id"],
                        badge[0],
                        recipient_name,
                        shipping_address,
                        city,
                        postcode,
                    )
                    flash("Physical badge claim submitted successfully.", "success")
                    return redirect(url_for("account_profile"))
                except Exception:
                    flash("Unable to submit your badge claim. Please try again.", "danger")

        else:
            email = request.form.get("email", "").strip()
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            phone_number = request.form.get("phone_number", "").strip()
            emergency_contact_name = request.form.get("emergency_contact_name", "").strip()
            emergency_contact_phone_number = request.form.get("emergency_contact_phone_number", "").strip()
            emergency_contact_relationship = request.form.get("emergency_contact_relationship", "").strip()

            has_errors = False

            if not email:
                flash("Email is required.", "danger")
                has_errors = True
            elif user_repository.get_user_by_email(email) and email != current_user["email"]:
                flash("The email is already in use. Please choose another email.", "danger")
                has_errors = True
            
            if email and not utils.is_valid_email_format(email):
                flash("Email address must contain @ and . and no other special characters.", "danger")
                has_errors = True

            if not first_name:
                flash("First name is required.", "danger")
                has_errors = True
            if not phone_number:
                flash("Phone number is required.", "danger")
                has_errors = True
            elif not utils.is_valid_nz_phone_number(phone_number):
                flash("Phone number must be a valid New Zealand number (for example 0212345678 or +64212345678).", "danger")
                has_errors = True
            if not emergency_contact_name:
                flash("Emergency contact name is required.", "danger")
                has_errors = True
            if not emergency_contact_phone_number:
                flash("Emergency contact phone number is required.", "danger")
                has_errors = True
            elif not utils.is_valid_nz_phone_number(emergency_contact_phone_number):
                flash("Emergency contact phone number must be a valid New Zealand number (for example 0212345678 or +64212345678).", "danger")
                has_errors = True
            if not emergency_contact_relationship:
                flash("Emergency contact relationship is required.", "danger")
                has_errors = True

            if not has_errors:
                user_repository.update_user_account_profile(
                    session["user_id"],
                    {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone_number": phone_number,
                        "emergency_contact_name": emergency_contact_name,
                        "emergency_contact_phone_number": emergency_contact_phone_number,
                        "emergency_contact_relationship": emergency_contact_relationship,
                    }
                )
                flash("Profile updated successfully.", "success")
                return redirect(url_for("account_profile"))

        profile_user = {
            "username": current_user["username"],
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_phone_number": emergency_contact_phone_number,
            "emergency_contact_relationship": emergency_contact_relationship,
            "role": session.get("role", ""),
            "account_status": current_user["account_status"],
        }
        total_points, badges, next_badge, progress_percent = _build_profile_badge_progress(session["user_id"])
        return render_template(
            "account_profile.html",
            title="My Account",
            user=profile_user,
            dashboard_url=dashboard_url,
            total_points=total_points,
            badges=badges,
            next_badge=next_badge,
            progress_percent=progress_percent,
        )

    total_points, badges, next_badge, progress_percent = _build_profile_badge_progress(session["user_id"])
    return render_template(
        "account_profile.html",
        title="My Account",
        user=current_user,
        dashboard_url=utils.get_dashboard_link_for_role(),
        total_points=total_points,
        badges=badges,
        next_badge=next_badge,
        progress_percent=progress_percent,
    )
        


#***********************************************************************************************************************
# Logout route
@app.route("/logout", methods=["GET"])
#When logout, user should not be redirected to login.Sally 10/05/2026
#@utils.login_required()
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/lines/<int:line_id>", methods=["GET"])
@utils.login_required("Please log in to view line details.")
def line_detail(line_id):
    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    can_manage_line = utils.check_role_access(session.get("role", ""), ["Admin", "Coordinator"])
    line_management_options = None
    assigned_operator_ids = []
    available_operators = []
    if can_manage_line:
        line_management_options = facade_repository.get_line_management_options()
        assigned_operator_ids = [operator["user_id"] for operator in line_data["operators"]]
        # Pass line's group_id to filter operators to only show team members
        available_operators = facade_repository.get_unassigned_operators_for_line(line_id, line_data["group_id"])

    # Determine if current operator is assigned to this line
    is_operator_assigned = False
    if session.get("role") == "Operator":
        current_user_id = session.get("user_id")
        is_operator_assigned = any(operator["user_id"] == current_user_id for operator in line_data["operators"])

    return render_template(
        "line_detail.html",
        title=f"Line {line_data['line_name']}",
        line=line_data,
        can_manage_line=can_manage_line,
        line_management_options=line_management_options,
        assigned_operator_ids=assigned_operator_ids,
        available_operators=available_operators,
        is_operator_assigned=is_operator_assigned,   # added
    )

@app.route("/traps/<int:trap_id>", methods=["GET"])
@utils.login_required("Please log in to view trap details.")
def trap_catches(trap_id):
    from app.repository.trap_repository import get_trap_by_id
    trap = get_trap_by_id(trap_id)
    if trap is None:
        abort(404)
    catches = facade_repository.get_trap_catches(trap_id)
    for catch in catches:
        catch["recorded_by_name"] = f"{catch['first_name']} {catch['last_name']}"
    trap_data = dict(trap)
    trap_data['catches'] = catches if catches else []
    return render_template("trap_catches.html", title=f"Trap {trap_data['code']}", trap=trap_data, session=session)

@app.route("/catches", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Admin", "Coordinator")
def catches():
    page_size = 12
    page = request.args.get('page', 1, type=int)
    if page is None or page < 1:
        page = 1

    filters = {}
    if request.args.get('line_id'):
        filters['line_id'] = int(request.args.get('line_id'))
    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('species'):
        filters['species'] = request.args.get('species')
    if request.args.get('status'):
        filters['status'] = request.args.get('status')

    catches_data, total_count = facade_repository.get_all_catches_paginated(
        filters=filters,
        page=page,
        page_size=page_size,
    )

    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    if total_pages > 0 and page > total_pages:
        page = total_pages
        catches_data, total_count = facade_repository.get_all_catches_paginated(
            filters=filters,
            page=page,
            page_size=page_size,
        )

    start_index = (page - 1) * page_size + 1 if total_count else 0
    end_index = start_index + len(catches_data) - 1 if catches_data else 0

    lines = facade_repository.get_lines_with_assigned_users()
    species_list = facade_repository.get_distinct_species()
    statuses = facade_repository.get_distinct_statuses()

    return render_template(
        "catches.html",
        title="Trap Catches",
        catches=catches_data,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_page=page - 1,
        next_page=page + 1,
        start_index=start_index,
        end_index=end_index,
        lines=lines,
        species_list=species_list,
        statuses=statuses,
        current_filters=filters
    )


@app.route("/catches/export", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Admin", "Coordinator")
def export_catches_csv():
    filters = {}
    if request.args.get('line_id'):
        filters['line_id'] = int(request.args.get('line_id'))
    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('species'):
        filters['species'] = request.args.get('species')
    if request.args.get('status'):
        filters['status'] = request.args.get('status')

    catches = facade_repository.get_all_catches(filters)

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Catch ID", "Date time", "Trap Line", "Trap Code", "Latitude", "Longitude",
        "Species Caught", "Sex", "Maturity", "Status", "Rebaited", "Bait Type",
        "Trap Condition", "Strikes", "Notes", "Recorded By"
    ])

    for catch in catches:
        writer.writerow([
            catch["catch_id"],
            catch["date"].strftime("%d-%m-%Y %H:%M:%S") if catch["date"] else "",
            catch["line_name"],
            catch["trap_code"],
            catch["latitude"],
            catch["longitude"],
            catch["species_caught"],
            catch["sex"],
            catch["maturity"] or "",
            catch["status"],
            catch["rebaited"],
            catch["bait_type"],
            catch["trap_condition"],
            catch["strikes"],
            catch["notes"] or "",
            f"{catch['first_name'] or ''} {catch['last_name'] or ''}".strip() or "Unknown"
        ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=trap_catches.csv"}
    )


@app.route("/catch/edit/<int:catch_id>", methods=["GET", "POST"])
@utils.login_required()
@utils.roles_required("Operator", "Admin", "Observer")
def edit_catch(catch_id):
    catch = facade_repository.get_catch_by_id(catch_id)
    if not catch:
        abort(404)

    user_role = session.get("role")
    user_id = session.get("user_id")
    species_list = common_repository.get_species()
    status_list = common_repository.get_trap_status()
    bait_type_list = common_repository.get_bait_types()
    sex_list = common_repository.get_params_by_type("sex")
    maturity_list = common_repository.get_params_by_type("maturity")
    rebaited_list = common_repository.get_params_by_type("rebaited")
    trap_condition_list = common_repository.get_params_by_type("trap_condition")
    
    # Determine if user can edit this catch
    can_edit = False
    if user_role == "Operator" and catch["recorded_by"] == user_id:
        can_edit = True
    # Admin and Observer can only view, not edit

    max_date_value = datetime.now().strftime('%Y-%m-%dT%H:%M')

    if request.method == "POST":
        if not can_edit:
            flash("You do not have permission to edit this catch record.", "danger")
            return redirect(url_for("trap_catches", trap_id=catch["trap_id"]))
        
        date_str = request.form.get("date", "")
        species = request.form.get("species", "").strip()
        sex = request.form.get("sex", "").strip()
        maturity = request.form.get("maturity", "").strip()
        status = request.form.get("status", "").strip()
        rebaited = request.form.get("rebaited", "").strip()
        bait_type = request.form.get("bait_type", "").strip()
        trap_condition = request.form.get("trap_condition", "").strip()
        strikes = request.form.get("strikes", "0")
        notes = request.form.get("notes", "").strip()

        errors = False

        if not date_str:
            flash("Date is required.", "danger")
            errors = True
        if not species:
            flash("Species caught is required.", "danger")
            errors = True
        if not sex:
            flash("Sex is required.", "danger")
            errors = True
        if not status:
            flash("Status is required.", "danger")
            errors = True
        if not rebaited:
            flash("Rebaited status is required.", "danger")
            errors = True
        if not bait_type:
            flash("Bait type is required.", "danger")
            errors = True
        if not trap_condition:
            flash("Trap condition is required.", "danger")
            errors = True

        try:
            strikes_int = int(strikes)
            if strikes_int < 0:
                raise ValueError
        except ValueError:
            flash("Strikes must be a non-negative integer.", "danger")
            errors = True

        if errors:
            return render_template(
                "catch_form.html",
                catch=catch,
                date_value=date_str,
                max_date_value=max_date_value,
                can_edit=can_edit,
                mode="edit",
                title="Edit Catch Record",
                species_list=species_list,
                status_list=status_list,
                bait_type_list=bait_type_list,
                sex_list=sex_list,
                maturity_list=maturity_list,
                rebaited_list=rebaited_list,
                trap_condition_list=trap_condition_list,
            )

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            flash("Invalid date format.", "danger")
            return render_template(
                "catch_form.html",
                catch=catch,
                date_value=date_str,
                max_date_value=max_date_value,
                can_edit=can_edit,
                mode="edit",
                title="Edit Catch Record",
                species_list=species_list,
                status_list=status_list,
                bait_type_list=bait_type_list,
                sex_list=sex_list,
                maturity_list=maturity_list,
                rebaited_list=rebaited_list,
                trap_condition_list=trap_condition_list,
            )

        if date_obj > datetime.now():
            flash("Date and time cannot be in the future.", "danger")
            return render_template(
                "catch_form.html",
                catch=catch,
                date_value=date_str,
                max_date_value=max_date_value,
                can_edit=can_edit,
                mode="edit",
                title="Edit Catch Record",
                species_list=species_list,
                status_list=status_list,
                bait_type_list=bait_type_list,
                sex_list=sex_list,
                maturity_list=maturity_list,
                rebaited_list=rebaited_list,
                trap_condition_list=trap_condition_list,
            )

        data = {
            "date": date_obj,
            "species_caught": species,
            "sex": sex,
            "maturity": maturity if maturity else None,
            "status": status,
            "rebaited": rebaited,
            "bait_type": bait_type,
            "trap_condition": trap_condition,
            "strikes": strikes_int,
            "notes": notes if notes else None
        }

        try:
            facade_repository.update_catch(catch_id, data)
            flash("Catch record updated successfully.", "success")
            return redirect(url_for("trap_catches", trap_id=catch["trap_id"]))
        except Exception as e:
            flash(f"Failed to update catch record: {e}", "danger")

    # GET request: populate the form with current data
    # structured date input for datetime-local input field
    date_value = catch["date"].strftime("%d-%m-%Y %H:%M:%S") if catch["date"] else ""
    return render_template(
        "catch_form.html",
        catch=catch,
        date_value=date_value,
        max_date_value=max_date_value,
        can_edit=can_edit,
        mode="edit",
        title="Edit Catch Record",
        species_list=species_list,
        status_list=status_list,
        bait_type_list=bait_type_list,
        sex_list=sex_list,
        maturity_list=maturity_list,
        rebaited_list=rebaited_list,
        trap_condition_list=trap_condition_list,
    )


@app.route("/catches/chart", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Admin", "Coordinator")
def catches_chart():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    group_by = request.args.get("group_by", "week").strip()
    if group_by not in ("day", "week", "month", "year"):
        group_by = "week"

    # Apply a sensible default window only when both dates are missing.
    if not start_date and not end_date:
        today = datetime.now().date()
        lookback_days_by_group = {
            "day": 10,
            "week": 70,
            "month": 365,
            "year": 3650,
        }
        lookback_days = lookback_days_by_group.get(group_by, 70)
        start_date = (today - timedelta(days=lookback_days)).isoformat()
        end_date = today.isoformat()

    start_date_original = start_date
    end_date_original = end_date

    operator_id_raw = request.args.get("operator_id", "").strip()
    operator_id = int(operator_id_raw) if operator_id_raw.isdigit() else None

    role = session.get("role")

    selected_group_id_raw = request.args.get("group_id", "").strip()

    selected_group_id = int(selected_group_id_raw) if selected_group_id_raw.isdigit() else None
    
    trap_type = request.args.get("trap_type", "").strip() or None
    species = request.args.get("species", "").strip() or None

    groups = common_repository.get_all_active_groups()

    valid_group_ids = {g["group_id"] for g in groups}
    if selected_group_id is not None and selected_group_id not in valid_group_ids:
        selected_group_id = None

    operators = facade_repository.get_chart_operators(group_id=selected_group_id)
    if operator_id is not None and all(op["user_id"] != operator_id for op in operators):
        operator_id = None

    trap_types = facade_repository.get_distinct_trap_types()
    species_list = facade_repository.get_distinct_species()

    rows = facade_repository.get_trap_catches_summary_data(
        start_date=start_date or None,
        end_date=end_date or None,
        group_by=group_by,
        operator_id=operator_id,
        trap_type=trap_type,
        species=species,
        group_id=selected_group_id,
    )

    series_dict = {}
    for row in rows:
        line_name = row["line_name"]
        time_period = row["time_period"]
        total_catches = int(row["total_catches"])
        # Ensure datetime is UTC-aware, then convert to Unix timestamp (milliseconds)
        if time_period.tzinfo is None:
            time_period = time_period.replace(tzinfo=timezone.utc)
        timestamp_ms = int(time_period.timestamp() * 1000)
        if line_name not in series_dict:
            series_dict[line_name] = []
        series_dict[line_name].append([timestamp_ms, total_catches])

    series = [{"name": name, "data": data} for name, data in sorted(series_dict.items())]

    return render_template(
        "trap_catches_chart.html",
        title="Catches Summary",
        series_json=json.dumps(series),
        start_date= start_date_original,
        end_date=end_date_original,
        group_by=group_by,
        operators=operators,
        operator_id=operator_id,
        trap_types=trap_types,
        trap_type=trap_type,
        species_list=species_list,
        species=species,
        groups=groups,
        selected_group_id=selected_group_id,
    )


# ── US 1.01 ── Super Admin: manage groups ─────────────────────────────────────

@app.route('/superadmin/dashboard')
@utils.login_required_without_group_checking()
@utils.roles_required('Admin')
def sa_dashboard():
    current_user = user_repository.get_user_by_id(session.get('user_id'))
    if current_user is None:
        session.clear()
        flash('Your account could not be found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    dashboard = dashboard_repository.get_super_admin_dashboard_data()

    return render_template(
        'sa_dashboard.html',
        title='Super Admin Dashboard',
        current_user=current_user,
        dashboard=dashboard,
    )

@app.route('/superadmin/groups')
@utils.login_required_without_group_checking()
@utils.roles_required('Admin')
def sa_manage_groups():
    page_size = 9
    page = request.args.get('page', 1, type=int)
    if page is None or page < 1:
        page = 1

    search_query = request.args.get('q', '').strip()
    all_groups = core_repository.get_all_groups_for_admin()

    if search_query:
        needle = search_query.lower()
        groups = [
            group for group in all_groups
            if needle in (group.get('name') or '').lower()
            or needle in (group.get('description') or '').lower()
            or needle in (group.get('created_by_name') or '').lower()
            or needle in (group.get('status') or '').lower()
        ]
    else:
        groups = all_groups

    filtered_count = len(groups)
    total_pages = (filtered_count + page_size - 1) // page_size if filtered_count else 0

    if total_pages > 0 and page > total_pages:
        page = total_pages

    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paged_groups = groups[start_index:end_index]

    start_display = start_index + 1 if filtered_count else 0
    end_display = min(end_index, filtered_count) if filtered_count else 0

    return render_template(
        'sa_manage_groups.html',
        groups=paged_groups,
        search_query=search_query,
        total_groups=len(all_groups),
        filtered_count=filtered_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_page=page - 1,
        next_page=page + 1,
        start_display=start_display,
        end_display=end_display,
    )


@app.route('/superadmin/groups/new', methods=['GET', 'POST'])
@utils.login_required_without_group_checking()
@utils.roles_required('Admin')
def sa_create_group():
    coordinator_options = core_repository.get_active_users_not_in_group()
    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public   = request.form.get('is_public') == 'true'
        operational_area = request.form.get('operational_area', '').strip()
        coordinator_id = request.form.get('coordinator_id', '').strip()
        if not name:
            flash('Group name is required.', 'danger')
            return render_template('sa_group_form.html', action='create', group=None, coordinator_options=coordinator_options)
        # Handle image upload
        image_url = None
        file = request.files.get('group_image')
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Only JPG and PNG images are allowed.', 'danger')
                return render_template('sa_group_form.html', action='create', group=None, coordinator_options=coordinator_options)
            # Check file size before saving (2 MB limit)
            if file.content_length and file.content_length > 2 * 1024 * 1024:
                flash('File is too large. Maximum file size is 2 MB.', 'danger')
                return render_template('sa_group_form.html', action='create', group=None, coordinator_options=coordinator_options)
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'groups', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            image_url = url_for('static', filename=f'uploads/groups/{filename}')
        try:
            group_id = core_repository.create_group(name, description, image_url, is_public, session['user_id'], operational_area)
            if coordinator_id.isdigit():
                core_repository.appoint_coordinator(group_id, int(coordinator_id))
            flash(f'Group "{name}" created successfully.', 'success')
            try:
                badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.CREATE_GROUP, 'Created group')
            except Exception:
                pass
            return redirect(url_for('sa_manage_groups'))
        except Exception as e:
            flash(f'Error creating group: {e}', 'danger')
    return render_template('sa_group_form.html', action='create', group=None, coordinator_options=coordinator_options)


@app.route('/superadmin/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@utils.login_required_without_group_checking()
@utils.roles_required('Admin')
def sa_edit_group(group_id):
    allowed_group_statuses = {'Active', 'Pending', 'Rejected', 'Inactive'}

    group = core_repository.get_group_by_id(group_id)
    if not group:
        flash('Group not found.', 'danger')
        return redirect(url_for('sa_manage_groups'))
    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public   = request.form.get('is_public') == 'true'
        group_status = request.form.get('status', '').strip() or group.get('status')
        charitable_name             = request.form.get('charitable_name', '').strip() or None
        charity_registration_number = request.form.get('charity_registration_number', '').strip() or None
        donation_description        = request.form.get('donation_description', '').strip() or None
        if not name:
            flash('Group name is required.', 'danger')
            coordinators = core_repository.get_coordinators_for_group(group_id)
            eligible = core_repository.get_active_users_not_in_group(group_id)
            return render_template('sa_group_form.html', action='edit', group=group,
                                   coordinators=coordinators, eligible_users=eligible)
        if group_status not in allowed_group_statuses:
            flash('Invalid group status selected.', 'danger')
            coordinators = core_repository.get_coordinators_for_group(group_id)
            eligible = core_repository.get_active_users_not_in_group(group_id)
            return render_template('sa_group_form.html', action='edit', group=group,
                                   coordinators=coordinators, eligible_users=eligible)
        # Handle image deletion or upload - keep existing if no new file uploaded
        # If the user clicked the Delete button (name=delete_image), remove the file and clear image_url
        image_url = group['image_url']
        if request.form.get('delete_image'):
            # attempt to remove the existing file from disk
            try:
                if image_url:
                    # image_url is the static URL returned by url_for, e.g. /static/uploads/groups/filename
                    filename = os.path.basename(image_url)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'groups', filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                image_url = None
                flash('Group image deleted.', 'success')
            except Exception as e:
                flash(f'Error deleting image: {e}', 'danger')
                return render_template('sa_group_form.html', action='edit', group=group)
        file = request.files.get('group_image')
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Only JPG and PNG images are allowed.', 'danger')
                coordinators = core_repository.get_coordinators_for_group(group_id)
                eligible = core_repository.get_active_users_not_in_group(group_id)
                return render_template('sa_group_form.html', action='edit', group=group,
                                       coordinators=coordinators, eligible_users=eligible)
            # Check file size before saving (2 MB limit)
            if file.content_length and file.content_length > 2 * 1024 * 1024:
                flash('File is too large. Maximum file size is 2 MB.', 'danger')
                coordinators = core_repository.get_coordinators_for_group(group_id)
                eligible = core_repository.get_active_users_not_in_group(group_id)
                return render_template('sa_group_form.html', action='edit', group=group,
                                       coordinators=coordinators, eligible_users=eligible)
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'groups', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            image_url = url_for('static', filename=f'uploads/groups/{filename}')
        core_repository.update_group(group_id, name, description, image_url, is_public, group_status,
                                     charitable_name, charity_registration_number, donation_description)
        flash('Group updated successfully.', 'success')
        return redirect(url_for('sa_manage_groups'))
    # Provide coordinators and eligible users so SA can manage coordinators from the Edit page
    coordinators = core_repository.get_coordinators_for_group(group_id)
    eligible     = core_repository.get_active_users_not_in_group(group_id)
    return render_template('sa_group_form.html', action='edit', group=group,
                           coordinators=coordinators, eligible_users=eligible)


@app.route('/apply-group', methods=['GET', 'POST'])
@utils.login_required_without_group_checking()
def apply_group():
    """Allow any logged-in user to submit a new group application for SA review."""
    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public   = request.form.get('is_public') == 'true'

        if not name:
            flash('Group name is required.', 'danger')
            return render_template('apply_group.html')

        try:
            core_repository.create_group_application(
                name, description, is_public, session['user_id']
            )
            flash('Your group application has been submitted and is awaiting Super Admin approval.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Error submitting application: {e}', 'danger')

    return render_template('apply_group.html')





#***********************************************************************************************************************
# Super Admin Lookup Table (Parameter) Management Routes
# Manages system-wide parameters: trap types, bait types, species, trap status, bait station types
#***********************************************************************************************************************

@app.route('/superadmin/parameters', methods=['GET'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_manage_parameters():
    """Super Admin dashboard for managing system parameters (lookup tables)."""
    # Map lookup tables to display info
    lookup_tables_info = {
        'Trap_Status': {'display': 'Trap Status', 'icon': '📋'},
        'Trap_Types': {'display': 'Trap Types', 'icon': '🪤'},
        'Bait_Types': {'display': 'Bait Types', 'icon': '🌿'},
        'Species': {'display': 'Species', 'icon': '🐾'},
        'Bait_Station_Types': {'display': 'Bait Station Types', 'icon': '🏗️'},
        'Knowledge_Categories': {'display': 'Knowledge Categories', 'icon': '🏷️'},
    }
    
    param_types = []
    for table_key, info in lookup_tables_info.items():
        try:
            if table_key == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                records = knowhub_repository.get_knowledge_categories()
                param_types.append({
                    'param_type': table_key,
                    'display_name': info['display'],
                    'value_count': len(records),
                    'icon': info['icon']
                })
            else:
                records = common_repository.get_lookup_table_all_records(table_key)
                active_count = len([r for r in records if r['status'] == 'Active'])
                param_types.append({
                    'param_type': table_key,
                    'display_name': info['display'],
                    'value_count': len(records),
                    'active_count': active_count,
                    'icon': info['icon']
                })
        except Exception:
            pass
    
    return render_template('admin_params.html', title='System Parameters', param_types=param_types, is_sa=True)


@app.route('/superadmin/parameters/<table_name>', methods=['GET'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_manage_parameters_detail(table_name):
    """Manage specific lookup table records."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types', 'Knowledge_Categories']
    if table_name not in valid_tables:
        flash('Invalid parameter table.', 'danger')
        return redirect(url_for('admin_params'))
    
    try:
        if table_name == 'Knowledge_Categories':
            from app.repository import knowhub_repository
            records = knowhub_repository.get_knowledge_categories()
            converted_values = [
                {'id': r['category_id'], 'param_value': r['name'], 'status': None, 'in_use': knowhub_repository.is_knowledge_category_in_use(r['category_id'])}
                for r in records
            ]
            display_name = 'Knowledge Categories'
        else:
            records = common_repository.get_lookup_table_all_records(table_name)

            # Convert to admin_params format (name -> param_value, add status field)
            converted_values = [
                {'id': r['id'], 'param_value': r['name'], 'status': r['status']}
                for r in records
            ]

            display_name = table_name.replace('_', ' ')
        
        return render_template(
            'admin_params_detail.html',
            title=f'Manage: {display_name}',
            param_type=table_name,
            display_name=display_name,
            values=converted_values,
            is_sa=True,
            is_lookup_table=True
        )
    except Exception as e:
        flash(f'Error loading {table_name}: {str(e)}', 'danger')
        return redirect(url_for('admin_params'))


@app.route('/superadmin/parameters/<table_name>/add', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_add_parameter(table_name):
    """Add a new record to a lookup table."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types', 'Knowledge_Categories']
    if table_name not in valid_tables:
        flash('Invalid parameter table.', 'danger')
        return redirect(url_for('admin_params'))
    
    name = request.form.get('new_value', '').strip()
    if not name:
        flash('Name cannot be empty.', 'danger')
    else:
        try:
            if table_name == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                knowhub_repository.add_knowledge_category(name)
            else:
                common_repository.add_lookup_table_record(table_name, name)
            flash(f'Added "{name}" successfully.', 'success')
        except ValueError as e:
            if 'already exists' in str(e):
                flash('This value already exists (case-insensitive).', 'warning')
            else:
                flash(f'Error: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Could not add value: {str(e)}', 'danger')
    
    return redirect(url_for('admin_params_detail', param_type=table_name))


@app.route('/superadmin/parameters/<table_name>/update', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_update_parameter(table_name):
    """Update a lookup table record."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types', 'Knowledge_Categories']
    if table_name not in valid_tables:
        flash('Invalid parameter table.', 'danger')
        return redirect(url_for('admin_params'))
    
    record_id_raw = request.form.get('record_id', '').strip()
    old_name = request.form.get('old_value', '').strip()
    new_name = request.form.get('new_value', '').strip()
    
    if not record_id_raw or not record_id_raw.isdigit():
        flash('Invalid record ID.', 'danger')
    elif not new_name:
        flash('New name cannot be empty.', 'danger')
    elif old_name == new_name:
        flash('New name is the same as current name — no change made.', 'warning')
    else:
        try:
            if table_name == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                knowhub_repository.update_knowledge_category(int(record_id_raw), new_name)
            else:
                common_repository.update_lookup_table_record(table_name, int(record_id_raw), new_name)
            flash(f'Renamed "{old_name}" to "{new_name}".', 'success')
        except ValueError as e:
            if 'already exists' in str(e):
                flash('A record with this name already exists (case-insensitive).', 'warning')
            elif 'duplicate_category' in str(e):
                flash('A record with this name already exists (case-insensitive).', 'warning')
            else:
                flash(f'Error: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Could not update record: {str(e)}', 'danger')
    
    return redirect(url_for('admin_params_detail', param_type=table_name))


@app.route('/superadmin/parameters/<table_name>/delete', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_delete_parameter(table_name):
    """Delete a lookup table record."""
    valid_tables = ['Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types', 'Knowledge_Categories']
    if table_name not in valid_tables:
        flash('Invalid parameter table.', 'danger')
        return redirect(url_for('admin_params'))
    
    record_id_raw = request.form.get('value_id', '').strip()
    record_name = request.form.get('value', '').strip()
    
    if not record_id_raw or not record_id_raw.isdigit():
        flash('Invalid record ID.', 'danger')
    else:
        try:
            # Check if record is in use
            if table_name == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                if knowhub_repository.is_knowledge_category_in_use(int(record_id_raw)):
                    flash(f'Cannot delete: "{record_name}" is used in existing records.', 'warning')
                else:
                    knowhub_repository.delete_knowledge_category(int(record_id_raw))
                    flash(f'Deleted "{record_name}".', 'success')
            elif common_repository.is_lookup_table_record_in_use(table_name, int(record_id_raw)):
                flash(f'Cannot delete: "{record_name}" is used in existing records.', 'warning')
            else:
                common_repository.delete_lookup_table_record(table_name, int(record_id_raw))
                flash(f'Deleted "{record_name}".', 'success')
        except Exception as e:
            flash(f'Could not delete record: {str(e)}', 'danger')
    
    return redirect(url_for('admin_params_detail', param_type=table_name))

    return render_template('apply_group.html')


@app.route('/superadmin/applications')
@utils.login_required()
@utils.roles_required('Admin')
def sa_group_applications():
    applications = core_repository.get_pending_group_applications()
    return render_template('sa_applications.html', applications=applications)


@app.route('/superadmin/applications/<int:group_id>/approve', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_approve_application(group_id):
    group = core_repository.get_group_by_id(group_id)
    if not group:
        flash('Application not found.', 'danger')
        return redirect(url_for('sa_group_applications'))

    # Attempt an atomic status change; prevents duplicate processing/race conditions
    updated = core_repository.set_group_status(group_id, 'Active')
    if not updated:
        flash('Application has already been processed (approved or rejected).', 'warning')
        return redirect(url_for('sa_group_applications'))

    # Assign the applicant (creator) as Group Coordinator so they see the group
    try:
        creator_id = group.get('created_by')
        if creator_id:
            core_repository.appoint_coordinator(group_id, creator_id)
            # Notify applicant of approval
            try:
                message = f'Your group application "{group.get("name")}" has been approved. You have been assigned as Group Coordinator.'
                notification_repository.create_user_notification(creator_id, message)
            except Exception:
                pass
    except Exception:
        # Non-fatal: group is activated even if appointment fails
        pass

    flash(f'Group "{group["name"]}" has been approved and the applicant assigned as Coordinator.', 'success')
    return redirect(url_for('sa_group_applications'))


@app.route('/superadmin/applications/<int:group_id>/reject', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_reject_application(group_id):
    group = core_repository.get_group_by_id(group_id)
    if not group:
        flash('Application not found.', 'danger')
        return redirect(url_for('sa_group_applications'))

    updated = core_repository.set_group_status(group_id, 'Rejected')
    if not updated:
        flash('Application has already been processed (approved or rejected).', 'warning')
        return redirect(url_for('sa_group_applications'))

    # Notify applicant of rejection
    try:
        creator_id = group.get('created_by')
        if creator_id:
            message = f'Your group application "{group.get("name")}" has been rejected by the Super Admin.'
            notification_repository.create_user_notification(creator_id, message)
    except Exception:
        pass

    flash(f'Group "{group["name"]}" has been rejected.', 'warning')
    return redirect(url_for('sa_group_applications'))


@app.route('/superadmin/groups/<int:group_id>/coordinators')
@utils.login_required()
@utils.roles_required('Admin')
def sa_manage_coordinators(group_id):
    group = core_repository.get_group_by_id(group_id)
    if not group:
        flash('Group not found.', 'danger')
        return redirect(url_for('sa_manage_groups'))
    coordinators = core_repository.get_coordinators_for_group(group_id)
    eligible     = core_repository.get_active_users_not_in_group(group_id)
    return render_template('sa_manage_coordinators.html',
                           group=group, coordinators=coordinators, eligible_users=eligible)


@app.route('/superadmin/groups/<int:group_id>/coordinators/appoint', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_appoint_coordinator(group_id):
    user_id = request.form.get('user_id', type=int)
    if not user_id:
        flash('Please select a user to appoint.', 'danger')
        return redirect(url_for('sa_manage_coordinators', group_id=group_id))
    core_repository.appoint_coordinator(group_id, user_id)
    try:
        notification_repository.notify_coordinator_appointed(user_id, group_id, session.get('user_id'))
    except Exception:
        # Do not fail the operation for notification issues
        pass
    flash('Coordinator appointed successfully.', 'success')
    return redirect(url_for('sa_edit_group', group_id=group_id))


@app.route('/superadmin/groups/<int:group_id>/coordinators/<int:user_id>/remove', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_remove_coordinator(group_id, user_id):
    core_repository.remove_coordinator(group_id, user_id)
    flash('Coordinator removed.', 'warning')
    return redirect(url_for('sa_edit_group', group_id=group_id))


# ── US 1.02 ── Group Coordinator: visibility & join requests ──────────────────

@app.route('/coordinator/join-requests')
@utils.login_required()
@utils.roles_required('Coordinator')
def coordinator_join_requests():
    group_id = session.get('group_id')
    if not group_id:
        flash('No group selected.', 'danger')
        return redirect(url_for('admin_dashboard'))
    group    = core_repository.get_group_by_id(group_id)
    requests = core_repository.get_pending_join_requests(group_id)
    return render_template('coordinator_join_requests.html', group=group, join_requests=requests)


@app.route('/coordinator/group/visibility', methods=['POST'])
@utils.login_required()
@utils.roles_required('Coordinator')
def coordinator_set_visibility():
    group_id  = session.get('group_id')
    is_public = request.form.get('is_public') == 'true'
    if not group_id:
        flash('No group selected.', 'danger')
        return redirect(url_for('admin_dashboard'))
    core_repository.set_group_visibility(group_id, is_public)
    flash(f'Group visibility set to {"Public" if is_public else "Private"}.', 'success')
    return redirect(url_for('coordinator_join_requests'))


@app.route('/coordinator/join-requests/<int:membership_id>/approve', methods=['POST'])
@utils.login_required()
@utils.roles_required('Coordinator')
def coordinator_approve_request(membership_id):
    core_repository.approve_join_request(membership_id)
    flash('Join request approved. User added as Observer.', 'success')
    return redirect(url_for('coordinator_join_requests'))


@app.route('/coordinator/join-requests/<int:membership_id>/reject', methods=['POST'])
@utils.login_required()
@utils.roles_required('Coordinator')
def coordinator_reject_request(membership_id):
    core_repository.reject_join_request(membership_id)
    flash('Join request rejected.', 'warning')
    return redirect(url_for('coordinator_join_requests'))


# ── Super Admin: manage join requests ──────────────────────────────────────────

@app.route('/superadmin/join-requests')
@utils.login_required()
@utils.roles_required('Admin')
def sa_join_requests():
    join_requests = core_repository.get_all_pending_join_requests()
    return render_template('sa_join_requests.html', join_requests=join_requests)


@app.route('/superadmin/join-requests/<int:membership_id>/approve', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_approve_join_request(membership_id):
    core_repository.approve_join_request(membership_id)
    flash('Join request approved. User added as Observer.', 'success')
    return redirect(url_for('sa_join_requests'))


@app.route('/superadmin/join-requests/<int:membership_id>/reject', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def sa_reject_join_request(membership_id):
    core_repository.reject_join_request(membership_id)
    flash('Join request rejected.', 'warning')
    return redirect(url_for('sa_join_requests'))
