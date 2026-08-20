from typing import List, Tuple, Optional
from pydantic import BaseModel, Field, model_validator

class StraightPlungePayloadSchema(BaseModel):
    # Support either a list of coordinates or a single coordinate (x, y)
    holes: Optional[List[Tuple[float, float]]] = None
    x: Optional[float] = None
    y: Optional[float] = None
    target_depth_z: float = Field(..., description="Target drill depth Z (e.g. -5.0 or 5.0 below start_z)")
    start_z: float = Field(default=0.0, description="Top surface of workpiece")
    retract_z: Optional[float] = Field(default=None, description="Clearance retract height")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Feed rate for plunge (mm/min)")
    rapid_feed: Optional[float] = Field(default=None, gt=0, description="Rapid travel rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    dwell_seconds: float = Field(default=0.0, ge=0, description="Dwell time at hole bottom")
    spindle_dwell_seconds: Optional[float] = Field(default=None, ge=0, description="Spindle spin-up dwell")
    approach_clearance: float = Field(default=1.0, ge=0, description="Clearance above start_z for rapid")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    tool_id: Optional[int] = Field(default=None, description="Database Tool ID to pull metadata/speeds from")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID to resolve feeds/speeds")
    machine_profile_id: Optional[int] = Field(default=None, description="Target machine profile ID (defaults to active)")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', 'makita_rt0701', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router speed dial setting (1-6)")
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
