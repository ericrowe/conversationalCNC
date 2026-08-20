from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models import db, Tool, MaterialPreset
from ..schemas import MaterialPresetCreateSchema, MaterialPresetUpdateSchema

materials_bp = Blueprint("materials", __name__, url_prefix="/api/materials")

@materials_bp.route("", methods=["GET"])
def get_materials():
    tool_id = request.args.get("tool_id", type=int)
    if tool_id:
        presets = MaterialPreset.query.filter_by(tool_id=tool_id).all()
    else:
        presets = MaterialPreset.query.all()
    return jsonify([p.to_dict() for p in presets]), 200

@materials_bp.route("/<int:preset_id>", methods=["GET"])
def get_material(preset_id):
    preset = db.session.get(MaterialPreset, preset_id)
    if not preset:
        return jsonify({"error": f"Material preset {preset_id} not found"}), 404
    return jsonify(preset.to_dict()), 200

@materials_bp.route("/tool/<int:tool_id>", methods=["POST"])
def create_material(tool_id):
    tool = db.session.get(Tool, tool_id)
    if not tool:
        return jsonify({"error": f"Tool {tool_id} not found"}), 404

    data = request.get_json() or {}
    try:
        validated = MaterialPresetCreateSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    preset = MaterialPreset(tool_id=tool_id, **validated.model_dump())
    db.session.add(preset)
    db.session.commit()
    return jsonify(preset.to_dict()), 201

@materials_bp.route("/<int:preset_id>", methods=["PUT"])
def update_material(preset_id):
    preset = db.session.get(MaterialPreset, preset_id)
    if not preset:
        return jsonify({"error": f"Material preset {preset_id} not found"}), 404

    data = request.get_json() or {}
    try:
        validated = MaterialPresetUpdateSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    for key, value in validated.model_dump(exclude_unset=True).items():
        setattr(preset, key, value)

    db.session.commit()
    return jsonify(preset.to_dict()), 200

@materials_bp.route("/<int:preset_id>", methods=["DELETE"])
def delete_material(preset_id):
    preset = db.session.get(MaterialPreset, preset_id)
    if not preset:
        return jsonify({"error": f"Material preset {preset_id} not found"}), 404

    db.session.delete(preset)
    db.session.commit()
    return jsonify({"message": f"Material preset {preset_id} deleted successfully"}), 200
