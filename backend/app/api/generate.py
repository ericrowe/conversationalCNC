from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models import db, MachineProfile, Tool, MaterialPreset
from ..schemas import (
    StraightPlungePayloadSchema,
    PeckDrillingPayloadSchema,
    HelicalThreadMillingPayloadSchema,
    CircularPocketPayloadSchema,
    SurfacingPayloadSchema,
)
from ..postprocessors import get_postprocessor, DIALECT_REGISTRY
from ..generators import (
    generate_straight_plunge,
    generate_peck_drilling,
    generate_helical_thread_milling,
    generate_circular_pocket,
    generate_surfacing,
    THREAD_STANDARDS,
    WorkEnvelope,
)

generate_bp = Blueprint("generate", __name__, url_prefix="/api/generate")


def _resolve_context(payload):
    """
    Helper function to resolve active machine profile, tool metadata,
    and material preset feeds/speeds from database IDs.
    """
    # 1. Resolve Machine Profile
    machine = None
    if getattr(payload, "machine_profile_id", None):
        machine = db.session.get(MachineProfile, payload.machine_profile_id)
    if not machine:
        machine = MachineProfile.query.filter_by(is_active=True).first()
    if not machine:
        machine = MachineProfile.query.first()

    dialect_name = machine.controller_dialect if machine else "grbl"
    safe_z_default = machine.safe_z_retract if machine else 5.0
    rapid_feed_default = machine.rapid_feed_rate if machine else 5000.0
    spindle_dwell_default = machine.spindle_dwell_seconds if machine else 2.0
    min_rpm = machine.min_spindle_rpm if machine else 16000
    max_rpm = machine.max_spindle_rpm if machine else 27000
    spindle_type = getattr(payload, "spindle_type", None) or (machine.spindle_type if machine else "router")
    router_model = getattr(payload, "router_model", None) or (machine.router_model if machine else "dewalt_611")

    # 2. Resolve Tool & Material Presets
    tool_number = 1
    tool_name = ""
    tool_diameter = getattr(payload, "tool_diameter", None)
    resolved_feed_xy = getattr(payload, "feed_rate_xy", None)
    resolved_plunge_feed = getattr(payload, "plunge_feed", None)
    resolved_spindle_speed = getattr(payload, "spindle_speed", None)

    preset_id = getattr(payload, "material_preset_id", None)
    if preset_id:
        preset = db.session.get(MaterialPreset, preset_id)
        if preset:
            if not resolved_plunge_feed:
                resolved_plunge_feed = preset.plunge_rate_z
            if not resolved_feed_xy:
                resolved_feed_xy = preset.feed_rate_xy
            if not resolved_spindle_speed:
                resolved_spindle_speed = preset.spindle_speed
            if not getattr(payload, "tool_id", None) and preset.tool:
                payload.tool_id = preset.tool.id

    tool_id = getattr(payload, "tool_id", None)
    if tool_id:
        tool = db.session.get(Tool, tool_id)
        if tool:
            tool_number = tool.tool_number
            tool_name = tool.name
            if not tool_diameter:
                tool_diameter = tool.diameter

    # Fallback defaults
    if not resolved_plunge_feed:
        resolved_plunge_feed = 200.0
    if not resolved_feed_xy:
        resolved_feed_xy = 800.0
    if not resolved_spindle_speed:
        resolved_spindle_speed = 16000
    if not tool_diameter:
        tool_diameter = 3.175

    work_envelope = None
    if machine:
        work_envelope = WorkEnvelope(
            work_area_x=machine.work_area_x,
            work_area_y=machine.work_area_y,
            work_area_z=machine.work_area_z,
        )

    postprocessor = get_postprocessor(dialect_name)

    return {
        "machine": machine,
        "postprocessor": postprocessor,
        "work_envelope": work_envelope,
        "tool_number": tool_number,
        "tool_name": tool_name,
        "tool_diameter": tool_diameter,
        "feed_rate_xy": resolved_feed_xy,
        "plunge_feed": resolved_plunge_feed,
        "spindle_speed": resolved_spindle_speed,
        "safe_z_default": safe_z_default,
        "rapid_feed_default": rapid_feed_default,
        "spindle_dwell_default": spindle_dwell_default,
        "spindle_type": spindle_type,
        "router_model": router_model,
        "min_rpm": min_rpm,
        "max_rpm": max_rpm,
    }


