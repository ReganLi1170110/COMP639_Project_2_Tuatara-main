# Operator Routes
# Handles routes specific to the Operator role, including the operator dashboard,
# assigned lines view, and management of field observations.

from flask import abort, render_template, request, redirect, url_for, flash, session
from app.repository import operator_repository, facade_repository, user_repository, catch_repository, common_repository
from app import flask_app as app
import app.utils as utils
from datetime import datetime

#***********************************************************************************************************************
# Operator dashboard, shows assigned lines, recent observations, and notifications
@app.route("/operator_dashboard", methods=["GET"])
@utils.login_required("Please log in to access the operator dashboard.")
@utils.roles_required("Operator")
def operator_dashboard():
    current_user = user_repository.get_user_by_id(session["user_id"])
    if current_user is None:
        session.clear()
        flash("Your account could not be found. Please log in again.", "danger")
        return redirect(url_for("login"))
    
    group_id = session.get("group_id")

    dashboard = facade_repository.get_operator_dashboard_data(session["user_id"], group_id)

    return render_template(
        "operator_dashboard.html",
        title="Operator Dashboard",
        current_user=current_user,
        dashboard=dashboard,
    )

#***********************************************************************************************************************
# My Lines page, shows lines assigned to the operator with status and recent activity
@app.route("/my_lines")
@utils.login_required("Please log in to view your lines.")
@utils.roles_required("Operator")
def my_lines():
    operator_id = session["user_id"]
    group_id = session.get("group_id")

    # Get lines assigned to this operator 
    assigned_lines = operator_repository.get_operator_assigned_lines(operator_id, group_id)
    for line in assigned_lines:
        print(line)   # this will show all keys and values
    return render_template("my_lines.html", lines=assigned_lines)

#***********************************************************************************************************************
# Add observation page, allows operators to add new observations with validation
@app.route("/observation/add", methods=["GET", "POST"])
@utils.login_required()
@utils.roles_required("Operator")
def add_observation():
    operator_id = session["user_id"]
    assigned_lines = facade_repository.get_operator_assigned_lines(operator_id)
    assigned_line_ids = {line["line_id"] for line in assigned_lines}

    if request.method == "POST":
        line_id_raw = request.form.get("line_id", "").strip()
        date_str = request.form.get("date_recorded")
        notes = request.form.get("notes", "").strip()

        line_id = None
        if line_id_raw:
            try:
                line_id = int(line_id_raw)
            except ValueError:
                flash("Invalid associated trap line.", "danger")
                return render_template(
                    "add_observation.html",
                    assigned_lines=assigned_lines,
                    now=datetime.now().strftime('%Y-%m-%dT%H:%M')
                )

            if line_id not in assigned_line_ids:
                flash("You can only associate observations with your assigned trap lines.", "danger")
                return render_template(
                    "add_observation.html",
                    assigned_lines=assigned_lines,
                    now=datetime.now().strftime('%Y-%m-%dT%H:%M')
                )

        # Parse date, fallback to now if invalid or missing
        try:
            date_recorded = datetime.strptime(date_str, "%Y-%m-%dT%H:%M") if date_str else datetime.now()
        except (ValueError, TypeError):
            date_recorded = datetime.now()

        # Date can't be in the future
        if date_recorded > datetime.now():
            flash("Observation date and time cannot be in the future.", "danger")
            return render_template(
                "add_observation.html",
                assigned_lines=assigned_lines,
                now=datetime.now().strftime('%Y-%m-%dT%H:%M')
            )

        # Word count validation (150 words limit)
        word_count = len(notes.split())
        if word_count > 150:
            flash(f"Observation notes cannot exceed 150 words. Current count: {word_count}", "danger")
            return render_template(
                "add_observation.html",
                assigned_lines=assigned_lines,
                now=datetime.now().strftime('%Y-%m-%dT%H:%M'),
                notes=notes,
                line_id=line_id_raw,
                date_recorded=date_str
            )

        # Add observation (species removed from requirements so not included here)
        try:
            facade_repository.add_observation(
                operator_id=operator_id,
                line_id=line_id,
                date_recorded=date_recorded,
                notes=notes
            )
            flash("Observation added successfully.", "success")
            try:
                from app.repository import badge_repository
                badge_repository.add_user_points(operator_id, badge_repository.BadgeAction.OBSERVATION, 'Observation added')
            except Exception:
                pass
            return redirect(url_for("operator_dashboard"))
        except Exception as e:
            flash(f"Failed to add observation: {e}", "danger")

    # GET request: show the form
    return render_template(
        "add_observation.html",
        assigned_lines=assigned_lines,
        now=datetime.now().strftime('%Y-%m-%dT%H:%M')
    )

