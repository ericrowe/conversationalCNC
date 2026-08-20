from typing import Optional
from pydantic import BaseModel, Field

class MachineProfileCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = False
    controller_dialect: str = "grbl"
    spindle_type: str = "router"  # "router" or "vfd_spindle"
    router_model: Optional[str] = "dewalt_611"  # "dewalt_611", "makita_rt0701", "generic"
    work_area_x: float = Field(default=750.0, gt=0)
    work_area_y: float = Field(default=750.0, gt=0)
    work_area_z: float = Field(default=65.0, gt=0)
    max_feed_xy: float = Field(default=8000.0, gt=0)
    max_feed_z: float = Field(default=500.0, gt=0)
    rapid_feed_rate: float = Field(default=5000.0, gt=0)
    min_spindle_rpm: int = Field(default=16000, gt=0)
    max_spindle_rpm: int = Field(default=27000, gt=0)
    spindle_dwell_seconds: float = Field(default=2.0, ge=0)
    z_probe_thickness: float = Field(default=14.85, ge=0)
    safe_z_retract: float = Field(default=5.0, gt=0)
    notes: Optional[str] = None

class MachineProfileUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    controller_dialect: Optional[str] = None
    spindle_type: Optional[str] = None
    router_model: Optional[str] = None
    work_area_x: Optional[float] = Field(None, gt=0)
    work_area_y: Optional[float] = Field(None, gt=0)
    work_area_z: Optional[float] = Field(None, gt=0)
    max_feed_xy: Optional[float] = Field(None, gt=0)
    max_feed_z: Optional[float] = Field(None, gt=0)
    rapid_feed_rate: Optional[float] = Field(None, gt=0)
    min_spindle_rpm: Optional[int] = Field(None, gt=0)
    max_spindle_rpm: Optional[int] = Field(None, gt=0)
    spindle_dwell_seconds: Optional[float] = Field(None, ge=0)
    z_probe_thickness: Optional[float] = Field(None, ge=0)
    safe_z_retract: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None
