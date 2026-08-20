from typing import List, Tuple, Optional
from pydantic import BaseModel, Field, model_validator
from ..generators.thread_milling import THREAD_STANDARDS

class HelicalThreadMillingPayloadSchema(BaseModel):
    holes: Optional[List[Tuple[float, float]]] = None
    x: Optional[float] = None
    y: Optional[float] = None
    thread_standard: Optional[str] = Field(default=None, description="Standard thread name e.g. 'M6x1.0' or '1/4-20 UNC'")
    nominal_diameter: Optional[float] = Field(default=None, gt=0, description="Nominal outer diameter in mm")
    pitch: Optional[float] = Field(default=None, gt=0, description="Thread pitch in mm")
    thread_length: float = Field(..., gt=0, description="Total axial length of threaded section")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Thread mill cutting diameter in mm")
    thread_type: str = Field(default="internal", description="'internal' (tapped hole) or 'external' (stud/boss)")
    thread_hand: str = Field(default="right_hand", description="'right_hand' or 'left_hand'")
    milling_direction: str = Field(default="bottom_to_top", description="'bottom_to_top' (climb) or 'top_to_bottom'")
    radial_passes: int = Field(default=1, ge=1, le=10, description="Number of radial depth passes")
    spring_passes: int = Field(default=0, ge=0, le=5, description="Number of final spring passes")
    start_z: float = Field(default=0.0, description="Top surface of workpiece")
    retract_z: Optional[float] = Field(default=None, description="Safe retract clearance Z")
    feed_rate_xy: Optional[float] = Field(default=None, gt=0, description="Helical cutting feed rate (mm/min)")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Plunge feed rate (mm/min)")
    rapid_feed: Optional[float] = Field(default=None, gt=0, description="Rapid traverse feed rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    spindle_dwell_seconds: Optional[float] = Field(default=None, ge=0, description="Spindle spin-up delay")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    tool_id: Optional[int] = Field(default=None, description="Database Tool ID")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID")
    machine_profile_id: Optional[int] = Field(default=None, description="Machine profile ID")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router dial 1-6")
    park_x: Optional[float] = 0.0
    park_y: Optional[float] = 0.0
    park_z: Optional[float] = None

    @model_validator(mode="after")
    def validate_and_resolve(self):
        # 1. Hole coordinates
        if not self.holes and (self.x is None or self.y is None):
            raise ValueError("Must provide either a list of 'holes' or both 'x' and 'y' coordinates.")
        if not self.holes and self.x is not None and self.y is not None:
            self.holes = [(self.x, self.y)]

        # 2. Resolve Thread Standards
        if self.thread_standard:
            std = THREAD_STANDARDS.get(self.thread_standard)
            if std:
                if self.nominal_diameter is None:
                    self.nominal_diameter = std["nominal_dia"]
                if self.pitch is None:
                    self.pitch = std["pitch"]
            else:
                if self.nominal_diameter is None or self.pitch is None:
                    raise ValueError(f"Unknown thread standard '{self.thread_standard}'. Please specify nominal_diameter and pitch explicitly.")

        if self.nominal_diameter is None or self.pitch is None:
            raise ValueError("Must provide nominal_diameter and pitch, or select a valid thread_standard.")

        return self
