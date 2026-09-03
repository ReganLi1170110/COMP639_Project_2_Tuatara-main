from app import utils
from app.repository import trap_repository, bait_station_repository, line_repository, common_repository, badge_repository
import json
from flask import jsonify, session

def format_operational_area(operational_area):
    if not operational_area:
        return None

    try:
        parsed = json.loads(operational_area)
    except (TypeError, ValueError, json.JSONDecodeError):
        return operational_area

    if isinstance(parsed, list):
        return ", ".join(str(item) for item in parsed if item)
    if isinstance(parsed, dict):
        return ", ".join(str(value) for value in parsed.values() if value)
    if isinstance(parsed, str):
        return parsed
    return str(parsed)


def _normalize_operational_area(operational_area):
    if operational_area is None:
        return None
    if isinstance(operational_area, dict):
        return operational_area

    try:
        parsed = json.loads(operational_area)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    if isinstance(parsed, dict):
        return parsed
    return None


def _is_polygon_geojson(candidate):
    if not isinstance(candidate, dict):
        return False
    if candidate.get("type") != "Polygon":
        return False

    coordinates = candidate.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        return False

    outer_ring = coordinates[0]
    if not isinstance(outer_ring, list) or len(outer_ring) < 3:
        return False

    for point in outer_ring:
        if not isinstance(point, list) or len(point) != 2:
            return False
        lng, lat = point
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return False
        if not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
            return False

    return True


def _get_group_map_data(group_id):
    with utils.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT operational_area
            FROM Groups
            WHERE group_id = %s;
            """,
            (group_id,),
        )
        group_row = cursor.fetchone()

        cursor.execute(
            """
            SELECT line_id, name, type
            FROM Line
            WHERE group_id = %s
            ORDER BY name;
            """,
            (group_id,),
        )
        lines = cursor.fetchall()

        cursor.execute(
            """
            SELECT t.trap_id AS id, t.code, t.latitude, t.longitude, t.trap_status AS status,
                   tt.name AS trap_type, l.line_id, l.name AS line_name
            FROM Traps t
            JOIN Trap_Types tt ON tt.id = t.trap_type_id
            JOIN Line l ON l.line_id = t.line_id
            WHERE l.group_id = %s
            ORDER BY t.code;
            """,
            (group_id,),
        )
        trap_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT bs.station_id AS id, bs.code, bs.latitude, bs.longitude, bs.status,
                   bst.name AS bait_station_type, bs.other_type_details,
                   l.line_id, l.name AS line_name
            FROM Bait_Stations bs
            JOIN Bait_Station_Types bst ON bst.id = bs.bait_station_type_id
            JOIN Line l ON l.line_id = bs.line_id
            WHERE l.group_id = %s
            ORDER BY bs.code;
            """,
            (group_id,),
        )
        bait_rows = cursor.fetchall()

    operational_area = _normalize_operational_area(group_row["operational_area"] if group_row else None)

    markers = []
    for trap in trap_rows:
        markers.append(
            {
                "kind": "trap",
                "id": trap["id"],
                "code": trap["code"],
                "latitude": float(trap["latitude"]),
                "longitude": float(trap["longitude"]),
                "status": trap["status"],
                "type_name": trap["trap_type"],
                "line_id": trap["line_id"],
                "line_name": trap["line_name"],
            }
        )

    for station in bait_rows:
        markers.append(
            {
                "kind": "bait_station",
                "id": station["id"],
                "code": station["code"],
                "latitude": float(station["latitude"]),
                "longitude": float(station["longitude"]),
                "status": station["status"],
                "type_name": station["bait_station_type"],
                "other_type_details": station["other_type_details"],
                "line_id": station["line_id"],
                "line_name": station["line_name"],
            }
        )

    return {
        "operational_area": operational_area,
        "lines": [
            {
                "line_id": row["line_id"],
                "name": row["name"],
                "type": row["type"],
            }
            for row in lines
        ],
        "trap_types": [
            {"id": row["id"], "name": row["name"]}
            for row in trap_repository.get_trap_types()
        ],
        "bait_station_types": [
            {"id": row["id"], "name": row["name"]}
            for row in bait_station_repository.get_bait_station_types()
        ],
        "markers": markers,
    }


