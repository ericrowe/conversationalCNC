"""
Pydantic Validation Schemas for Step-and-Repeat Array Nesting & Soft Jaw Fixturing.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class StepAndRepeatPayloadSchema(BaseModel):
    gcode: str = Field(..., description="Single-part G-code snippet to array")
    cols_x: int = Field(default=2, ge=1, le=50, description="Number of columns along X")
    rows_y: int = Field(default=2, ge=1, le=50, description="Number of rows along Y")
    spacing_x: float = Field(default=60.0, gt=0, description="Instance spacing / pitch along X (mm)")
    spacing_y: float = Field(default=50.0, gt=0, description="Instance spacing / pitch along Y (mm)")
    layout_pattern: str = Field(default="grid", description="'grid' or 'staggered'")
    order_strategy: str = Field(default="zigzag", description="'zigzag' or 'oneway'")
    safe_z_retract: float = Field(default=5.0, description="Safe Z clearance for instance shifts (mm)")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    dialect: str = Field(default="grbl", description="'grbl' or 'standard'")


class SoftJawFixturePayloadSchema(BaseModel):
    jaw_type: str = Field(default="rectangular", description="'rectangular' or 'round_bore'")
    part_length_x: float = Field(default=60.0, gt=0, description="Part length along X (mm)")
    part_width_y: float = Field(default=40.0, gt=0, description="Part width along Y (mm)")
    part_diameter: float = Field(default=50.0, gt=0, description="Part outer diameter (mm)")
    step_depth_z: float = Field(default=3.0, gt=0, description="Clamping pocket step depth (mm)")
    jaw_gap: float = Field(default=10.0, ge=0, description="Vise jaw opening gap under clamp (mm)")
    dogbone_relief: bool = Field(default=True, description="Add 45° corner dogbone relief overcuts")

    # Tooling & cutting params
    tool_id: Optional[int] = Field(default=None, description="Tool ID from library")
    tool_diameter: float = Field(default=6.35, gt=0, description="Endmill diameter (mm)")
    tool_number: int = Field(default=1, ge=1, description="Tool number")
    tool_name: str = Field(default="Endmill", description="Tool name")
    stepdown_z: float = Field(default=1.5, gt=0, description="Z depth per pass (mm)")
    stepover_percent: float = Field(default=50.0, ge=10, le=90, description="Radial stepover %")
    feed_rate_xy: float = Field(default=1000.0, gt=0, description="XY Cutting feed (mm/min)")
    plunge_feed: float = Field(default=250.0, gt=0, description="Z Plunge feed (mm/min)")
    spindle_speed: int = Field(default=16000, gt=0, description="Spindle RPM")
    safe_z_retract: float = Field(default=5.0, description="Safe retract clearance Z (mm)")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    dialect: str = Field(default="grbl", description="'grbl' or 'standard'")