@generate_bp.route("/dialects", methods=["GET"])
def get_available_dialects():
    return jsonify({
        "available_dialects": list(set(DIALECT_REGISTRY.keys())),
        "default": "grbl"
    }), 200


@generate_bp.route("/thread-standards", methods=["GET"])
def get_thread_standards():
    """Returns database of standard Metric ISO and Imperial UNC/UNF threads."""
    return jsonify({
        "standards": THREAD_STANDARDS,
        "categories": {
            "metric": [k for k, v in THREAD_STANDARDS.items() if v["type"] == "metric"],
            "imperial_unc": [k for k, v in THREAD_STANDARDS.items() if v["type"] == "imperial_unc"],
            "imperial_unf": [k for k, v in THREAD_STANDARDS.items() if v["type"] == "imperial_unf"],
        }
    }), 200


@generate_bp.route("/drilling/straight-plunge", methods=["POST"])
def generate_straight_plunge_gcode():
    data = request.get_json() or {}
    try:
        payload = StraightPlungePayloadSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    ctx = _resolve_context(payload)

    try:
        program = generate_straight_plunge(
            holes=payload.holes,
            target_depth_z=payload.target_depth_z,
            start_z=payload.start_z,
            retract_z=payload.retract_z if payload.retract_z is not None else ctx["safe_z_default"],
            plunge_feed=ctx["plunge_feed"],
            rapid_feed=payload.rapid_feed or ctx["rapid_feed_default"],
            spindle_speed=ctx["spindle_speed"],
            dwell_seconds=payload.dwell_seconds,
            spindle_dwell_seconds=(
                payload.spindle_dwell_seconds
                if payload.spindle_dwell_seconds is not None
                else ctx["spindle_dwell_default"]
            ),
            approach_clearance=payload.approach_clearance,
            units=payload.units,
            tool_number=ctx["tool_number"],
            tool_name=ctx["tool_name"],
            spindle_type=ctx["spindle_type"],
            router_model=ctx["router_model"],
            router_dial=payload.router_dial,
            min_spindle_rpm=ctx["min_rpm"],
            max_spindle_rpm=ctx["max_rpm"],
            postprocessor=ctx["postprocessor"],
            work_envelope=ctx["work_envelope"],
            park_x=payload.park_x,
            park_y=payload.park_y,
            park_z=payload.park_z,
        )
    except ValueError as val_err:
        return jsonify({"error": "Generation error", "message": str(val_err)}), 400

    return jsonify({
        "success": True,
        "data": program.to_dict(),
        "machine_profile": ctx["machine"].to_dict() if ctx["machine"] else None,
        "dialect_used": ctx["postprocessor"].dialect_name,
    }), 200


