from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..schemas.sequencer_schema import JobSequenceRequestSchema
from ..generators.sequencer import generate_job_sequence, SequenceGenerationError
from ..models import db, MachineProfile
from .system import record_activity

sequencer_bp = Blueprint("sequencer", __name__, url_prefix="/api/generate/job-sequence")


@sequencer_bp.after_request
def _log_sequencer_activity(response):
    if response.status_code == 200 and request.method == "POST":
        try:
            raw = response.get_json() or {}
            payload_data = raw.get("data", raw) if isinstance(raw, dict) else {}
            if isinstance(payload_data, dict) and "gcode" in payload_data:
                gcode_text = payload_data.get("gcode", "")
                line_count = payload_data.get("line_count") or (len(gcode_text.splitlines()) if gcode_text else 0)
                record_activity(
                    operation="Multi-Operation Sequencer Program",
                    machine_name="Sequencer Job",
                    lines=line_count,
                    client_ip=request.remote_addr or "127.0.0.1",
                    estimated_time_sec=payload_data.get("estimated_time_seconds", 0.0) or 0.0
                )
        except Exception:
            pass
    return response


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
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    ops_dict_list = [op.model_dump() for op in payload.operations]

    try:
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
    except SequenceGenerationError as seq_err:
        return jsonify({
            "error": "Job sequence generation failed",
            "message": str(seq_err),
            "details": seq_err.to_dict(),
        }), 400
    except ValueError as val_err:
        return jsonify({
            "error": "Job sequence validation failed",
            "message": str(val_err),
        }), 400

    return jsonify({"success": True, "data": result}), 200
