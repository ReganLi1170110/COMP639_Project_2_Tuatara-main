# Admin Routes
# Handles administrative tasks including user management, line and trap configuration,
# and system parameter maintenance.

from flask import abort, render_template, request, redirect, url_for, flash, session
from app.db import db
from app.repository import facade_repository, user_repository, operator_repository, notification_repository, trap_repository, bait_station_repository, badge_repository
from app import flask_app as app
import app.utils as utils

@app.route('/admin/fulfillment', methods=['GET', 'POST'])
@utils.login_required('Please log in to access fulfillment management.')
@utils.roles_required('Admin')
def admin_fulfillment():
    if request.method == 'POST':
        action = request.form.get('action', '').strip()
        redemption_id = request.form.get('redemption_id', '').strip()
        if action == 'mark_shipped' and redemption_id.isdigit():
            updated = badge_repository.mark_badge_redemption_shipped(int(redemption_id))
            if updated:
                flash('Badge redemption marked as shipped.', 'success')
            else:
                flash('Unable to mark this request as shipped. It may already be shipped or no longer exists.', 'danger')
        else:
            flash('Invalid fulfillment request.', 'danger')
        return redirect(url_for('admin_fulfillment'))

    pending_redemptions = badge_repository.get_pending_badge_redemptions()
    shipped_redemptions = badge_repository.get_shipped_badge_redemptions()
    return render_template(
        'admin/fulfillment.html',
        title='Badge Fulfillment',
        pending_redemptions=pending_redemptions,
        shipped_redemptions=shipped_redemptions,
    )

# Admin routes for managing users, lines, traps, and control parameters.
#***********************************************************************************************************************
# admin dashboard
@app.route("/coordinator_dashboard", methods=["GET"])
@utils.login_required("Please log in to access the admin dashboard.")
@utils.roles_required("Coordinator")
def admin_dashboard():
    from app.repository import core_repository
    current_user = user_repository.get_user_by_id(session["user_id"])
    if current_user is None:
        session.clear()
        flash("Your account could not be found. Please log in again.", "danger")
        return redirect(url_for("login"))
    group_id = session.get("group_id")
    dashboard = facade_repository.get_admin_dashboard_data(group_id)

    group_info = core_repository.get_group_by_id(group_id) if group_id else None
    group_members = core_repository.get_group_members(group_id) if group_id else []
    # Donation summary for coordinator's group
    donation_summary = None
    if group_id:
        try:
            from app.repository import donation_repository
            donation_summary = donation_repository.get_donation_summary_for_group(group_id)
        except Exception:
            donation_summary = None
    # Donation records for display on dashboard
    donation_records = []
    if group_id:
        try:
            from app.repository import donation_repository
            donation_records = donation_repository.get_donations_for_group(group_id, limit=50)
        except Exception:
            donation_records = []

    return render_template(
        "admin_dashboard.html",
        title="Admin Dashboard",
        current_user=current_user,
        dashboard=dashboard,
        group_info=group_info,
        group_members=group_members,
        donation_summary=donation_summary,
        donation_records=donation_records,
    )


@app.route('/coordinator/donations', methods=['GET'])
@utils.login_required('Please log in to view donations.')
@utils.roles_required('Coordinator')
def coordinator_donations():
    from app.repository import core_repository, donation_repository
    group_id = session.get('group_id')
    if not group_id:
        abort(404)
    group_info = core_repository.get_group_by_id(group_id)
    donation_records = donation_repository.get_donations_for_group(group_id)
    total_amount = sum(d['amount'] for d in donation_records)
    return render_template('donations_popup.html', group_info=group_info, donation_records=donation_records, total_amount=total_amount)

