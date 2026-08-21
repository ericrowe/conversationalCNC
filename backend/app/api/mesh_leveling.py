"""
Flask API Blueprint for Workpiece Surface Mesh Leveling & Auto-Warping.
"""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..schemas.mesh_schema import (
    MeshCandidatePointsRequestSchema,
    MeshProbeMacroRequestSchema,
    MeshParseLogRequestSchema,
    MeshWarpGCodeRequestSchema,
)
from ..generators.mesh_leveling import (
    generate_rectangular_probe_points,
    generate_circular_probe_points,
    generate_polygon_probe_points,
    generate_mesh_probe_macro,
    parse_probe_log,
    WorkpieceMeshMap,
)

mesh_bp = Blueprint("mesh", __name__, url_prefix="/api/mesh")


@mesh_bp.route("/generate-points", methods=["POST"])
def api_generate_points():
    """Generates candidate probe points based on selected boundary shape and parameters."""
    data = request.get_json() or {}
    try:
        payload = MeshCandidatePointsRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    try:
        shape = payload.shape_type.lower().strip()
        if shape == "rectangle":
            points = generate_rectangular_probe_points(
                x_min=payload.x_min,
                y_min=payload.y_min,
                x_max=payload.x_max,
                y_max=payload.y_max,
                grid_x=payload.grid_x,
                grid_y=payload.grid_y,
                margin=payload.margin,
            )
        elif shape in ("circle", "circular", "disc", "donut", "ring"):
            points = generate_circular_probe_points(
                center_x=payload.center_x,
                center_y=payload.center_y,
                radius=payload.radius,
                inner_radius=payload.inner_radius,
                grid_resolution=payload.grid_resolution,
                margin=payload.margin,
                pattern_type=payload.pattern_type,
            )
        elif shape == "polygon":
            if not payload.vertices or len(payload.vertices) < 3:
                return jsonify({"error": "Polygon must have at least 3 vertices."}), 400
            vertices_tuples = [(v[0], v[1]) for v in payload.vertices]
            points = generate_polygon_probe_points(
                vertices=vertices_tuples,
                grid_spacing=max(5.0, (payload.x_max - payload.x_min) / max(2, payload.grid_x)),
                margin=payload.margin,
            )
        else:
            return jsonify({"error": f"Unsupported shape type: {payload.shape_type}"}), 400

        # Build initial mesh map representation
        mesh_map = WorkpieceMeshMap(points, shape_type=shape)
        return jsonify({
            "success": True,
            "data": {
                "shape_type": shape,
                "point_count": len(points),
                "points": points,
                "triangles": mesh_map.triangles,
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@mesh_bp.route("/probe-macro", methods=["POST"])
def api_generate_probe_macro():
    """Generates an automated G38.2 workpiece touch-probing G-code program."""
    data = request.get_json() or {}
    try:
        payload = MeshProbeMacroRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    try:
        raw_points = [p.model_dump() for p in payload.points]
        result = generate_mesh_probe_macro(
            points=raw_points,
            search_dist=payload.search_dist,
            fast_feed=payload.fast_feed,
            slow_feed=payload.slow_feed,
            safe_traverse_z=payload.safe_traverse_z,
            plate_thickness=payload.plate_thickness,
            shape_type=payload.shape_type,
            units=payload.units,
            dialect=payload.dialect,
        )
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@mesh_bp.route("/parse-log", methods=["POST"])
def api_parse_probe_log():
    """Parses raw machine sender probe output lines into calibrated surface heightmap points."""
    data = request.get_json() or {}
    try:
        payload = MeshParseLogRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    try:
        template_dicts = [p.model_dump() for p in payload.points_template] if payload.points_template else None
        mesh_map = parse_probe_log(
            log_text=payload.log_text,
            points_template=template_dicts,
            plate_thickness=payload.plate_thickness,
        )
        return jsonify({"success": True, "data": mesh_map.to_dict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@mesh_bp.route("/warp-gcode", methods=["POST"])
def api_warp_gcode():
    """Applies dynamic surface warping to a raw G-code program using a provided heightmap."""
    data = request.get_json() or {}
    try:
        payload = MeshWarpGCodeRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    try:
        raw_points = [p.model_dump() for p in payload.points]
        mesh_map = WorkpieceMeshMap(raw_points, shape_type=payload.shape_type)
        warped_gcode = mesh_map.warp_gcode(
            gcode_text=payload.gcode_text,
            max_segment_length=payload.max_segment_length,
            fade_height=payload.fade_height,
        )

        return jsonify({
            "success": True,
            "data": {
                "gcode": warped_gcode,
                "line_count": len(warped_gcode.splitlines()),
                "z_min": mesh_map.z_min,
                "z_max": mesh_map.z_max,
                "z_span": mesh_map.z_span,
                "active_points": len(mesh_map.active_points),
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
