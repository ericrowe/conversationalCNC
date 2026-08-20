from typing import Optional
from pydantic import BaseModel, Field

class MaterialPresetCreateSchema(BaseModel):
    material_name: str = Field(..., min_length=1, max_length=100)
    spindle_speed: int = Field(..., gt=0)
    feed_rate_xy: float = Field(..., gt=0)
    plunge_rate_z: float = Field(..., gt=0)
    pass_depth: float = Field(..., gt=0)
    notes: Optional[str] = None

class MaterialPresetUpdateSchema(BaseModel):
    material_name: Optional[str] = Field(None, min_length=1, max_length=100)
    spindle_speed: Optional[int] = Field(None, gt=0)
    feed_rate_xy: Optional[float] = Field(None, gt=0)
    plunge_rate_z: Optional[float] = Field(None, gt=0)
    pass_depth: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None

class ToolCreateSchema(BaseModel):
    tool_number: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=100)
    tool_type: str = Field(default="endmill")
    diameter: float = Field(..., gt=0)
    flute_length: Optional[float] = Field(None, gt=0)
    overall_length: Optional[float] = Field(None, gt=0)
    flute_count: int = Field(default=2, ge=1)
    notes: Optional[str] = None

class ToolUpdateSchema(BaseModel):
    tool_number: Optional[int] = Field(None, ge=1)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    tool_type: Optional[str] = None
    diameter: Optional[float] = Field(None, gt=0)
    flute_length: Optional[float] = Field(None, gt=0)
    overall_length: Optional[float] = Field(None, gt=0)
    flute_count: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None
