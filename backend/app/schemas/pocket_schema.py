from typing import List, Tuple, Optional
from pydantic import BaseModel, Field, model_validator

class CircularPocketPayloadSchema(BaseModel):
    pockets: Optional[List[Tuple[float, float]]] = None
    x: Optional[float] = None
    y: Optional[float] = None
    pocket_diameter: float = Field(..., gt=0, description="Target circular pocket diameter in mm")
    target_depth_z: float = Field(..., description="Target pocket depth Z")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Endmill cutting diameter in mm")
    stepdown_z: float = Field(default=1.5, gt=0, description="Z depth per pass")
    stepover_percent: float = Field(default=50.0, gt=0, le=95.0, description="Radial stepover % of tool diameter")
    finish_allowance: float = Field(default=0.2, ge=0, description="Stock allowance for finish perimeter pass")
    finish_feed_xy: Optional[float] = Field(default=None, gt=0, description="Finish pass feed rate")
    start_z: float = Field(default=0.0, description="Top surface of workpiece")
    retract_z: Optional[float] = Field(default=None, description="Clearance retract height")
    feed_rate_xy: Optional[float] = Field(default=None, gt=0, description="Cutting feed rate (mm/min)")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Plunge feed rate (mm/min)")
    rapid_feed: Optional[float] = Field(default=None, gt=0, description="Rapid traverse feed rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    spindle_dwell_seconds: Optional[float] = Field(default=None, ge=0, description="Spindle dwell")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    tool_id: Optional[int] = Field(default=None, description="Database Tool ID")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID")
    machine_profile_id: Optional[int] = Field(default=None, description="Machine profile ID")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router speed dial 1-6")
    park_x: Optional[float] = 0.0
    park_y: Optional[float] = 0.0
    park_z: Optional[float] = None

    @model_validator(mode="after")
    def validate_pocket_coordinates(self):
        if not self.pockets and (self.x is None or self.y is None):
            raise ValueError("Must provide either a list of 'pockets' or both 'x' and 'y' coordinates.")
        if not self.pockets and self.x is not None and self.y is not None:
            self.pockets = [(self.x, self.y)]
        return self