#***********************************************************************************************************************
# Edit observation page, allows operators to edit their own observations with validation
@app.route("/observation/edit/<int:observation_id>", methods=["GET", "POST"])
@utils.login_required()
@utils.roles_required("Operator")
def edit_observation(observation_id):
    observation = facade_repository.get_observation_by_id(observation_id)
    if not observation:
        abort(404)

    if observation["operator_id"] != session["user_id"]:
        flash("You are not allowed to edit this observation.", "danger")
        return redirect(url_for("operator_dashboard"))

    assigned_lines = facade_repository.get_operator_assigned_lines(session["user_id"])

    if request.method == "POST":
        line_id = request.form.get("line_id")
        date_str = request.form.get("date_recorded")
        notes = request.form.get("notes", "").strip()

        # Parse date, fallback to now if invalid or missing
        try:
            date_recorded = datetime.strptime(date_str, "%Y-%m-%dT%H:%M") if date_str else datetime.now()
        except (ValueError, TypeError):
            date_recorded = datetime.now()

        # Word count validation (150 words limit)
        word_count = len(notes.split())
        if word_count > 150:
            flash(f"Observation notes cannot exceed 150 words. Current count: {word_count}", "danger")
            date_value = date_recorded.strftime("%d-%m-%Y %H:%M:%S") if date_recorded else ""
            return render_template(
                "edit_observation.html",
                observation={**observation, "notes": notes, "line_id": int(line_id) if line_id else None},
                assigned_lines=assigned_lines,
                date_value=date_value
            )
 
         # Update observation (species removed)
        try:
            facade_repository.update_observation(
                observation_id=observation_id,
                line_id=line_id if line_id else None,
                date_recorded=date_recorded,
                notes=notes
            )
            flash("Observation updated successfully.", "success")
            return redirect(url_for("operator_dashboard"))
        except Exception as e:
            flash(f"Failed to update observation: {e}", "danger")

    # GET request: populate the form with current data
    date_value = observation["date_recorded"].strftime("%d-%m-%Y %H:%M:%S") if observation["date_recorded"] else ""
    return render_template(
        "edit_observation.html",
        observation=observation,
        assigned_lines=assigned_lines,
        date_value=date_value
    )

@app.route('/line/<int:line_id>/trap/<int:trap_id>/add_catch', methods=['GET', 'POST'])
@utils.login_required()
@utils.roles_required('Operator')
def add_catch_record(line_id, trap_id):
    context = {
        'line_id': line_id,
        'trap_id': trap_id,
        'catch': None,
        'date_value': '',
        'species_list': common_repository.get_species(),
        'sex_list': common_repository.get_params_by_type('sex'),
        'maturity_list': common_repository.get_params_by_type('maturity'),
        'status_list': common_repository.get_trap_status(),
        'rebaited_list': common_repository.get_params_by_type('rebaited'),
        'bait_type_list': common_repository.get_bait_types(),
        'trap_condition_list': common_repository.get_params_by_type('trap_condition'),
        'mode': 'add',
        'title': 'Add Catch Record',
        'now': datetime.now().strftime('%Y-%m-%dT%H:%M')
    }

    if request.method == 'POST':
        species_raw = request.form.get('species', '').strip()
        sex = request.form.get('sex', '').strip()
        maturity = request.form.get('maturity', '').strip()
        status_raw = request.form.get('status', '').strip()
        rebaited = request.form.get('rebaited', '').strip()
        bait_type_raw = request.form.get('bait_type', '').strip()
        trap_condition = request.form.get('trap_condition', '').strip()
        strikes_raw = request.form.get('strikes', '0')
        notes = request.form.get('notes', '')
        date_str = request.form.get('date')

        missing_fields = []
        if not date_str:
            missing_fields.append('date')
        if not species_raw:
            missing_fields.append('species')
        if not sex:
            missing_fields.append('sex')
        if not status_raw:
            missing_fields.append('status')
        if not rebaited:
            missing_fields.append('rebaited')
        if not bait_type_raw:
            missing_fields.append('bait type')
        if not trap_condition:
            missing_fields.append('trap condition')

        if missing_fields:
            flash(f"Missing required fields: {', '.join(missing_fields)}.", 'danger')
            return render_template('catch_form.html', **context)

        try:
            date = datetime.fromisoformat(date_str)
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('catch_form.html', **context)

        if date > datetime.now():
            flash('Date and time cannot be in the future.', 'danger')
            return render_template('catch_form.html', **context)

        try:
            strikes = int(strikes_raw)
        except (TypeError, ValueError):
            flash('Strikes must be a valid number.', 'danger')
            return render_template('catch_form.html', **context)

        try:
            species_id = int(species_raw)
            status_id = int(status_raw)
            bait_type_id = int(bait_type_raw)
        except (TypeError, ValueError):
            flash('Species, status, and bait type must be selected.', 'danger')
            return render_template('catch_form.html', **context)

        if strikes < 0:
            flash('Strikes cannot be less than 0.', 'danger')
            return render_template('catch_form.html', **context)
        catch_repository.add_catch(session['user_id'], {
            'trap_id': trap_id,
            'date': date,
            'species_caught_id': species_id,
            'sex': sex,
            'maturity': maturity,
            'trap_status_id': status_id,
            'rebaited': rebaited,
            'bait_type_id': bait_type_id,
            'trap_condition': trap_condition,
            'strikes': strikes,
            'notes': notes
        })

        flash('Catch record added.', 'success')
        try:
            from app.repository import badge_repository
            badge_repository.add_user_points(session['user_id'], badge_repository.BadgeAction.CATCH, 'Catch recorded')
        except Exception:
            pass
        return redirect(url_for('line_detail', line_id=line_id))

    return render_template('catch_form.html', **context)