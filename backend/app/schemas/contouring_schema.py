"""
Pydantic Validation Schemas for 2.5D Arbitrary Profile & Contour Milling.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class ContourSegmentItemSchema(BaseModel):
    type: str = Field(default="line", description="'line' or 'arc'")
    x: float = Field(..., description="Target X endpoint in mm")
    y: float = Field(..., description="Target Y endpoint in mm")
    i: Optional[float] = Field(default=0.0, description="Arc Center X offset (mm) if type='arc'")
    j: Optional[float] = Field(default=0.0, description="Arc Center Y offset (mm) if type='arc'")
    radius: Optional[float] = Field(default=None, description="Arc radius in mm (alternative to I, J)")
    cw: Optional[bool] = Field(default=False, description="True for clockwise (G2), False for CCW (G3)")


class ContourProfilePayloadSchema(BaseModel):
    segments: List[ContourSegmentItemSchema] = Field(default_factory=list, description="Ordered list of geometry segments")
    start_point: List[float] = Field(default_factory=lambda: [0.0, 0.0], description="[X, Y] starting coordinate")
    is_closed: bool = Field(default=True, description="True if profile closes back to start")
    side: str = Field(default="left", description="'left' (climb), 'right' (conventional), or 'center'")
    lead_in_type: str = Field(default="tangential_arc", description="'tangential_arc', 'linear_45', or 'direct'")
    lead_in_radius: float = Field(default=5.0, ge=0, description="Lead-in/out arc radius or linear distance (mm)")

    # Depths & stepdowns
    target_depth_z: float = Field(default=-5.0, description="Target cut depth Z (mm)")
    stepdown_z: float = Field(default=1.5, gt=0, description="Maximum stepdown depth per pass (mm)")
    start_z: float = Field(default=0.0, description="Workpiece top surface Z (mm)")
    retract_z: Optional[float] = Field(default=5.0, description="Safe retract clearance Z (mm)")
    finish_allowance: float = Field(default=0.2, ge=0, description="Radial stock to leave for final finish pass (mm)")
    spring_pass: bool = Field(default=True, description="Repeat final full-depth pass to clean wall deflection")

    # Feeds & Speeds & Tooling
    tool_id: Optional[int] = Field(default=None, description="Tool ID from library")
    tool_diameter: Optional[float] = Field(default=3.175, gt=0, description="Tool diameter in mm")
    feed_rate_xy: Optional[float] = Field(default=800.0, gt=0, description="XY Cutting feed rate (mm/min)")
    plunge_feed: Optional[float] = Field(default=250.0, gt=0, description="Z Plunge feed rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=16000, gt=0, description="Spindle RPM")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router speed dial")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID")
    machine_profile_id: Optional[int] = Field(default=None, description="Machine profile ID")

    units: str = Field(default="mm", description="'mm' or 'inch'")
    dialect: str = Field(default="grbl", description="'grbl' or 'standard'")

    @model_validator(mode="after")
    def validate_contour(self):
        if not self.segments:
            # Provide default rectangular profile if empty
            self.segments = [
                ContourSegmentItemSchema(type="line", x=40.0, y=0.0),
                ContourSegmentItemSchema(type="line", x=40.0, y=30.0),
                ContourSegmentItemSchema(type="line", x=0.0, y=30.0),
                ContourSegmentItemSchema(type="line", x=0.0, y=0.0),
            ]
        return self