@generate_bp.route("/drilling/peck", methods=["POST"])
def generate_peck_drilling_gcode():
    data = request.get_json() or {}
    try:
        payload = PeckDrillingPayloadSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    ctx = _resolve_context(payload)

    try:
        program = generate_peck_drilling(
            holes=payload.holes,
            target_depth_z=payload.target_depth_z,
            peck_depth=payload.peck_depth,
            peck_retract_type=payload.peck_retract_type,
            start_z=payload.start_z,
            retract_z=payload.retract_z if payload.retract_z is not None else ctx["safe_z_default"],
            plunge_feed=ctx["plunge_feed"],
            rapid_feed=payload.rapid_feed or ctx["rapid_feed_default"],
            spindle_speed=ctx["spindle_speed"],
            dwell_seconds=payload.dwell_seconds,
            spindle_dwell_seconds=(
                payload.spindle_dwell_seconds
                if payload.spindle_dwell_seconds is not None
                else ctx["spindle_dwell_default"]
            ),
            approach_clearance=payload.approach_clearance,
            units=payload.units,
            tool_number=ctx["tool_number"],
            tool_name=ctx["tool_name"],
            spindle_type=ctx["spindle_type"],
            router_model=ctx["router_model"],
            router_dial=payload.router_dial,
            min_spindle_rpm=ctx["min_rpm"],
            max_spindle_rpm=ctx["max_rpm"],
            postprocessor=ctx["postprocessor"],
            work_envelope=ctx["work_envelope"],
            park_x=payload.park_x,
            park_y=payload.park_y,
            park_z=payload.park_z,
        )
    except ValueError as val_err:
        return jsonify({"error": "Generation error", "message": str(val_err)}), 400

    return jsonify({
        "success": True,
        "data": program.to_dict(),
        "machine_profile": ctx["machine"].to_dict() if ctx["machine"] else None,
        "dialect_used": ctx["postprocessor"].dialect_name,
    }), 200


@generate_bp.route("/thread-milling", methods=["POST"])
def generate_thread_milling_gcode():
    data = request.get_json() or {}
    try:
        payload = HelicalThreadMillingPayloadSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    ctx = _resolve_context(payload)

    tool_dia = payload.tool_diameter or ctx["tool_diameter"]

    try:
        program = generate_helical_thread_milling(
            holes=payload.holes,
            nominal_diameter=payload.nominal_diameter,
            pitch=payload.pitch,
            thread_length=payload.thread_length,
            tool_diameter=tool_dia,
            thread_type=payload.thread_type,
            thread_hand=payload.thread_hand,
            milling_direction=payload.milling_direction,
            radial_passes=payload.radial_passes,
            spring_passes=payload.spring_passes,
            start_z=payload.start_z,
            retract_z=payload.retract_z if payload.retract_z is not None else ctx["safe_z_default"],
            feed_rate_xy=payload.feed_rate_xy or ctx["feed_rate_xy"],
            plunge_feed=payload.plunge_feed or ctx["plunge_feed"],
            rapid_feed=payload.rapid_feed or ctx["rapid_feed_default"],
            spindle_speed=ctx["spindle_speed"],
            spindle_dwell_seconds=(
                payload.spindle_dwell_seconds
                if payload.spindle_dwell_seconds is not None
                else ctx["spindle_dwell_default"]
            ),
            units=payload.units,
            tool_number=ctx["tool_number"],
            tool_name=ctx["tool_name"],
            spindle_type=ctx["spindle_type"],
            router_model=ctx["router_model"],
            router_dial=payload.router_dial,
            min_spindle_rpm=ctx["min_rpm"],
            max_spindle_rpm=ctx["max_rpm"],
            postprocessor=ctx["postprocessor"],
            work_envelope=ctx["work_envelope"],
            park_x=payload.park_x,
            park_y=payload.park_y,
            park_z=payload.park_z,
        )
    except ValueError as val_err:
        return jsonify({"error": "Generation error", "message": str(val_err)}), 400

    return jsonify({
        "success": True,
        "data": program.to_dict(),
        "machine_profile": ctx["machine"].to_dict() if ctx["machine"] else None,
        "dialect_used": ctx["postprocessor"].dialect_name,
    }), 200


