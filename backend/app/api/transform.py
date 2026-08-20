from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..schemas.transformation_schema import (
    ShiftTransformPayloadSchema,
    RotateTransformPayloadSchema,
    MirrorTransformPayloadSchema,
    FeedSpeedOverridePayloadSchema,
    SplitToolsPayloadSchema,
)
from ..generators.transformations import (
    transform_shift_gcode,
    transform_rotate_gcode,
    transform_mirror_gcode,
    transform_override_feeds_speeds,
    split_multitool_gcode,
)

transform_bp = Blueprint("transform", __name__, url_prefix="/api/transform")


@transform_bp.route("/shift", methods=["POST"])
def api_shift_gcode():
    data = request.get_json() or {}
    try:
        payload = ShiftTransformPayloadSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result_gcode = transform_shift_gcode(
        gcode_text=payload.gcode,
        delta_x=payload.delta_x,
        delta_y=payload.delta_y,
        delta_z=payload.delta_z,
    )
    return jsonify({"success": True, "gcode": result_gcode}), 200


@transform_bp.route("/rotate", methods=["POST"])
def api_rotate_gcode():
    data = request.get_json() or {}
    try:
        payload = RotateTransformPayloadSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result_gcode = transform_rotate_gcode(
        gcode_text=payload.gcode,
        angle_deg=payload.angle_deg,
        center_x=payload.center_x,
        center_y=payload.center_y,
    )
    return jsonify({"success": True, "gcode": result_gcode}), 200


@transform_bp.route("/mirror", methods=["POST"])
def api_mirror_gcode():
    data = request.get_json() or {}
    try:
        payload = MirrorTransformPayloadSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result_gcode = transform_mirror_gcode(
        gcode_text=payload.gcode,
        mirror_axis=payload.mirror_axis,
        origin_x=payload.origin_x,
        origin_y=payload.origin_y,
    )
    return jsonify({"success": True, "gcode": result_gcode}), 200


@transform_bp.route("/feed-speed-override", methods=["POST"])
def api_override_feeds_speeds():
    data = request.get_json() or {}
    try:
        payload = FeedSpeedOverridePayloadSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result_gcode = transform_override_feeds_speeds(
        gcode_text=payload.gcode,
        feed_multiplier=payload.feed_percent / 100.0,
        speed_multiplier=payload.speed_percent / 100.0,
    )
    return jsonify({"success": True, "gcode": result_gcode}), 200


@transform_bp.route("/split-tools", methods=["POST"])
def api_split_tools():
    data = request.get_json() or {}
    try:
        payload = SplitToolsPayloadSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    sub_programs = split_multitool_gcode(
        gcode_text=payload.gcode,
        safe_retract_z=payload.safe_retract_z,
    )
    return jsonify({"success": True, "sub_programs": sub_programs, "count": len(sub_programs)}), 200