def _get_all_groups_map_data():
    group_rows = common_repository.get_all_active_groups()  # Using repository method for consistency and potential caching
    lines = common_repository.get_all_active_lines()
    trap_rows = common_repository.get_all_active_traps()
    bait_rows = common_repository.get_all_active_bait_stations()
    markers = []
    for trap in trap_rows:
        markers.append(
            {
                "kind": "trap",
                "id": trap["id"],
                "code": trap["code"],
                "latitude": float(trap["latitude"]),
                "longitude": float(trap["longitude"]),
                "status": trap["status"],
                "type_name": trap["trap_type"],
                "line_id": trap["line_id"],
                "line_name": trap["line_name"],
                "group_id": trap["group_id"],
                "group_name": trap["group_name"],
            }
        )

    for station in bait_rows:
        markers.append(
            {
                "kind": "bait_station",
                "id": station["id"],
                "code": station["code"],
                "latitude": float(station["latitude"]),
                "longitude": float(station["longitude"]),
                "status": station["status"],
                "type_name": station["bait_station_type"],
                "other_type_details": station["other_type_details"],
                "line_id": station["line_id"],
                "line_name": station["line_name"],
                "group_id": station["group_id"],
                "group_name": station["group_name"],
            }
        )

    operational_areas = []
    for row in group_rows:
        normalized = _normalize_operational_area(row["operational_area"])
        if normalized:
            operational_areas.append(
                {
                    "group_id": row["group_id"],
                    "group_name": row["name"],
                    "status": row["status"],
                    "polygon": normalized,
                }
            )

    return {
        "mode": "all",
        "operational_areas": operational_areas,
        "lines": [
            {
                "line_id": row["line_id"],
                "name": row["name"],
                "type": row["type"],
                "group_id": row["group_id"],
                "group_name": row["group_name"],
            }
            for row in lines
        ],
        "trap_types": [
            {"id": row["id"], "name": row["name"]}
            for row in trap_repository.get_trap_types()
        ],
        "bait_station_types": [
            {"id": row["id"], "name": row["name"]}
            for row in bait_station_repository.get_bait_station_types()
        ],
        "markers": markers,
    }


def _parse_group_id(group_id_raw):
    try:
        return int(group_id_raw)
    except (TypeError, ValueError):
        return None


def _award_map_points(action, description):
    user_id = session.get("user_id")
    if not user_id:
        return

    try:
        badge_repository.add_user_points(user_id, action, description)
    except Exception:
        pass


