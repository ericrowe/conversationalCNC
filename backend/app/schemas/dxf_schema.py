"""
Pydantic Validation Schemas for DXF 2D Vector CAD Importer.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DXFParsePayloadSchema(BaseModel):
    dxf_text: str = Field(..., min_length=10, description="Raw ASCII DXF file content")


class DXFToGCodePayloadSchema(BaseModel):
    chains: List[Dict[str, Any]] = Field(default_factory=list, description="List of ordered geometry chains")
    circles: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of extracted circle centers")
    operation_type: str = Field(default="contour", description="'contour', 'pocket', or 'drill'")
    side: str = Field(default="left", description="'left', 'right', or 'center'")
    target_depth_z: float = Field(default=-5.0, description="Target depth Z (mm)")
    stepdown_z: float = Field(default=1.5, gt=0, description="Stepdown depth per pass (mm)")
    finish_allowance: float = Field(default=0.2, ge=0, description="Wall finish allowance (mm)")
    spring_pass: bool = Field(default=True, description="Spring pass clean wall taper")

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
