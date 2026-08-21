from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..schemas.sequencer_schema import JobSequenceRequestSchema
from ..generators.sequencer import generate_job_sequence
from ..models import db, MachineProfile

sequencer_bp = Blueprint("sequencer", __name__, url_prefix="/api/generate/job-sequence")


def _get_active_machine():
    machine = MachineProfile.query.filter_by(is_active=True).first()
    if not machine:
        machine = MachineProfile.query.first()
    return machine


@sequencer_bp.route("", methods=["POST"])
def api_generate_job_sequence():
    data = request.get_json() or {}
    machine = _get_active_machine()

    if "dialect" not in data and machine:
        data["dialect"] = machine.controller_dialect
    if "safe_z_retract" not in data and machine:
        data["safe_z_retract"] = machine.safe_z_retract

    try:
        payload = JobSequenceRequestSchema(**data)
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400

    ops_dict_list = [op.model_dump() for op in payload.operations]

    result = generate_job_sequence(
        job_name=payload.job_name,
        operations=ops_dict_list,
        safe_z_retract=payload.safe_z_retract,
        units=payload.units,
        dialect=payload.dialect,
        optimize_tool_order=payload.optimize_tool_order,
        park_x=payload.park_x,
        park_y=payload.park_y,
        park_z=payload.park_z,
        apply_mesh_leveling=payload.apply_mesh_leveling,
        mesh_data=payload.mesh_data,
        mesh_max_segment_length=payload.mesh_max_segment_length,
    )
    return jsonify({"success": True, "data": result}), 200