def _create_map_marker_for_group(group_id, payload):
    kind = (payload.get("kind") or "").strip()
    code = (payload.get("code") or "").strip()
    line_id_raw = payload.get("line_id")
    latitude_raw = payload.get("latitude")
    longitude_raw = payload.get("longitude")

    if kind not in {"trap", "bait_station"}:
        return jsonify({"error": "Marker type must be trap or bait_station."}), 400
    if not code:
        return jsonify({"error": "Code is required."}), 400

    try:
        line_id = int(line_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Line is required."}), 400

    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Latitude and longitude must be numeric."}), 400

    if not utils.is_within_new_zealand(latitude, longitude):
        return jsonify({"error": "Coordinates must be in New Zealand bounds."}), 400

    line_row = line_repository.get_line_by_id(line_id, group_id)  # Using repository method for consistency and potential caching
    if not line_row:
        return jsonify({"error": "Line not found in selected group."}), 404

    if kind == "trap" and line_row["type"] != "Trap":
        return jsonify({"error": "Traps must be added to Trap lines."}), 400
    if kind == "bait_station" and line_row["type"] == "Trap":
        return jsonify({"error": "Bait stations must be added to Bait Station lines."}), 400

    if kind == "trap":
        trap_type_id = payload.get("trap_type_id")
        try:
            trap_type_id = int(trap_type_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Trap type is required."}), 400

        valid_type_ids = {row["id"] for row in trap_repository.get_trap_types()}
        if trap_type_id not in valid_type_ids:
            return jsonify({"error": "Invalid trap type selected."}), 400

        if trap_repository.trap_code_exists_exact(code):
            return jsonify({"error": "Trap code already exists."}), 400

        trap_id = trap_repository.add_trap_to_line(line_id, code, trap_type_id, latitude, longitude)
        trap = trap_repository.get_trap_by_id(trap_id)
        _award_map_points(badge_repository.BadgeAction.ADD_TRAP, "Added trap from map")
        marker = {
            "kind": "trap",
            "id": trap["trap_id"],
            "code": trap["code"],
            "latitude": float(trap["latitude"]),
            "longitude": float(trap["longitude"]),
            "status": trap["trap_status"],
            "type_name": trap["trap_type"],
            "line_id": trap["line_id"],
            "line_name": trap["line_name"],
        }
        return jsonify({"success": True, "marker": marker}), 201

    bait_station_type_id = payload.get("bait_station_type_id")
    other_type_details = (payload.get("other_type_details") or "").strip() or None
    try:
        bait_station_type_id = int(bait_station_type_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Bait station type is required."}), 400

    valid_station_type_ids = {row["id"] for row in bait_station_repository.get_bait_station_types()}
    if bait_station_type_id not in valid_station_type_ids:
        return jsonify({"error": "Invalid bait station type selected."}), 400

    if not bait_station_repository.is_station_code_unique(code):
        return jsonify({"error": "Bait station code already exists."}), 400

    station_id = bait_station_repository.add_bait_station(
        code=code,
        line_id=line_id,
        latitude=latitude,
        longitude=longitude,
        bait_station_type_id=bait_station_type_id,
        other_type_details=other_type_details,
    )
    station = bait_station_repository.get_station_by_id(station_id)
    _award_map_points(badge_repository.BadgeAction.ADD_BAIT_STATION, "Added bait station from map")
    marker = {
        "kind": "bait_station",
        "id": station["station_id"],
        "code": station["code"],
        "latitude": float(station["latitude"]),
        "longitude": float(station["longitude"]),
        "status": station["status"],
        "type_name": station["bait_station_type"],
        "other_type_details": station["other_type_details"],
        "line_id": station["line_id"],
        "line_name": station["line_name"],
    }
    return jsonify({"success": True, "marker": marker}), 201


def _update_map_marker_for_group(group_id, marker_id, payload):
    kind = (payload.get("kind") or "").strip()
    code = (payload.get("code") or "").strip()
    line_id_raw = payload.get("line_id")
    latitude_raw = payload.get("latitude")
    longitude_raw = payload.get("longitude")

    if kind not in {"trap", "bait_station"}:
        return jsonify({"error": "Marker type must be trap or bait_station."}), 400
    if not code:
        return jsonify({"error": "Code is required."}), 400

    try:
        line_id = int(line_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Line is required."}), 400

    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Latitude and longitude must be numeric."}), 400

    if not utils.is_within_new_zealand(latitude, longitude):
        return jsonify({"error": "Coordinates must be in New Zealand bounds."}), 400

    line_row = line_repository.get_line_by_id(line_id, group_id)  # Using repository method for consistency and potential caching
    if not line_row:
        return jsonify({"error": "Line not found in selected group."}), 404

    if kind == "trap" and line_row["type"] != "Trap":
        return jsonify({"error": "Traps must be on Trap lines."}), 400
    if kind == "bait_station" and line_row["type"] == "Trap":
        return jsonify({"error": "Bait stations must be on Bait Station lines."}), 400

    if kind == "trap":
        trap_type_id = payload.get("trap_type_id")
        trap_status = payload.get("status")
        try:
            trap_type_id = int(trap_type_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Trap type is required."}), 400

        valid_type_ids = {row["id"] for row in trap_repository.get_trap_types()}
        if trap_type_id not in valid_type_ids:
            return jsonify({"error": "Invalid trap type selected."}), 400

        trap_row = trap_repository.get_trap_by_ids(marker_id, group_id)  # Using repository method for consistency and potential caching

        if not trap_row:
            return jsonify({"error": "Trap not found in selected group."}), 404

        if code.lower() != trap_row["code"].lower() and trap_repository.trap_code_exists_exact(code):
            return jsonify({"error": "Trap code already exists."}), 400
        
        trap_repository.update_trap_map(marker_id, code, line_id, trap_type_id, latitude, longitude, trap_status)
        trap = trap_repository.get_trap_by_id(marker_id)
        _award_map_points(badge_repository.BadgeAction.TRAP_MAINTENANCE, "Updated trap from map")
        marker = {
            "kind": "trap",
            "id": trap["trap_id"],
            "code": trap["code"],
            "latitude": float(trap["latitude"]),
            "longitude": float(trap["longitude"]),
            "status": trap["trap_status"],
            "type_name": trap["trap_type"],
            "line_id": trap["line_id"],
            "line_name": trap["line_name"],
        }
        return jsonify({"success": True, "marker": marker}), 200

    bait_station_type_id = payload.get("bait_station_type_id")
    other_type_details = (payload.get("other_type_details") or "").strip() or None
    bait_status = payload.get("status")
    try:
        bait_station_type_id = int(bait_station_type_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Bait station type is required."}), 400

    valid_station_type_ids = {row["id"] for row in bait_station_repository.get_bait_station_types()}
    if bait_station_type_id not in valid_station_type_ids:
        return jsonify({"error": "Invalid bait station type selected."}), 400

    station_row = bait_station_repository.get_bait_station_by_id(marker_id, group_id)  # Using repository method for consistency and potential caching

    if not station_row:
        return jsonify({"error": "Bait station not found in selected group."}), 404

    if code.lower() != station_row["code"].lower() and not bait_station_repository.is_station_code_unique(code):
        return jsonify({"error": "Bait station code already exists."}), 400

    bait_station_repository.update_bait_station_map(marker_id, code, line_id, bait_station_type_id, latitude, longitude, bait_status, other_type_details)

    station = bait_station_repository.get_station_by_id(marker_id)
    _award_map_points(badge_repository.BadgeAction.LINE_MAINTENANCE, "Updated bait station from map")
    marker = {
        "kind": "bait_station",
        "id": station["station_id"],
        "code": station["code"],
        "latitude": float(station["latitude"]),
        "longitude": float(station["longitude"]),
        "status": station["status"],
        "type_name": station["bait_station_type"],
        "other_type_details": station["other_type_details"],
        "line_id": station["line_id"],
        "line_name": station["line_name"],
    }
    return jsonify({"success": True, "marker": marker}), 200