@generate_bp.route("/pocket/circular", methods=["POST"])
def generate_circular_pocket_gcode():
    data = request.get_json() or {}
    try:
        payload = CircularPocketPayloadSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    ctx = _resolve_context(payload)

    tool_dia = payload.tool_diameter or ctx["tool_diameter"]

    try:
        program = generate_circular_pocket(
            pockets=payload.pockets,
            pocket_diameter=payload.pocket_diameter,
            target_depth_z=payload.target_depth_z,
            tool_diameter=tool_dia,
            stepdown_z=payload.stepdown_z,
            stepover_percent=payload.stepover_percent,
            finish_allowance=payload.finish_allowance,
            finish_feed_xy=payload.finish_feed_xy,
            start_z=payload.start_z,
            retract_z=payload.retract_z if payload.retract_z is not None else ctx["safe_z_default"],
            feed_rate_xy=payload.feed_rate_xy or ctx["feed_rate_xy"],
            plunge_feed=payload.plunge_feed or ctx["plunge_feed"],
            rapid_feed=payload.rapid_feed or ctx["rapid_feed_default"],
            spindle_speed=ctx["spindle_speed"],
            spindle_dwell_seconds=(
                payload.spindle_dwell_seconds
                if payload.spindle_dwell_seconds is not None
                else ctx["spindle_dwell_default"]
            ),
            units=payload.units,
            tool_number=ctx["tool_number"],
            tool_name=ctx["tool_name"],
            spindle_type=ctx["spindle_type"],
            router_model=ctx["router_model"],
            router_dial=payload.router_dial,
            min_spindle_rpm=ctx["min_rpm"],
            max_spindle_rpm=ctx["max_rpm"],
            postprocessor=ctx["postprocessor"],
            work_envelope=ctx["work_envelope"],
            park_x=payload.park_x,
            park_y=payload.park_y,
            park_z=payload.park_z,
        )
    except ValueError as val_err:
        return jsonify({"error": "Generation error", "message": str(val_err)}), 400

    return jsonify({
        "success": True,
        "data": program.to_dict(),
        "machine_profile": ctx["machine"].to_dict() if ctx["machine"] else None,
        "dialect_used": ctx["postprocessor"].dialect_name,
    }), 200


@generate_bp.route("/surfacing", methods=["POST"])
def generate_surfacing_gcode():
    data = request.get_json() or {}
    try:
        payload = SurfacingPayloadSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    ctx = _resolve_context(payload)

    tool_dia = payload.tool_diameter or ctx["tool_diameter"]

    try:
        program = generate_surfacing(
            length_x=payload.length_x,
            width_y=payload.width_y,
            origin_x=payload.origin_x,
            origin_y=payload.origin_y,
            origin_mode=payload.origin_mode,
            total_depth_z=payload.total_depth_z,
            stepdown_z=payload.stepdown_z,
            tool_diameter=tool_dia,
            stepover_percent=payload.stepover_percent,
            cut_direction=payload.cut_direction,
            overtravel=payload.overtravel,
            start_z=payload.start_z,
            retract_z=payload.retract_z if payload.retract_z is not None else ctx["safe_z_default"],
            feed_rate_xy=payload.feed_rate_xy or ctx["feed_rate_xy"],
            plunge_feed=payload.plunge_feed or ctx["plunge_feed"],
            rapid_feed=payload.rapid_feed or ctx["rapid_feed_default"],
            spindle_speed=ctx["spindle_speed"],
            spindle_dwell_seconds=(
                payload.spindle_dwell_seconds
                if payload.spindle_dwell_seconds is not None
                else ctx["spindle_dwell_default"]
            ),
            units=payload.units,
            tool_number=ctx["tool_number"],
            tool_name=ctx["tool_name"],
            spindle_type=ctx["spindle_type"],
            router_model=ctx["router_model"],
            router_dial=payload.router_dial,
            min_spindle_rpm=ctx["min_rpm"],
            max_spindle_rpm=ctx["max_rpm"],
            postprocessor=ctx["postprocessor"],
            work_envelope=ctx["work_envelope"],
            park_x=payload.park_x,
            park_y=payload.park_y,
            park_z=payload.park_z,
        )
    except ValueError as val_err:
        return jsonify({"error": "Generation error", "message": str(val_err)}), 400

    return jsonify({
        "success": True,
        "data": program.to_dict(),
        "machine_profile": ctx["machine"].to_dict() if ctx["machine"] else None,
        "dialect_used": ctx["postprocessor"].dialect_name,
    }), 200
