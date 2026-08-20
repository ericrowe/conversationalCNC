from flask import Blueprint, request, jsonify
from pydantic import BaseModel, Field
from typing import Optional
from ..generators.feeds_speeds import calculate_feeds_and_speeds, MATERIAL_PHYSICS_CATALOG

calculator_bp = Blueprint("calculator", __name__, url_prefix="/api/calculator")

class FeedsSpeedsRequestSchema(BaseModel):
    material_key: str = Field(default="softwood_pine", description="Material key")
    tool_diameter_mm: float = Field(..., gt=0, description="Tool diameter (mm)")
    num_flutes: int = Field(default=2, ge=1, description="Number of tool flutes")
    stepover_mm: Optional[float] = Field(default=None, description="Radial stepover (mm)")
    stepdown_mm: Optional[float] = Field(default=None, description="Axial depth of cut (mm)")
    tool_stickout_mm: Optional[float] = Field(default=None, description="Tool stickout length (mm)")
    max_spindle_rpm: Optional[int] = Field(default=27000, gt=0, description="Max machine spindle RPM")
    min_spindle_rpm: Optional[int] = Field(default=10000, ge=0, description="Min machine spindle RPM")


@calculator_bp.route("/materials-catalog", methods=["GET"])
def get_materials_catalog():
    return jsonify({"success": True, "materials": MATERIAL_PHYSICS_CATALOG}), 200


@calculator_bp.route("/feeds-speeds", methods=["POST"])
def api_calculate_feeds_speeds():
    data = request.get_json() or {}
    try:
        payload = FeedsSpeedsRequestSchema(**data)
    except Exception as e:
        return jsonify({"error": "Validation error", "details": str(e)}), 400

    try:
        result = calculate_feeds_and_speeds(
            material_key=payload.material_key,
            tool_diameter_mm=payload.tool_diameter_mm,
            num_flutes=payload.num_flutes,
            stepover_mm=payload.stepover_mm,
            stepdown_mm=payload.stepdown_mm,
            tool_stickout_mm=payload.tool_stickout_mm,
            max_spindle_rpm=payload.max_spindle_rpm or 27000,
            min_spindle_rpm=payload.min_spindle_rpm or 10000,
        )
    except ValueError as val_err:
        return jsonify({"error": "Calculation error", "message": str(val_err)}), 400

    return jsonify({"success": True, "data": result}), 200
