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


class RectangularPocketPayloadSchema(BaseModel):
    origin_x: float = Field(default=0.0, description="Origin X coordinate")
    origin_y: float = Field(default=0.0, description="Origin Y coordinate")
    length_x: float = Field(..., gt=0, description="Pocket length along X (mm)")
    width_y: float = Field(..., gt=0, description="Pocket width along Y (mm)")
    corner_radius: float = Field(default=0.0, ge=0, description="Corner fillet radius in mm")
    origin_mode: str = Field(default="center", description="'center' or 'corner'")
    target_depth_z: float = Field(..., description="Target pocket depth Z")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Endmill cutting diameter in mm")
    stepdown_z: float = Field(default=1.5, gt=0, description="Z depth per pass")
    stepover_percent: float = Field(default=60.0, gt=0, le=95.0, description="Radial stepover % of tool diameter")
    finish_pass_allowance: float = Field(default=0.3, ge=0, description="Stock allowance for finish perimeter pass")
    finish_feed: Optional[float] = Field(default=None, gt=0, description="Finish pass feed rate")
    entry_strategy: str = Field(default="helical_ramp", description="'helical_ramp' or 'plunge'")
    ramp_angle_deg: float = Field(default=2.5, gt=0, le=45.0, description="Helical ramp descent angle")
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


class RectangularBossPayloadSchema(BaseModel):
    boss_origin_x: float = Field(default=0.0, description="Boss island Origin X")
    boss_origin_y: float = Field(default=0.0, description="Boss island Origin Y")
    boss_length_x: float = Field(..., gt=0, description="Boss length along X (mm)")
    boss_width_y: float = Field(..., gt=0, description="Boss width along Y (mm)")
    stock_length_x: float = Field(..., gt=0, description="Stock boundary length along X (mm)")
    stock_width_y: float = Field(..., gt=0, description="Stock boundary width along Y (mm)")
    boss_corner_radius: float = Field(default=0.0, ge=0, description="Boss corner fillet radius in mm")
    boss_origin_mode: str = Field(default="center", description="'center' or 'corner'")
    target_depth_z: float = Field(..., description="Target machining depth Z")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Endmill cutting diameter in mm")
    stepdown_z: float = Field(default=1.5, gt=0, description="Z depth per pass")
    stepover_percent: float = Field(default=60.0, gt=0, le=95.0, description="Radial stepover % of tool diameter")
    start_z: float = Field(default=0.0, description="Top surface of workpiece")
    retract_z: Optional[float] = Field(default=None, description="Clearance retract height")
    feed_rate_xy: Optional[float] = Field(default=None, gt=0, description="Cutting feed rate (mm/min)")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Plunge feed rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    tool_id: Optional[int] = Field(default=None, description="Database Tool ID")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID")
    machine_profile_id: Optional[int] = Field(default=None, description="Machine profile ID")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router speed dial 1-6")


class CircularBossPayloadSchema(BaseModel):
    boss_center_x: float = Field(default=0.0, description="Boss center X coordinate (mm)")
    boss_center_y: float = Field(default=0.0, description="Boss center Y coordinate (mm)")
    boss_diameter: float = Field(..., gt=0, description="Finished cylindrical shaft diameter (mm)")
    stock_shape: str = Field(default="circle", description="'circle' (round bar) or 'rectangle'")
    stock_diameter: Optional[float] = Field(default=25.0, description="Outer diameter of round stock (mm)")
    stock_length_x: Optional[float] = Field(default=30.0, description="Stock length X if rectangular stock (mm)")
    stock_width_y: Optional[float] = Field(default=30.0, description="Stock width Y if rectangular stock (mm)")
    target_depth_z: float = Field(..., description="Target machining depth Z / shaft length (mm)")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Endmill cutting diameter in mm")
    stepdown_z: float = Field(default=1.0, gt=0, description="Z depth per pass")
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
