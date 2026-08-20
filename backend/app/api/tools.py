from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models import db, Tool
from ..schemas import ToolCreateSchema, ToolUpdateSchema

tools_bp = Blueprint("tools", __name__, url_prefix="/api/tools")

@tools_bp.route("", methods=["GET"])
def get_tools():
    tools = Tool.query.order_by(Tool.tool_number).all()
    return jsonify([t.to_dict() for t in tools]), 200

@tools_bp.route("/<int:tool_id>", methods=["GET"])
def get_tool(tool_id):
    tool = db.session.get(Tool, tool_id)
    if not tool:
        return jsonify({"error": f"Tool {tool_id} not found"}), 404
    return jsonify(tool.to_dict()), 200

@tools_bp.route("", methods=["POST"])
def create_tool():
    data = request.get_json() or {}
    try:
        validated = ToolCreateSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    existing = Tool.query.filter_by(tool_number=validated.tool_number).first()
    if existing:
        return jsonify({"error": f"Tool number T{validated.tool_number} already exists."}), 400

    tool = Tool(**validated.model_dump())
    db.session.add(tool)
    db.session.commit()
    return jsonify(tool.to_dict()), 201

@tools_bp.route("/<int:tool_id>", methods=["PUT"])
def update_tool(tool_id):
    tool = db.session.get(Tool, tool_id)
    if not tool:
        return jsonify({"error": f"Tool {tool_id} not found"}), 404

    data = request.get_json() or {}
    try:
        validated = ToolUpdateSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    update_data = validated.model_dump(exclude_unset=True)
    if "tool_number" in update_data and update_data["tool_number"] != tool.tool_number:
        existing = Tool.query.filter_by(tool_number=update_data["tool_number"]).first()
        if existing:
            return jsonify({"error": f"Tool number T{update_data['tool_number']} already exists."}), 400

    for key, value in update_data.items():
        setattr(tool, key, value)

    db.session.commit()
    return jsonify(tool.to_dict()), 200

@tools_bp.route("/<int:tool_id>", methods=["DELETE"])
def delete_tool(tool_id):
    tool = db.session.get(Tool, tool_id)
    if not tool:
        return jsonify({"error": f"Tool {tool_id} not found"}), 404

    db.session.delete(tool)
    db.session.commit()
    return jsonify({"message": f"Tool {tool_id} deleted successfully"}), 200
