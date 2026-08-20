from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..schemas.jog_schema import (
    JogStepRequestSchema,
    JogZeroRequestSchema,
    JogGotoOriginRequestSchema,
    JogSpindleRequestSchema,
)
from ..generators.jog import (
    generate_jog_command,
    generate_zero_wcs_command,
    generate_goto_origin_command,
    generate_spindle_manual_command,
)
from ..models import db, MachineProfile

jog_bp = Blueprint("jog", __name__, url_prefix="/api/jog")


def _get_active_dialect() -> str:
    machine = MachineProfile.query.filter_by(is_active=True).first()
    if not machine:
        machine = MachineProfile.query.first()
    return machine.controller_dialect if machine else "grbl"


@jog_bp.route("/step", methods=["POST"])
def api_jog_step():
    data = request.get_json() or {}
    if "dialect" not in data:
        data["dialect"] = _get_active_dialect()

    try:
        payload = JogStepRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result = generate_jog_command(
        axis=payload.axis,
        distance=payload.distance,
        feed_rate=payload.feed_rate,
        units=payload.units,
        dialect=payload.dialect,
    )
    return jsonify({"success": True, "data": result}), 200


@jog_bp.route("/zero", methods=["POST"])
def api_jog_zero():
    data = request.get_json() or {}
    try:
        payload = JogZeroRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result = generate_zero_wcs_command(
        axes=payload.axes,
        wcs_slot=payload.wcs_slot,
    )
    return jsonify({"success": True, "data": result}), 200


@jog_bp.route("/goto-origin", methods=["POST"])
def api_jog_goto_origin():
    data = request.get_json() or {}
    try:
        payload = JogGotoOriginRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result = generate_goto_origin_command(
        safe_z_retract=payload.safe_z_retract,
        units=payload.units,
    )
    return jsonify({"success": True, "data": result}), 200


@jog_bp.route("/spindle", methods=["POST"])
def api_jog_spindle():
    data = request.get_json() or {}
    try:
        payload = JogSpindleRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    result = generate_spindle_manual_command(
        rpm=payload.rpm,
        state=payload.state,
        clockwise=payload.clockwise,
    )
    return jsonify({"success": True, "data": result}), 200
