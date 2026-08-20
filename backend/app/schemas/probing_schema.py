from pydantic import BaseModel, Field
from typing import Optional

class ZProbeRequestSchema(BaseModel):
    plate_thickness: float = Field(default=14.85, ge=0, description="Touch plate thickness (mm)")
    search_dist: float = Field(default=30.0, gt=0, description="Max downward search travel (mm)")
    fast_feed: float = Field(default=150.0, gt=0, description="Fast initial probing feed rate (mm/min)")
    slow_feed: float = Field(default=25.0, gt=0, description="Slow fine precision touch feed rate (mm/min)")
    retract_height: float = Field(default=20.0, gt=0, description="Post-probe safe Z retract (mm)")
    wcs_slot: int = Field(default=1, ge=1, le=6, description="WCS Slot (1=G54, 2=G55, etc.)")
    units: str = Field(default="mm", description="'mm' or 'inch'")

class CornerXYZProbeRequestSchema(BaseModel):
    tool_diameter: float = Field(default=6.35, gt=0, description="Tool diameter (mm)")
    plate_thickness: float = Field(default=14.85, ge=0, description="Touch block top thickness (mm)")
    block_x_lip: float = Field(default=10.0, ge=0, description="Touch block X lip thickness (mm)")
    block_y_lip: float = Field(default=10.0, ge=0, description="Touch block Y lip thickness (mm)")
    search_dist: float = Field(default=25.0, gt=0, description="Max probing travel (mm)")
    fast_feed: float = Field(default=150.0, gt=0, description="Fast probing feed rate (mm/min)")
    slow_feed: float = Field(default=25.0, gt=0, description="Slow fine precision feed rate (mm/min)")
    retract_z: float = Field(default=15.0, gt=0, description="Safe Z clearance (mm)")
    wcs_slot: int = Field(default=1, ge=1, le=6, description="WCS Slot (1=G54)")
    units: str = Field(default="mm", description="'mm' or 'inch'")
