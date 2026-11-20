from typing import Literal, Optional
from pydantic import BaseModel, Field

class LinearSlotPayloadSchema(BaseModel):
    start_x: float = Field(..., description="Start X coordinate (mm)")
    start_y: float = Field(..., description="Start Y coordinate (mm)")
    end_x: float = Field(..., description="End X coordinate (mm)")
    end_y: float = Field(..., description="End Y coordinate (mm)")
    slot_width: float = Field(..., gt=0, description="Target slot width (mm)")
    target_depth_z: float = Field(..., description="Target slot depth Z")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Endmill cutting diameter in mm")
    stepdown_z: float = Field(default=1.0, gt=0, description="Z depth per pass")
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
    cutting_strategy: Literal["conventional", "trochoidal"] = Field(
        default="conventional", description="Slotting strategy ('conventional' or 'trochoidal')"
    )
    trochoidal_stepover_pct: float = Field(
        default=15.0, ge=5.0, le=40.0, description="Trochoidal forward stepover (% of tool diameter)"
    )


class ArcSlotPayloadSchema(BaseModel):
    center_x: float = Field(..., description="Arc center X coordinate (mm)")
    center_y: float = Field(..., description="Arc center Y coordinate (mm)")
    radius: float = Field(..., gt=0, description="Arc centerline radius (mm)")
    start_angle_deg: float = Field(..., description="Start angle in degrees")
    end_angle_deg: float = Field(..., description="End angle in degrees")
    slot_width: float = Field(..., gt=0, description="Target slot width (mm)")
    target_depth_z: float = Field(..., description="Target slot depth Z")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Endmill cutting diameter in mm")
    stepdown_z: float = Field(default=1.0, gt=0, description="Z depth per pass")
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
    cutting_strategy: Literal["conventional", "trochoidal"] = Field(
        default="conventional", description="Slotting strategy ('conventional' or 'trochoidal')"
    )
    trochoidal_stepover_pct: float = Field(
        default=15.0, ge=5.0, le=40.0, description="Trochoidal forward stepover (% of tool diameter)"
    )
