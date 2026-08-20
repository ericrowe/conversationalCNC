from typing import Optional
from pydantic import BaseModel, Field

class SurfacingPayloadSchema(BaseModel):
    length_x: float = Field(..., gt=0, description="Stock length along X (mm)")
    width_y: float = Field(..., gt=0, description="Stock width along Y (mm)")
    origin_x: float = Field(default=0.0, description="Origin X reference coordinate")
    origin_y: float = Field(default=0.0, description="Origin Y reference coordinate")
    origin_mode: str = Field(default="corner", description="'corner' (lower-left 0,0) or 'center'")
    total_depth_z: float = Field(default=1.0, gt=0, description="Total depth of cut (mm)")
    stepdown_z: float = Field(default=0.5, gt=0, description="Depth per Z pass (mm)")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Flycutter/endmill diameter (mm)")
    stepover_percent: float = Field(default=70.0, gt=0, le=95.0, description="Stepover percentage (1-95%)")
    cut_direction: str = Field(default="zigzag", description="'zigzag' (bidirectional) or 'climb_oneway'")
    overtravel: float = Field(default=2.0, ge=0, description="Clearance past stock edges before turn/lift (mm)")
    start_z: float = Field(default=0.0, description="Top surface of workpiece")
    retract_z: Optional[float] = Field(default=None, description="Clearance retract height")
    feed_rate_xy: Optional[float] = Field(default=None, gt=0, description="Cutting feed rate (mm/min)")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Plunge feed rate (mm/min)")
    rapid_feed: Optional[float] = Field(default=None, gt=0, description="Rapid traverse feed rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    spindle_dwell_seconds: Optional[float] = Field(default=None, ge=0, description="Spindle spin-up delay")
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
