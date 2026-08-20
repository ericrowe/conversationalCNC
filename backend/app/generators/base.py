from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class BoundingBox:
    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0
    min_z: float = 0.0
    max_z: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": round(self.min_x, 3),
            "max_x": round(self.max_x, 3),
            "min_y": round(self.min_y, 3),
            "max_y": round(self.max_y, 3),
            "min_z": round(self.min_z, 3),
            "max_z": round(self.max_z, 3),
        }

@dataclass
class WorkEnvelope:
    work_area_x: float
    work_area_y: float
    work_area_z: float

    def validate_bounds(self, bounds: BoundingBox) -> List[str]:
        """
        Validates if toolpath bounding box is within machine work envelope.
        Assumes standard workpiece coordinate setup with work area 0..max.
        """
        violations = []
        if bounds.min_x < 0:
            violations.append(f"X coordinate {bounds.min_x:.2f} is below minimum 0.00")
        if bounds.max_x > self.work_area_x:
            violations.append(
                f"X coordinate {bounds.max_x:.2f} exceeds work envelope max {self.work_area_x:.2f}"
            )
        if bounds.min_y < 0:
            violations.append(f"Y coordinate {bounds.min_y:.2f} is below minimum 0.00")
        if bounds.max_y > self.work_area_y:
            violations.append(
                f"Y coordinate {bounds.max_y:.2f} exceeds work envelope max {self.work_area_y:.2f}"
            )
        return violations

@dataclass
class GCodeProgram:
    gcode: str
    lines: List[str]
    line_count: int
    bounds: BoundingBox
    estimated_time_seconds: float
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gcode": self.gcode,
            "lines": self.lines,
            "line_count": self.line_count,
            "bounds": self.bounds.to_dict(),
            "estimated_time_seconds": round(self.estimated_time_seconds, 2),
            "warnings": self.warnings,
        }