@app.route('/coordinator/donations/<int:donation_id>/receipt', methods=['GET'])
@utils.login_required('Please log in to view receipts.')
@utils.roles_required('Coordinator', 'Admin')
def donation_receipt(donation_id):
    """Generate and display a printable donation receipt."""
    from app.repository import donation_repository, core_repository
    from datetime import datetime, timezone

    donation = donation_repository.get_donation_by_id(donation_id)
    if not donation:
        abort(404)

    # AC3 – no receipt for anonymous donations
    if donation.get('is_anonymous'):
        abort(403)

    # Only allow coordinator to view receipts for their own group (Super Admin can view all)
    user_role = session.get('role')
    if user_role != 'Admin':
        group_id = session.get('group_id')
        if group_id is not None:
            try:
                group_id = int(group_id)
            except (ValueError, TypeError):
                pass
        if donation.get('group_id') and donation.get('group_id') != group_id:
            abort(403)

    group = None
    if donation.get('group_id'):
        group = core_repository.get_group_by_id(donation['group_id'])

    from app.repository import group_settings_repository
    site_logo = group_settings_repository.get_site_setting('receipt_logo', '')
    site_footer = group_settings_repository.get_site_setting('receipt_footer', '')

    now = datetime.now().strftime('%Y-%m-%dT%H:%M')
    return render_template('donation_receipt.html', donation=donation, group=group, now=now, site_logo=site_logo, site_footer=site_footer)


#***********************************************************************************************************************
# User management
@app.route("/users", methods=["GET"])
@utils.login_required("Please log in to view users.")
@utils.roles_required("Coordinator")
def users():
    page_size = 12
    page = request.args.get("page", 1, type=int)
    if page is None or page < 1:
        page = 1

    admin_options = user_repository.get_user_admin_options()
    valid_roles = set(admin_options["roles"])
    valid_statuses = set(admin_options["account_statuses"])

    allowed_sort_fields = {"username", "email", "role", "account_status"}
    sort_by = request.args.get("sort_by", "username").strip()
    if sort_by not in allowed_sort_fields:
        sort_by = "username"

    sort_dir = request.args.get("sort_dir", "asc").strip().lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "asc"

    role_filter = request.args.get("role", "").strip()
    if role_filter not in valid_roles:
        role_filter = ""

    status_filter = request.args.get("status", "").strip()
    if status_filter not in valid_statuses:
        status_filter = ""

    search_term = request.args.get("q", "").strip()

    users_data, total_count = facade_repository.get_users_with_assigned_lines_paginated(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        role_filter=role_filter,
        status_filter=status_filter,
        search_term=search_term,
    )

    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    if total_pages > 0 and page > total_pages:
        page = total_pages
        users_data, total_count = facade_repository.get_users_with_assigned_lines_paginated(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            role_filter=role_filter,
            status_filter=status_filter,
            search_term=search_term,
        )

    start_index = (page - 1) * page_size + 1 if total_count else 0
    end_index = start_index + len(users_data) - 1 if users_data else 0

    return render_template(
        "users.html",
        title="Users",
        users=users_data,
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
        admin_options=admin_options,
        can_manage_users=True,
        selected_sort_by=sort_by,
        selected_sort_dir=sort_dir,
        selected_role=role_filter,
        selected_status=status_filter,
        search_query=search_term,
        current_user_id=session.get("user_id"),
    )

#************************************************************************************************************************
# Admin update user role and account status
@app.route("/users/<int:user_id>/admin-update", methods=["POST"])
@utils.login_required("Please log in to access the admin update feature.")
@utils.roles_required("Coordinator")
def user_admin_update(user_id):
    from app.repository import core_repository, notification_repository

    current_user_id = session.get("user_id")
    group_id = session.get("group_id")

    # Cannot edit yourself
    if user_id == current_user_id:
        flash("You cannot change your own role or status.", "danger")
        return redirect(url_for("users"))

    target_user = user_repository.get_user_by_id(user_id)
    if target_user is None:
        abort(404)

    # Verify target user belongs to coordinator's group
    group_members = core_repository.get_group_members(group_id)
    member_ids = [m["user_id"] for m in group_members]
    if user_id not in member_ids:
        flash("You can only manage users within your own group.", "danger")
        return redirect(url_for("users"))

    new_role = request.form.get("role", "").strip()
    account_status = request.form.get("account_status", "").strip()
    redirect_target = request.form.get("redirect_to", "profile").strip()

    # Cannot assign Coordinator role
    if new_role in ("Coordinator"):
        flash("You cannot assign the Coordinator role.", "danger")
        return redirect(url_for("users"))

    # Get old role for notification
    old_role = next((m["role"] for m in group_members if m["user_id"] == user_id), "")

    # Update role in Group_Members and account_status in Users
    core_repository.update_member_role(group_id, user_id, new_role, account_status)

    # Notify user if role changed
    if new_role and new_role != old_role:
        try:
            notification_repository.notify_user_role_changed(user_id, new_role, current_user_id, group_id)
        except Exception:
            pass

    flash("User updated successfully.", "success")

    if redirect_target == "users":
        return redirect(url_for("users"))
    return redirect(url_for("user_profile", user_id=user_id))

