from typing import Optional
from pydantic import BaseModel, Field, model_validator

class TextEngravingPayloadSchema(BaseModel):
    text: str = Field(..., min_length=1, description="The text string to engrave")
    layout_mode: str = Field(default="linear", description="'linear' or 'arc'")
    
    # Linear layout properties
    start_x: float = Field(default=0.0, description="Start/Origin X coordinate in mm")
    start_y: float = Field(default=0.0, description="Start/Origin Y coordinate in mm")
    rotation_deg: float = Field(default=0.0, description="Rotation angle in degrees")
    align: str = Field(default="left", description="'left', 'center', or 'right'")
    line_spacing_mult: float = Field(default=1.4, gt=0, description="Line spacing multiplier")

    # Arc / Circular layout properties
    center_x: float = Field(default=0.0, description="Arc Center X coordinate in mm")
    center_y: float = Field(default=0.0, description="Arc Center Y coordinate in mm")
    arc_radius: float = Field(default=30.0, gt=0, description="Arc Radius in mm")
    start_angle_deg: float = Field(default=90.0, description="Starting or center angle on circle in degrees")
    arc_direction: str = Field(default="clockwise", description="'clockwise' or 'counter_clockwise'")

    # Font sizing & spacing
    font_size: float = Field(default=10.0, gt=0, description="Cap height in mm")
    letter_spacing: float = Field(default=1.0, ge=0, description="Extra spacing between characters in mm")
    font_name: str = Field(default="simplex_sans", description="Font name e.g. 'simplex_sans', 'duplex_sans', 'roman_serif', 'cursive_script', 'block_stencil'")
    curve_subdivisions: int = Field(default=4, ge=1, le=16, description="Curve interpolation smoothing steps per segment (1-16)")


    # Depths & stepdowns
    target_depth_z: float = Field(default=-0.5, description="Target engraving depth Z (mm)")
    stepdown_z: float = Field(default=0.5, gt=0, description="Maximum depth per pass (mm)")
    start_z: float = Field(default=0.0, description="Top surface of workpiece (mm)")
    retract_z: Optional[float] = Field(default=None, description="Safe retract clearance Z")

    # Feeds & Speeds
    feed_rate_xy: Optional[float] = Field(default=None, gt=0, description="Engraving feed rate (mm/min)")
    plunge_feed: Optional[float] = Field(default=None, gt=0, description="Plunge feed rate (mm/min)")
    rapid_feed: Optional[float] = Field(default=None, gt=0, description="Rapid traverse feed rate (mm/min)")
    spindle_speed: Optional[int] = Field(default=None, gt=0, description="Spindle RPM")
    spindle_dwell_seconds: Optional[float] = Field(default=None, ge=0, description="Spindle spin-up delay")
    units: str = Field(default="mm", description="'mm' or 'inch'")

    # Tooling & Machine resolution
    tool_id: Optional[int] = Field(default=None, description="Tool ID from library")
    tool_diameter: Optional[float] = Field(default=None, gt=0, description="Tool tip / cutter diameter in mm")
    material_preset_id: Optional[int] = Field(default=None, description="Material preset ID")
    machine_profile_id: Optional[int] = Field(default=None, description="Machine profile ID")
    spindle_type: Optional[str] = Field(default=None, description="'router' or 'vfd_spindle'")
    router_model: Optional[str] = Field(default=None, description="'dewalt_611', etc.")
    router_dial: Optional[int] = Field(default=None, ge=1, le=6, description="Router dial 1-6")
    park_x: Optional[float] = 0.0
    park_y: Optional[float] = 0.0
    park_z: Optional[float] = None

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.text.strip():
            raise ValueError("Engraving text cannot be empty or pure whitespace.")
        return self
