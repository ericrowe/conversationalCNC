from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class JobOperationItemSchema(BaseModel):
    op_name: str = Field(default="Operation", description="Human readable operation name")
    op_type: str = Field(default="drilling", description="Operation type ('drilling', 'circular_pocket', 'surfacing', etc.)")
    tool_number: int = Field(default=1, ge=1, description="Tool number")
    tool_name: Optional[str] = Field(default="Standard Tool", description="Tool name")
    tool_diameter: float = Field(default=3.175, gt=0, description="Tool diameter (mm)")
    spindle_speed: int = Field(default=16000, gt=0, description="Spindle speed (RPM)")
    feed_rate_xy: Optional[float] = Field(default=800.0, description="Cutting feed rate XY (mm/min)")
    plunge_feed: Optional[float] = Field(default=200.0, description="Plunge feed rate Z (mm/min)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation specific parameter dictionary")
    raw_gcode: Optional[str] = Field(default=None, description="Pre-generated G-code block if available")


class JobSequenceRequestSchema(BaseModel):
    job_name: str = Field(default="Conversational Part Job", description="Overall job program name")
    operations: List[JobOperationItemSchema] = Field(default_factory=list, description="Ordered list of operations")
    safe_z_retract: float = Field(default=5.0, gt=0, description="Safe retract clearance between operations")
    units: str = Field(default="mm", description="'mm' or 'inch'")
    dialect: str = Field(default="grbl", description="'grbl', 'smoothieware', 'standard', etc.")
    optimize_tool_order: bool = Field(default=False, description="Whether to group operations by tool to minimize tool changes")
    park_x: Optional[float] = Field(default=0.0, description="End of job parking position X")
    park_y: Optional[float] = Field(default=0.0, description="End of job parking position Y")
    park_z: Optional[float] = Field(default=5.0, description="End of job parking position Z")
    apply_mesh_leveling: bool = Field(default=False, description="Whether to warp all queued toolpaths against active surface mesh")
    mesh_data: Optional[Dict[str, Any]] = Field(default=None, description="Active WorkpieceMeshMap serialized dictionary")
    mesh_max_segment_length: float = Field(default=3.0, gt=0.1, le=20.0, description="Max linear move segmentation length for mesh following (mm)")
