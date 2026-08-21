"""
Pydantic Schemas for Workpiece Surface Mesh Leveling & Auto-Warping API.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MeshPointSchema(BaseModel):
    id: Optional[int] = 0
    x: float
    y: float
    z: float = 0.0
    active: bool = True
    row: Optional[int] = None
    col: Optional[int] = None
    ring: Optional[int] = None
    dist: Optional[float] = None


class MeshCandidatePointsRequestSchema(BaseModel):
    shape_type: str = Field(default="rectangle", description="rectangle, circle, donut, or polygon")
    x_min: float = 0.0
    y_min: float = 0.0
    x_max: float = 100.0
    y_max: float = 100.0
    grid_x: int = Field(default=5, ge=2, le=20)
    grid_y: int = Field(default=5, ge=2, le=20)
    center_x: float = 0.0
    center_y: float = 0.0
    radius: float = Field(default=50.0, gt=0)
    inner_radius: float = Field(default=0.0, ge=0)
    grid_resolution: int = Field(default=5, ge=2, le=20)
    margin: float = Field(default=2.0, ge=0)
    pattern_type: str = Field(default="grid", description="grid or polar")
    vertices: Optional[List[List[float]]] = None


class MeshProbeMacroRequestSchema(BaseModel):
    points: List[MeshPointSchema]
    shape_type: str = "rectangle"
    search_dist: float = Field(default=20.0, gt=0)
    fast_feed: float = Field(default=150.0, gt=0)
    slow_feed: float = Field(default=25.0, gt=0)
    safe_traverse_z: float = Field(default=5.0, gt=0)
    plate_thickness: float = Field(default=0.0, ge=0)
    units: str = "mm"
    dialect: str = "grbl"


class MeshParseLogRequestSchema(BaseModel):
    log_text: str
    points_template: Optional[List[MeshPointSchema]] = None
    plate_thickness: float = Field(default=0.0, ge=0)


class MeshWarpGCodeRequestSchema(BaseModel):
    gcode_text: str
    points: List[MeshPointSchema]
    shape_type: str = "rectangle"
    max_segment_length: float = Field(default=3.0, gt=0.1, le=20.0)
    fade_height: Optional[float] = None
