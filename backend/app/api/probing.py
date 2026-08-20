from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..schemas.probing_schema import ZProbeRequestSchema, CornerXYZProbeRequestSchema
from ..generators.probing import (
    generate_z_probe_macro,
    generate_corner_xyz_probe_macro,
    generate_homing_macro,
)

probing_bp = Blueprint("probing", __name__, url_prefix="/api/probing")


@probing_bp.route("/z-touch-plate", methods=["POST"])
def api_z_touch_plate():
    data = request.get_json() or {}
    try:
        payload = ZProbeRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result = generate_z_probe_macro(
        plate_thickness=payload.plate_thickness,
        search_dist=payload.search_dist,
        fast_feed=payload.fast_feed,
        slow_feed=payload.slow_feed,
        retract_height=payload.retract_height,
        wcs_slot=payload.wcs_slot,
        units=payload.units,
    )
    return jsonify({"success": True, "data": result}), 200


@probing_bp.route("/corner-xyz", methods=["POST"])
def api_corner_xyz():
    data = request.get_json() or {}
    try:
        payload = CornerXYZProbeRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result = generate_corner_xyz_probe_macro(
        tool_diameter=payload.tool_diameter,
        plate_thickness=payload.plate_thickness,
        block_x_lip=payload.block_x_lip,
        block_y_lip=payload.block_y_lip,
        search_dist=payload.search_dist,
        fast_feed=payload.fast_feed,
        slow_feed=payload.slow_feed,
        retract_z=payload.retract_z,
        wcs_slot=payload.wcs_slot,
        units=payload.units,
    )
    return jsonify({"success": True, "data": result}), 200


@probing_bp.route("/homing", methods=["GET", "POST"])
def api_homing_macro():
    result = generate_homing_macro()
    return jsonify({"success": True, "data": result}), 200
