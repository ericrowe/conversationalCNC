from pydantic import BaseModel, Field
from typing import List, Optional

class JogStepRequestSchema(BaseModel):
    axis: str = Field(..., description="Axis to jog ('X', 'Y', 'Z', 'XY', etc.)")
    distance: float = Field(..., description="Incremental distance to move (mm or inches)")
    feed_rate: float = Field(default=1000.0, gt=0, description="Jog feed rate (mm/min)")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    dialect: str = Field(default="grbl", description="Controller dialect ('grbl', 'standard', etc.)")

class JogZeroRequestSchema(BaseModel):
    axes: List[str] = Field(default=["X", "Y", "Z"], description="Axes to zero ('X', 'Y', 'Z')")
    wcs_slot: int = Field(default=1, ge=1, le=6, description="WCS Slot (1=G54)")

class JogGotoOriginRequestSchema(BaseModel):
    safe_z_retract: float = Field(default=5.0, gt=0, description="Safe Z retract clearance before XY move")
    units: str = Field(default="mm", description="'mm' or 'inch'")

class JogSpindleRequestSchema(BaseModel):
    rpm: int = Field(default=16000, ge=0, description="Spindle RPM")
    state: bool = Field(default=True, description="True for ON, False for OFF")
    clockwise: bool = Field(default=True, description="True for CW (M3), False for CCW (M4)")
