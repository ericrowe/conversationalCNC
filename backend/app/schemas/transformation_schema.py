from typing import Optional
from pydantic import BaseModel, Field

class ShiftTransformPayloadSchema(BaseModel):
    gcode: str = Field(..., description="Raw G-Code text to transform")
    delta_x: float = Field(default=0.0, description="Offset along X (mm)")
    delta_y: float = Field(default=0.0, description="Offset along Y (mm)")
    delta_z: float = Field(default=0.0, description="Offset along Z (mm)")

class RotateTransformPayloadSchema(BaseModel):
    gcode: str = Field(..., description="Raw G-Code text to transform")
    angle_deg: float = Field(..., description="Rotation angle in degrees")
    center_x: float = Field(default=0.0, description="Pivot center X (mm)")
    center_y: float = Field(default=0.0, description="Pivot center Y (mm)")

class MirrorTransformPayloadSchema(BaseModel):
    gcode: str = Field(..., description="Raw G-Code text to transform")
    mirror_axis: str = Field(default="x", description="'x' (mirrors Y) or 'y' (mirrors X)")
    origin_x: float = Field(default=0.0, description="Mirror origin X (mm)")
    origin_y: float = Field(default=0.0, description="Mirror origin Y (mm)")

class FeedSpeedOverridePayloadSchema(BaseModel):
    gcode: str = Field(..., description="Raw G-Code text to transform")
    feed_percent: float = Field(default=100.0, gt=0, description="Feed override percentage (e.g. 80 for 80%)")
    speed_percent: float = Field(default=100.0, gt=0, description="Spindle speed override percentage")

class SplitToolsPayloadSchema(BaseModel):
    gcode: str = Field(..., description="Raw multi-tool G-Code text to split")
    safe_retract_z: float = Field(default=5.0, description="Safe retract Z clearance for sub-programs")
