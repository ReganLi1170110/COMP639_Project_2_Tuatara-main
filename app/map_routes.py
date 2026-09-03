from flask import abort, json, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app import map_routes_helper
from app.repository import (
    core_repository,
    user_repository
)
from app import flask_app as app
import app.utils as utils


@app.route("/map", methods=["GET"])
@utils.login_required("Please log in to view the map.")
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def group_map():
    group_id = session.get("group_id")
    user_id = session.get("user_id")

    if not group_id:
        flash("Please select a group first.", "warning")
        return redirect(url_for("choose_group"))

    if not user_repository.is_accessible_group_member(user_id, group_id):
        flash("You do not have access to this group map.", "danger")
        return redirect(url_for("home"))

    can_edit = session.get("role") in ("Coordinator", "Admin")
    return render_template("group_map.html", title="Operations Map", can_edit=can_edit)


@app.route("/admin/map", methods=["GET"])
@utils.login_required("Please log in to view the admin map.")
@utils.roles_required("Admin")
def admin_map():
    return render_template("admin_map.html", title="Admin Operations Map", can_edit=True)


@app.route("/api/admin/map/groups", methods=["GET"])
@utils.login_required("Please log in to load groups.")
@utils.roles_required("Admin")
def admin_map_groups_api():
    groups = core_repository.get_all_groups_for_admin()
    return jsonify(
        {
            "groups": [
                {
                    "group_id": row["group_id"],
                    "name": row["name"],
                    "status": row["status"],
                }
                for row in groups
            ]
        }
    )


@app.route("/api/admin/map/data", methods=["GET"])
@utils.login_required("Please log in to load map data.")
@utils.roles_required("Admin")
def admin_map_data_api():
    group_id_raw = (request.args.get("group_id") or "").strip()
    if group_id_raw.lower() == "all":
        return jsonify(map_routes_helper._get_all_groups_map_data())

    group_id = map_routes_helper._parse_group_id(group_id_raw)
    if not group_id:
        return jsonify({"error": "A valid group_id is required."}), 400

    group_row = core_repository.get_group_by_id(group_id)
    if not group_row:
        return jsonify({"error": "Group not found."}), 404

    payload = map_routes_helper._get_group_map_data(group_id)
    payload["group_name"] = group_row["name"]
    payload["group_id"] = group_id
    return jsonify(payload)


@app.route("/api/admin/map/operational-area", methods=["POST"])
@utils.login_required("Please log in to update operational area.")
@utils.roles_required("Admin")
def admin_save_operational_area_api():
    payload = request.get_json(silent=True) or {}
    group_id = map_routes_helper._parse_group_id(payload.get("group_id"))
    if not group_id:
        return jsonify({"error": "A valid group_id is required."}), 400

    if not core_repository.get_group_by_id(group_id):
        return jsonify({"error": "Group not found."}), 404

    polygon = payload.get("polygon")

    if polygon is not None and not map_routes_helper._is_polygon_geojson(polygon):
        return jsonify({"error": "Invalid polygon GeoJSON payload."}), 400

    with utils.get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Groups
            SET operational_area = %s
            WHERE group_id = %s;
            """,
            (json.dumps(polygon) if polygon is not None else None, group_id),
        )

    return jsonify({"success": True, "operational_area": polygon, "group_id": group_id})


@app.route("/api/admin/map/markers", methods=["POST"])
@utils.login_required("Please log in to add map markers.")
@utils.roles_required("Admin")
def admin_create_map_marker_api():
    payload = request.get_json(silent=True) or {}
    group_id = map_routes_helper._parse_group_id(payload.get("group_id"))
    if not group_id:
        return jsonify({"error": "A valid group_id is required."}), 400

    if not core_repository.get_group_by_id(group_id):
        return jsonify({"error": "Group not found."}), 404

    return map_routes_helper._create_map_marker_for_group(group_id, payload)


@app.route("/api/admin/map/markers/<int:marker_id>", methods=["PUT"])
@utils.login_required("Please log in to update map markers.")
@utils.roles_required("Admin")
def admin_update_map_marker_api(marker_id):
    payload = request.get_json(silent=True) or {}
    group_id = map_routes_helper._parse_group_id(payload.get("group_id"))
    if not group_id:
        return jsonify({"error": "A valid group_id is required."}), 400

    if not core_repository.get_group_by_id(group_id):
        return jsonify({"error": "Group not found."}), 404

    return map_routes_helper._update_map_marker_for_group(group_id, marker_id, payload)


@app.route("/api/map/data", methods=["GET"])
@utils.login_required("Please log in to load map data.")
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def map_data_api():
    group_id = session.get("group_id")
    user_id = session.get("user_id")

    if not group_id:
        return jsonify({"error": "No group selected."}), 400

    if not user_repository.is_accessible_group_member(user_id, group_id):
        return jsonify({"error": "Unauthorized for selected group."}), 403

    return jsonify(map_routes_helper._get_group_map_data(group_id))


@app.route("/api/map/operational-area", methods=["POST"])
@utils.login_required("Please log in to update the operational area.")
@utils.roles_required("Coordinator", "Admin")
def save_operational_area_api():
    group_id = session.get("group_id")
    user_id = session.get("user_id")

    if not group_id:
        return jsonify({"error": "No group selected."}), 400

    if not user_repository.is_accessible_group_member(user_id, group_id):
        return jsonify({"error": "Unauthorized for selected group."}), 403

    payload = request.get_json(silent=True) or {}
    polygon = payload.get("polygon")

    if polygon is not None and not map_routes_helper._is_polygon_geojson(polygon):
        return jsonify({"error": "Invalid polygon GeoJSON payload."}), 400

    with utils.get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE Groups
            SET operational_area = %s
            WHERE group_id = %s;
            """,
            (json.dumps(polygon) if polygon is not None else None, group_id),
        )

    return jsonify({"success": True, "operational_area": polygon})


@app.route("/api/map/markers", methods=["POST"])
@utils.login_required("Please log in to add map markers.")
@utils.roles_required("Operator", "Coordinator", "Admin")
def create_map_marker_api():
    group_id = session.get("group_id")
    user_id = session.get("user_id")

    if not group_id:
        return jsonify({"error": "No group selected."}), 400

    if not user_repository.is_accessible_group_member(user_id, group_id):
        return jsonify({"error": "Unauthorized for selected group."}), 403

    payload = request.get_json(silent=True) or {}
    return map_routes_helper._create_map_marker_for_group(group_id, payload)


@app.route("/api/map/markers/<int:marker_id>", methods=["PUT"])
@utils.login_required("Please log in to update markers.")
@utils.roles_required("Coordinator", "Admin")
def update_map_marker_api(marker_id):
    group_id = session.get("group_id")
    user_id = session.get("user_id")

    if not group_id:
        return jsonify({"error": "No group selected."}), 400

    if not user_repository.is_accessible_group_member(user_id, group_id):
        return jsonify({"error": "Unauthorized for selected group."}), 403

    payload = request.get_json(silent=True) or {}
    return map_routes_helper._update_map_marker_for_group(group_id, marker_id, payload)
