# Bait Station Routes
# Defines web routes for managing bait station activity and logging records.

from flask import render_template, request, redirect, url_for, flash, session, abort
from app import flask_app as app
from app.repository import bait_station_repository, common_repository, bait_station_record_repository
import app.utils as utils
from datetime import datetime

@app.route("/bait-stations/<int:station_id>/activity", methods=["GET"])
@utils.login_required()
def bait_station_activity(station_id):
    station = bait_station_repository.get_station_by_id(station_id)
    if not station:
        abort(404)
        
    records = bait_station_record_repository.get_station_records(station_id)
    return render_template(
        "bait_station_activity.html",
        title=f"Activity - {station['code']}",
        station=station,
        records=records
    )

@app.route("/lines/<int:line_id>/bait-stations/<int:station_id>/record/add", methods=["GET", "POST"])
@utils.login_required()
def add_bait_station_record(line_id, station_id):
    station = bait_station_repository.get_station_by_id(station_id)
    if not station:
        abort(404)
        
    # Coordinators can add records directly; Operators must be assigned to the line.
    role = session.get("role")
    if role == "Coordinator":
        pass
    elif role == "Operator":
        from app.routes import is_operator_assigned_to_line
        if not is_operator_assigned_to_line(session['user_id'], line_id):
            flash('You are not assigned to this line.', 'danger')
            return redirect(url_for('lines'))
    else:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('lines'))

    if request.method == "POST":
        # Required fields
        date_str = request.form.get("date")
        bait_remaining = request.form.get("bait_remaining")
        target_species_id = request.form.get("target_species")
        active_ingredient = request.form.get("active_ingredient", "").strip()
        formulation = request.form.get("formulation")
        concentration = request.form.get("concentration")

        # Optional fields
        bait_added = request.form.get("bait_added") or 0
        bait_removed = request.form.get("bait_removed") or 0
        notes = request.form.get("notes", "").strip()

        # Basic validation
        missing = []
        if not date_str:
            missing.append('Date and time')
        if bait_remaining is None or bait_remaining == "":
            missing.append('Bait remaining')
        if not target_species_id:
            missing.append('Target species')
        if not active_ingredient:
            missing.append('Active ingredient')
        if not formulation:
            missing.append('Formulation')
        if concentration is None or concentration == "":
            missing.append('Concentration')

        if missing:
            flash(f"Missing required fields: {', '.join(missing)}", "danger")
            return redirect(url_for("add_bait_station_record", line_id=line_id, station_id=station_id))

        try:
            # parse and validate date
            date_recorded = datetime.fromisoformat(date_str)
            if date_recorded > datetime.now():
                flash("Date and time cannot be in the future.", "danger")
                return redirect(url_for("add_bait_station_record", line_id=line_id, station_id=station_id))

            # numeric validations
            bait_remaining_f = float(bait_remaining)
            bait_added_f = float(bait_added)
            bait_removed_f = float(bait_removed)
            concentration_f = float(concentration)
            if bait_remaining_f < 0 or bait_added_f < 0 or bait_removed_f < 0 or concentration_f < 0:
                flash("Weights and concentration must be non-negative.", "danger")
                return redirect(url_for("add_bait_station_record", line_id=line_id, station_id=station_id))

            # concentration reasonable range check (0-100)
            if concentration_f > 100:
                flash("Concentration must be 0-100%.", "danger")
                return redirect(url_for("add_bait_station_record", line_id=line_id, station_id=station_id))

            bait_station_record_repository.add_station_record(
                station_id=station_id,
                recorded_by=session["user_id"],
                bait_remaining=bait_remaining_f,
                bait_added=bait_added_f,
                notes=notes,
                date=date_recorded,
                bait_removed=bait_removed_f,
                target_species_id=int(target_species_id),
                active_ingredient=active_ingredient,
                formulation=formulation,
                concentration=concentration_f
            )
            flash("Bait station record added successfully.", "success")
            try:
                from app.repository import badge_repository
                badge_repository.add_user_points(session["user_id"], badge_repository.BadgeAction.ADD_BAIT_STATION, 'Add Bait Station')
            except Exception:
                pass
            return redirect(url_for("line_detail", line_id=line_id))
        except ValueError:
            flash("Numeric fields must be valid numbers.", "danger")
            return redirect(url_for("add_bait_station_record", line_id=line_id, station_id=station_id))
        except Exception as e:
            # Improve messaging for numeric overflow / precision errors coming from the DB
            msg = str(e).lower()
            if 'numeric field overflow' in msg or 'precision' in msg or 'out of range' in msg:
                # Provide a user-friendly message for weight fields (kg)
                flash('Weight too large: weight fields (kg) must be less than 10,000,000 kg.', 'danger')
            else:
                flash(f"Could not add record: {e}", "danger")
            return redirect(url_for("add_bait_station_record", line_id=line_id, station_id=station_id))
            
    bait_types = common_repository.get_bait_types()
    species = common_repository.get_species()
    return render_template(
        "add_bait_station_record.html",
        title=f"Add Record - {station['code']}",
        station=station,
        line_id=line_id,
        bait_types=bait_types,
        species=species,
        active_ingredients=common_repository.get_params_by_type('active_ingredient'),
        now=datetime.now().strftime('%Y-%m-%dT%H:%M')
    )
