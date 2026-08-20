"""
Pydantic Validation Schemas for SVG 2D Vector CAD Importer with Grayscale Shading.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SVGParsePayloadSchema(BaseModel):
    svg_text: str = Field(..., min_length=10, description="Raw SVG XML file content")
    default_dpi: float = Field(default=96.0, gt=0, description="Default screen DPI (typically 96 DPI)")
    flip_y: bool = Field(default=True, description="Flip Y coordinates from screen down to Cartesian up")
    max_cut_depth: float = Field(default=-6.0, description="100% Black maximum cut depth (mm)")
    invert_shading: bool = Field(default=False, description="Invert grayscale shading (White=100% depth instead of Black)")
    shading_mode: str = Field(default="fill", description="'fill' or 'stroke' color evaluation")
    target_width: Optional[float] = Field(default=None, gt=0, description="Manual target width in mm")
    target_height: Optional[float] = Field(default=None, gt=0, description="Manual target height in mm")


class SVGToGCodePayloadSchema(BaseModel):
    chains: List[Dict[str, Any]] = Field(default_factory=list, description="List of ordered geometry chains")
    circles: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of extracted circle centers")
    operation_type: str = Field(default="auto", description="'contour', 'drill', or 'auto'")
    side: str = Field(default="left", description="'left', 'right', or 'center'")
    target_depth_z: Optional[float] = Field(default=None, description="Global depth override in mm if specified")
    stepdown_z: float = Field(default=1.5, gt=0, description="Stepdown depth per pass (mm)")
    finish_allowance: float = Field(default=0.0, ge=0, description="Wall finish allowance (mm)")
    spring_pass: bool = Field(default=False, description="Spring pass clean wall taper")
    lead_in_type: str = Field(default="tangential_arc", description="'tangential_arc', 'linear_45', or 'direct'")
    use_grayscale_depths: bool = Field(default=True, description="Respect calculated grayscale depth per path")

    tool_id: Optional[int] = Field(default=None, description="Tool ID from library")
    tool_diameter: float = Field(default=3.175, gt=0, description="Tool diameter in mm")
    tool_number: int = Field(default=1, ge=1, description="Tool number")
    tool_name: str = Field(default="Endmill", description="Tool name")
    feed_rate_xy: float = Field(default=800.0, gt=0, description="Cutting feed rate (mm/min)")
    plunge_feed: float = Field(default=250.0, gt=0, description="Plunge feed rate (mm/min)")
    spindle_speed: int = Field(default=16000, gt=0, description="Spindle RPM")
    safe_z_retract: float = Field(default=5.0, description="Safe retract clearance Z (mm)")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    dialect: str = Field(default="grbl", description="'grbl' or 'standard'")
