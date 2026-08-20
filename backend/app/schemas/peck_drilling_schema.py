from typing import List, Tuple, Optional
from pydantic import BaseModel, Field, model_validator

class PeckDrillingPayloadSchema(BaseModel):
    holes: Optional[List[Tuple[float, float]]] = None
    x: Optional[float] = None
    y: Optional[float] = None
    target_depth_z: float = Field(..., description="Target drill depth Z (e.g. -15.0)")
    peck_depth: float = Field(..., gt=0, description="Peck increment depth Q in mm")
    peck_retract_type: str = Field(default="full_retract", description="'full_retract' (G83 chip clear) or 'chip_break' (G73)")
    start_z: float = Field(default=0.0, description="Top surface of workpiece")
    retract_z: Optional[float] = Field(default=None, description="Clearance retract height")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Feed rate for plunge (mm/min)")
    rapid_feed: Optional[float] = Field(default=None, gt=0, description="Rapid travel rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    dwell_seconds: float = Field(default=0.0, ge=0, description="Dwell time at hole bottom")
    spindle_dwell_seconds: Optional[float] = Field(default=None, ge=0, description="Spindle spin-up dwell")
    approach_clearance: float = Field(default=1.0, ge=0, description="Clearance above stock for rapid")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    tool_id: Optional[int] = Field(default=None, description="Database Tool ID")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID")
    machine_profile_id: Optional[int] = Field(default=None, description="Target machine profile ID")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router speed dial 1-6")
    park_x: Optional[float] = 0.0
    park_y: Optional[float] = 0.0
    park_z: Optional[float] = None

    @model_validator(mode="after")
    def validate_hole_coordinates(self):
        if not self.holes and (self.x is None or self.y is None):
            raise ValueError("Must provide either a list of 'holes' or both 'x' and 'y' coordinates.")
        if not self.holes and self.x is not None and self.y is not None:
            self.holes = [(self.x, self.y)]
        return self