#***********************************************************************************************************************
# Line and trap management  
@app.route("/coordinator/lines/create", methods=["POST"])
@utils.login_required("Please log in to create a line.")
@utils.roles_required("Coordinator")
def admin_create_line():
    name = request.form.get("name", "").strip()
    line_type = request.form.get("line_type", "Trap").strip()
    line_status = request.form.get("line_status", "Pending").strip()

    line_management_options = facade_repository.get_line_management_options()
    valid_statuses = line_management_options["line_statuses"]
    if line_status not in valid_statuses:
        line_status = "Pending"

    if not name:
        flash("Line name is required.", "danger")
        return redirect(url_for("lines"))

    try:
        line_id = facade_repository.create_line(name, line_type, line_status)
        flash("Line created successfully.", "success")
        try:
            badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.CREATE_LINE, 'Created line')
        except Exception:
            pass
        return redirect(url_for("line_detail", line_id=line_id))
    except Exception:
        flash("Could not create line. Make sure the name is unique.", "danger")
        return redirect(url_for("lines"))

#***********************************************************************************************************************
# Admin update line details (name, status)
@app.route("/admin/lines/<int:line_id>/update", methods=["POST"])
@utils.login_required("Please log in to update a line.")
@utils.roles_required("Coordinator")
def admin_update_line(line_id):
    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    name = request.form.get("name", "").strip()
    line_type = request.form.get("line_type", line_data["line_type"]).strip()
    line_status = request.form.get("line_status", "").strip()

    line_management_options = facade_repository.get_line_management_options()
    valid_statuses = line_management_options["line_statuses"]

    if not name:
        flash("Line name is required.", "danger")
    elif line_status not in valid_statuses:
        flash("Invalid line status selected.", "danger")
    else:
        try:
            facade_repository.update_line(line_id, name, line_type, line_status)
            flash("Line updated successfully.", "success")
            try:
                from app.repository import badge_repository
                badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.LINE_MAINTENANCE, 'Line maintenance')
            except Exception:
                pass
        except Exception:
            flash("Could not update line. Make sure the name is unique.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#************************************************************************************************************************
# Admin retire line (set to inactive)
@app.route("/admin/lines/<int:line_id>/retire", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_retire_line(line_id):
    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    facade_repository.retire_line(line_id)
    flash("Line retired (set to inactive).", "success")
    return redirect(url_for("lines"))


#***********************************************************************************************************************
# Add operator to line with different modes
@app.route("/admin/lines/<int:line_id>/operators/add", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_add_operator_to_line(line_id):
    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    current_group_id = session.get("group_id")
    if current_group_id is None or line_data.get("group_id") != int(current_group_id):
        flash("You can only manage operators for lines in your selected group.", "danger")
        return redirect(url_for("lines"))

    operator_id_raw = request.form.get("operator_id", "").strip()
    if not operator_id_raw.isdigit():
        flash("Please select a valid operator.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    operator_id = int(operator_id_raw)
    action_mode = request.form.get("action_mode", "add").strip()
    replace_specific_operator_id_raw = request.form.get("replace_specific_operator_id", "").strip()
    replace_all_operators = request.form.get("replace_all_operators", "").strip() == "true"
    
    # Parse replace_specific_operator_id if provided
    replace_specific_operator_id = None
    if replace_specific_operator_id_raw.isdigit():
        replace_specific_operator_id = int(replace_specific_operator_id_raw)
    
    try:
        result = operator_repository.handle_operator_assignment_with_notifications(
            line_id=line_id,
            line_name=line_data["line_name"],
            new_operator_id=operator_id,
            action_mode=action_mode,
            existing_operators=line_data["operators"],
            admin_user_id=session["user_id"],
            replace_specific_operator_id=replace_specific_operator_id,
            replace_all_operators=replace_all_operators,
        )
        
        if result["success"]:
            flash(result["message"], "success")
        else:
            flash(result["message"], "warning")
    except Exception as e:
        # Log full exception for diagnostics
        app.logger.exception("Error assigning operator to line %s: %s", line_id, e)
        # Re-check whether the operator is actually assigned; notify user accordingly
        try:
            latest_line = facade_repository.get_line_detail(line_id)
            assigned_ids = {op["user_id"] for op in latest_line.get("operators", [])}
            if operator_id in assigned_ids:
                flash("Operator was assigned but notifications failed.", "warning")
            else:
                flash("Could not assign operator.", "danger")
        except Exception:
            flash("Could not assign operator.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))
#*****************************************************************************************************************
# Admin remove operator from line (with notifications)
@app.route("/admin/lines/<int:line_id>/operators/<int:operator_id>/remove", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_remove_operator_from_line(line_id, operator_id):

    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    current_group_id = session.get("group_id")
    if current_group_id is None or line_data.get("group_id") != int(current_group_id):
        flash("You can only manage operators for lines in your selected group.", "danger")
        return redirect(url_for("lines"))

    try:
        removed = facade_repository.remove_operator_from_line(line_id, operator_id)
        if removed:
            try:
                notification_repository.create_line_assignment_notifications(
                    line_id=line_id,
                    line_name=line_data["line_name"],
                    admin_name=session.get("user_name", "Administrator"),
                    removed_operator_ids={operator_id}
                )
            except Exception as e:
                app.logger.exception("Failed to send removal notification for operator %s on line %s: %s", operator_id, line_id, e)
                # Notification failure shouldn't mask the successful removal; inform user accordingly
                flash("Operator was removed but notification sending failed.", "warning")
            else:
                flash("Operator removed from line.", "success")
        else:
            flash("Operator was not assigned to this line.", "warning")
    except Exception as e:
        app.logger.exception("Error removing operator %s from line %s: %s", operator_id, line_id, e)
        # Re-check whether the operator was actually removed despite the exception
        try:
            latest_line = facade_repository.get_line_detail(line_id)
            assigned_ids = {op["user_id"] for op in latest_line.get("operators", [])}
            if operator_id not in assigned_ids:
                flash("Operator was removed but an error occurred while processing notifications.", "warning")
            else:
                flash("Could not remove operator assignment.", "danger")
        except Exception:
            flash("Could not remove operator assignment.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#***********************************************************************************************************************
# Admin add trap to line
@app.route("/admin/lines/<int:line_id>/traps/create", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_create_trap(line_id):
    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    code = request.form.get("code", "").strip()
    trap_type = request.form.get("trap_type", "").strip()
    latitude_raw = request.form.get("latitude", "").strip()
    longitude_raw = request.form.get("longitude", "").strip()

    options = facade_repository.get_line_management_options()
    valid_trap_types = options["trap_types"]
    trap_type_options = trap_repository.get_trap_types()

    if not code:
        flash("Trap code is required.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if trap_repository.trap_code_exists_exact(code):
        flash("Trap code already exists. Please use a different code.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if not trap_type:
        flash("Trap type is required.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if valid_trap_types and trap_type not in valid_trap_types:
        flash("Invalid trap type selected.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    selected_trap_type = next((tt for tt in trap_type_options if tt["name"] == trap_type), None)
    if selected_trap_type is None:
        flash("Invalid trap type selected.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except ValueError:
        flash("Latitude and longitude must be valid numbers.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))
    if not utils.is_within_new_zealand(latitude, longitude):
        flash(
            "Trap location must be in New Zealand. Most locations should use latitude between -48.5 and -33.5 and longitude between 166.0 and 179.5. For Chatham Islands, use latitude between -45.0 and -43.0 and longitude between -177.0 and -175.0.",
            "danger",
        )
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        facade_repository.add_trap_to_line(line_id, code, selected_trap_type["id"], latitude, longitude)
        flash("Trap added successfully.", "success")
        try:
            badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.ADD_TRAP, 'Added trap')
        except Exception:
            pass
    except Exception:
        flash("Could not add trap. Make sure the code is unique and the trap type is valid.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#***********************************************************************************************************************
# Admin update trap details and status
@app.route("/admin/traps/<int:trap_id>/update", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_update_trap(trap_id):
    line_id_raw = request.form.get("line_id", "").strip()
    trap_type = request.form.get("trap_type", "").strip()
    latitude_raw = request.form.get("latitude", "").strip()
    longitude_raw = request.form.get("longitude", "").strip()
    trap_status = request.form.get("trap_status", "").strip()

    trap_data = trap_repository.get_trap_by_id(trap_id)
    if trap_data is None:
        abort(404)

    line_id = trap_data["line_id"]
    if line_id_raw.isdigit():
        line_id = int(line_id_raw)

    options = facade_repository.get_line_management_options()
    valid_trap_types = options["trap_types"]
    trap_type_options = trap_repository.get_trap_types()

    if not trap_type:
        flash("Trap type is required.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if valid_trap_types and trap_type not in valid_trap_types:
        flash("Invalid trap type selected.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    selected_trap_type = next((tt for tt in trap_type_options if tt["name"] == trap_type), None)
    if selected_trap_type is None:
        flash("Invalid trap type selected.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except ValueError:
        flash("Latitude and longitude must be valid numbers.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))
    if not utils.is_within_new_zealand(latitude, longitude):
        flash(
            "Trap location must be in New Zealand. Most locations should use latitude between -48.5 and -33.5 and longitude between 166.0 and 179.5. For Chatham Islands, use latitude between -45.0 and -43.0 and longitude between -177.0 and -175.0.",
            "danger",
        )
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        updated = facade_repository.update_trap(trap_id, selected_trap_type["id"], latitude, longitude, trap_status)
        if updated:
            flash("Trap updated successfully.", "success")
            try:
                from app.repository import badge_repository
                badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.TRAP_MAINTENANCE, 'Trap maintenance')
            except Exception:
                pass
        else:
            flash("Cannot set trap to Active while its line is inactive.", "warning")
    except Exception as e:
        print("Error updating trap:", trap_id, trap_type, latitude, longitude, trap_status, e)
        flash("Could not update trap. Make sure the code is unique.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#***********************************************************************************************************************
# Admin retire trap (set to inactive)
@app.route("/admin/traps/<int:trap_id>/retire", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_retire_trap(trap_id):
    trap_data = facade_repository.get_trap_catches(trap_id)
    if trap_data is None:
        abort(404)

    line_id = trap_data["line_id"]
    if facade_repository.retire_trap(trap_id):
        flash("Trap retired successfully.", "success")
    else:
        flash("Could not retire trap.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#***********************************************************************************************************************
# Admin list and manage control parameters (species, trap types, line statuses, etc.)
@app.route("/admin/params", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_params():
    param_types = facade_repository.get_manageable_param_types_with_counts()

    # Include specialized lookup-table parameters (bait/trap/species/status) as cards
    try:
        from app.repository import common_repository
        from app.repository import knowhub_repository
        lookup_tables = [
            'Trap_Status',
            'Trap_Types',
            'Bait_Types',
            'Species',
            'Bait_Station_Types',
            'Knowledge_Categories',
        ]
        # Avoid duplicating entries if they already exist in param_types
        existing_types = set([pt.get('param_type') for pt in param_types])
        for tbl in lookup_tables:
            if tbl in existing_types or tbl.lower() in existing_types:
                continue
            try:
                if tbl == 'Knowledge_Categories':
                    records = knowhub_repository.get_knowledge_categories()
                    param_types.append({
                        'param_type': tbl,
                        'value_count': len(records),
                    })
                    continue
                records = common_repository.get_lookup_table_all_records(tbl)
                param_types.append({
                    'param_type': tbl,
                    'value_count': len(records),
                    'active_count': len([r for r in records if r.get('status') == 'Active'])
                })
            except Exception:
                # non-fatal: skip missing tables
                pass
    except Exception:
        # If common repository cannot be loaded, just continue with existing param_types
        pass

    return render_template("admin_params.html", title="Control Parameters", param_types=param_types)

#***********************************************************************************************************************
# Admin view and manage specific parameter type values
@app.route("/admin/params/<param_type>", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin", "Coordinator")
def admin_params_detail(param_type):
    manageable_param_types = facade_repository.get_manageable_param_types()
    # Support both Params table types and specialized lookup tables
    lookup_tables = [
        'Trap_Status', 'Trap_Types', 'Bait_Types', 'Species', 'Bait_Station_Types', 'Knowledge_Categories'
    ]

    if param_type not in manageable_param_types and param_type not in lookup_tables:
        flash("Invalid parameter type.", "danger")
        return redirect(url_for("admin_params"))

    # If this is a lookup-table type, fetch from common_repository and convert
    if param_type in lookup_tables:
        try:
            # special-case Knowledge_Categories (separate table without status column)
            if param_type == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                records = knowhub_repository.get_knowledge_categories()
                values = []
                for r in records:
                    in_use = knowhub_repository.is_knowledge_category_in_use(r['category_id'])
                    values.append({ 'id': r['category_id'], 'param_value': r['name'], 'status': None, 'in_use': in_use })
                display_name = 'Knowledge Category'
                return render_template(
                    "admin_params_detail.html",
                    title=f"Manage: {display_name}",
                    param_type=param_type,
                    display_name=display_name,
                    values=values,
                    is_sa=True,
                    is_lookup_table=True,
                )
            from app.repository import common_repository
            records = common_repository.get_lookup_table_all_records(param_type)
            values = [{ 'id': r['id'], 'param_value': r['name'], 'status': r.get('status') } for r in records]
            display_name = param_type.replace("_", " ").title()
            return render_template(
                "admin_params_detail.html",
                title=f"Manage: {display_name}",
                param_type=param_type,
                display_name=display_name,
                values=values,
                is_sa=True,
                is_lookup_table=True,
            )
        except Exception as e:
            flash(f"Error loading {param_type}: {e}", "danger")
            return redirect(url_for('admin_params'))

    # Fallback: regular Params table handling
    values = facade_repository.get_params_by_type_with_id(param_type)
    display_name = param_type.replace("_", " ").title()
    return render_template(
        "admin_params_detail.html",
        title=f"Manage: {display_name}",
        param_type=param_type,
        display_name=display_name,
        values=values,
        is_sa=False,
        is_lookup_table=False,
    )

#***********************************************************************************************************************
# Admin add new value to a parameter type
@app.route("/admin/params/<param_type>/add", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin", "Coordinator")
def admin_params_add(param_type):
    manageable_param_types = facade_repository.get_manageable_param_types()
    # Allow Knowledge_Categories to be managed here as a special-case
    if param_type not in manageable_param_types and param_type != 'Knowledge_Categories':
        flash("Invalid parameter type.", "danger")
        return redirect(url_for("admin_params"))
    new_value = request.form.get("new_value", "").strip()
    if not new_value:
        flash("Value cannot be empty.", "danger")
    else:
        try:
            if param_type == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                knowhub_repository.add_knowledge_category(new_value)
            else:
                facade_repository.add_param_value(param_type, new_value)
            flash(f"Added \"{new_value}\" successfully.", "success")
        except ValueError as e:
            # knowhub_repository raises specific ValueErrors
            if str(e) in ("duplicate_category", "duplicate_param_value", "duplicate_param_value"):
                flash("This value already exists (case-insensitive).", "warning")
            else:
                flash("Could not add value — it may already exist.", "danger")
        except Exception:
            flash("Could not add value — it may already exist.", "danger")
    return redirect(url_for("admin_params_detail", param_type=param_type))

#***********************************************************************************************************************
# Admin update (rename) a parameter value
@app.route("/admin/params/<param_type>/update", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin", "Coordinator")
def admin_params_update(param_type):
    manageable_param_types = facade_repository.get_manageable_param_types()
    if param_type not in manageable_param_types and param_type != 'Knowledge_Categories':
        flash("Invalid parameter type.", "danger")
        return redirect(url_for("admin_params"))
    old_value = request.form.get("old_value", "").strip()
    new_value = request.form.get("new_value", "").strip()
    if not old_value or not new_value:
        flash("Both current and new values are required.", "danger")
    elif old_value == new_value:
        flash("New value is the same as the current value — no change made.", "warning")
    else:
        try:
            if param_type == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                # find category id by old_value
                cats = knowhub_repository.get_knowledge_categories()
                cat_id = next((c['category_id'] for c in cats if c['name'] == old_value), None)
                if not cat_id:
                    flash("Category not found.", "danger")
                else:
                    knowhub_repository.update_knowledge_category(cat_id, new_value)
                    flash(f"Renamed \"{old_value}\" to \"{new_value}\".", "success")
            else:
                facade_repository.update_param_value(param_type, old_value, new_value)
                flash(f"Renamed \"{old_value}\" to \"{new_value}\".", "success")
        except ValueError as e:
            if str(e) == "param_value_in_use":
                flash("Cannot rename this value because it is in use by existing records.", "warning")
            elif str(e) == "duplicate_category":
                flash("This category name already exists (case-insensitive).", "warning")
            else:
                flash("Could not update value — the new value may already exist.", "danger")
        except Exception:
            flash("Could not update value — the new value may already exist.", "danger")
    return redirect(url_for("admin_params_detail", param_type=param_type))

#***********************************************************************************************************************
# Admin delete a parameter value
@app.route("/admin/params/<param_type>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin", "Coordinator")
def admin_params_delete(param_type):
    manageable_param_types = facade_repository.get_manageable_param_types()
    if param_type not in manageable_param_types and param_type != 'Knowledge_Categories':
        flash("Invalid parameter type.", "danger")
        return redirect(url_for("admin_params"))
    value_id_raw = request.form.get("value_id", "").strip()
    value_display = request.form.get("value", "").strip()
    if not value_id_raw or not value_id_raw.isdigit():
        flash("No value specified for deletion.", "danger")
    else:
        try:
            if param_type == 'Knowledge_Categories':
                from app.repository import knowhub_repository
                deleted = knowhub_repository.delete_knowledge_category(int(value_id_raw))
                if deleted:
                    flash(f"Deleted \"{value_display}\".", "success")
                else:
                    flash("Could not delete value.", "danger")
            else:
                deleted = facade_repository.delete_param_value(param_type, int(value_id_raw))
                if deleted:
                    flash(f"Deleted \"{value_display}\".", "success")
                else:
                    flash("Could not delete value.", "danger")
        except ValueError as e:
            if str(e) in ("param_value_in_use", "category_in_use"):
                flash("Cannot delete: this parameter value is used in existing records.", "warning")
            else:
                flash("Could not delete value.", "danger")
        except Exception:
            flash("Could not delete value.", "danger")
    return redirect(url_for("admin_params_detail", param_type=param_type))

#***********************************************************************************************************************
# User profile page, admin can view all profiles and manage
@app.route("/users/<int:user_id>", methods=["GET"])
@utils.login_required("Please log in to view your profile.")
@utils.roles_required("Coordinator")
def user_profile(user_id):
    is_admin = utils.check_role_access(session.get("role", ""), ["Coordinator"])

    user_data = facade_repository.get_user_profile(user_id)
    if user_data is None:
        abort(404)

    # Reuse the same badge progress builder used by account_profile
    # so the user profile page renders identical badge data/state.
    from app.common_routes import _build_profile_badge_progress
    total_points, badges, next_badge, progress_percent = _build_profile_badge_progress(user_id)

    admin_options = None
    if is_admin:
        admin_options = user_repository.get_user_admin_options()

    return render_template(
        "user_profile.html",
        title=f"User {user_data['full_name']}",
        user=user_data,
        admin_options=admin_options,
        can_manage_user=is_admin,
        total_points=total_points,
        badges=badges,
        next_badge=next_badge,
        progress_percent=progress_percent,
    )

#***********************************************************************************************************************
# Admin add bait station to line
@app.route("/admin/lines/<int:line_id>/bait-stations/create", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_create_bait_station(line_id):
    line_data = facade_repository.get_line_detail(line_id)
    if line_data is None:
        abort(404)

    code = request.form.get("code", "").strip()
    station_type = request.form.get("bait_station_type", "").strip()
    other_details = request.form.get("other_details", "").strip()
    latitude_raw = request.form.get("latitude", "").strip()
    longitude_raw = request.form.get("longitude", "").strip()
    status = request.form.get("status", "Active").strip()

    if not code:
        flash("Bait station code is required.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if not bait_station_repository.is_station_code_unique(code):
        flash("Bait station code already exists.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    station_types = bait_station_repository.get_bait_station_types()
    selected_type = next((st for st in station_types if st['name'] == station_type), None)
    
    if not selected_type:
        flash("Invalid station type selected.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))
    
    # Get other details if provided (AC3)
    other_details = request.form.get("other_details", "").strip()
    if station_type == 'Other' and not other_details:
        flash("Please specify details for 'Other' type.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))
    if station_type != 'Other':
        other_details = None

    # AC3 - Check if 'Other' details are provided if needed
    if station_type == 'Other' and not other_details:
        flash("Please specify details for 'Other' type.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))
        
    if station_type != 'Other':
        other_details = None

    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except ValueError:
        flash("Latitude and longitude must be valid numbers.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if not utils.is_within_new_zealand(latitude, longitude):
        flash(
            "Bait station location must be in New Zealand. Most locations should use latitude between -48.5 and -33.5 and longitude between 166.0 and 179.5. For Chatham Islands, use latitude between -45.0 and -43.0 and longitude between -177.0 and -175.0.",
            "danger",
        )
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        bait_station_repository.add_bait_station(
            code=code,
            line_id=line_id,
            latitude=latitude,
            longitude=longitude,
            bait_station_type_id=selected_type['id'],
            other_type_details=other_details
        )
        flash("Bait station added successfully.", "success")
        try:
            badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.ADD_BAIT_STATION, 'Added bait station')
        except Exception:
            pass
    except Exception:
        flash("Could not add bait station.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#***********************************************************************************************************************
# Admin update bait station
@app.route("/admin/bait-stations/<int:station_id>/update", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_update_bait_station(station_id):
    line_id_raw = request.form.get("line_id", "").strip()
    station_type = request.form.get("bait_station_type", "").strip()
    other_details = request.form.get("other_details", "").strip()
    latitude_raw = request.form.get("latitude", "").strip()
    longitude_raw = request.form.get("longitude", "").strip()
    status = request.form.get("status", "").strip()

    station_data = bait_station_repository.get_station_by_id(station_id)
    if station_data is None:
        abort(404)

    line_id = station_data["line_id"]
    if line_id_raw.isdigit():
        line_id = int(line_id_raw)

    station_types = bait_station_repository.get_bait_station_types()
    selected_type = next((st for st in station_types if st['name'] == station_type), None)
    
    if not selected_type:
        flash("Invalid station type selected.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except ValueError:
        flash("Latitude and longitude must be valid numbers.", "danger")
        return redirect(url_for("line_detail", line_id=line_id))

    if not utils.is_within_new_zealand(latitude, longitude):
        flash(
            "Bait station location must be in New Zealand. Most locations should use latitude between -48.5 and -33.5 and longitude between 166.0 and 179.5. For Chatham Islands, use latitude between -45.0 and -43.0 and longitude between -177.0 and -175.0.",
            "danger",
        )
        return redirect(url_for("line_detail", line_id=line_id))

    try:
        bait_station_repository.update_bait_station(
            station_id=station_id,
            bait_station_type_id=selected_type['id'],
            latitude=latitude,
            longitude=longitude,
            status=status,
            other_type_details=other_details
        )
        flash("Bait station updated successfully.", "success")
    except Exception:
        flash("Could not update bait station.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))

#***********************************************************************************************************************
# Admin retire bait station
@app.route("/admin/bait-stations/<int:station_id>/retire", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator")
def admin_retire_bait_station(station_id):
    station_data = bait_station_repository.get_station_by_id(station_id)
    if station_data is None:
        abort(404)

    line_id = station_data["line_id"]
    if bait_station_repository.retire_bait_station(station_id):
        flash("Bait station retired successfully.", "success")
    else:
        flash("Could not retire bait station.", "danger")

    return redirect(url_for("line_detail", line_id=line_id))
