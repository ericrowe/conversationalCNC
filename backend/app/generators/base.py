import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

_PAREN_COMMENT_RE = re.compile(r"\([^)]*\)")


def _strip_comments(line: str) -> str:
    no_parens = _PAREN_COMMENT_RE.sub("", line)
    if ";" in no_parens:
        no_parens = no_parens.split(";", 1)[0]
    return no_parens.strip()


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
    wcs_origin_x: Optional[float] = None
    wcs_origin_y: Optional[float] = None
    wcs_origin_z: Optional[float] = None

    def validate_bounds(self, bounds: BoundingBox) -> List[str]:
        """
        Validates toolpath bounding box against work envelope and (when WCS origin is known)
        absolute machine coordinates.
        - Local G54 coordinates may legally be negative around a fixture datum (e.g. center origin)
          provided total axis travel span does not exceed the machine envelope.
        - When wcs_origin_x/y/z are supplied, transforms into machine coordinates and enforces
          [0..work_area_x], [0..work_area_y], and [-work_area_z..work_area_z].
        """
        violations: List[str] = []

        span_x = bounds.max_x - bounds.min_x
        span_y = bounds.max_y - bounds.min_y
        span_z = bounds.max_z - bounds.min_z

        if span_x > self.work_area_x:
            violations.append(
                f"X travel span {span_x:.2f} exceeds work envelope max {self.work_area_x:.2f}"
            )
        if span_y > self.work_area_y:
            violations.append(
                f"Y travel span {span_y:.2f} exceeds work envelope max {self.work_area_y:.2f}"
            )
        if span_z > self.work_area_z or abs(bounds.min_z) > self.work_area_z or bounds.max_z > self.work_area_z:
            violations.append(
                f"Z coordinate range [{bounds.min_z:.2f}, {bounds.max_z:.2f}] (span {span_z:.2f}) "
                f"exceeds Z work envelope max {self.work_area_z:.2f}"
            )

        if self.wcs_origin_x is not None:
            mach_min_x = self.wcs_origin_x + bounds.min_x
            mach_max_x = self.wcs_origin_x + bounds.max_x
            if mach_min_x < 0:
                violations.append(
                    f"Machine X coordinate {mach_min_x:.2f} is below minimum 0.00"
                )
            if mach_max_x > self.work_area_x:
                violations.append(
                    f"Machine X coordinate {mach_max_x:.2f} exceeds work envelope max {self.work_area_x:.2f}"
                )
        else:
            if bounds.max_x > self.work_area_x:
                violations.append(
                    f"X coordinate {bounds.max_x:.2f} exceeds work envelope max {self.work_area_x:.2f}"
                )
            if bounds.min_x < -self.work_area_x:
                violations.append(
                    f"X coordinate {bounds.min_x:.2f} exceeds negative work envelope span -{self.work_area_x:.2f}"
                )

        if self.wcs_origin_y is not None:
            mach_min_y = self.wcs_origin_y + bounds.min_y
            mach_max_y = self.wcs_origin_y + bounds.max_y
            if mach_min_y < 0:
                violations.append(
                    f"Machine Y coordinate {mach_min_y:.2f} is below minimum 0.00"
                )
            if mach_max_y > self.work_area_y:
                violations.append(
                    f"Machine Y coordinate {mach_max_y:.2f} exceeds work envelope max {self.work_area_y:.2f}"
                )
        else:
            if bounds.max_y > self.work_area_y:
                violations.append(
                    f"Y coordinate {bounds.max_y:.2f} exceeds work envelope max {self.work_area_y:.2f}"
                )
            if bounds.min_y < -self.work_area_y:
                violations.append(
                    f"Y coordinate {bounds.min_y:.2f} exceeds negative work envelope span -{self.work_area_y:.2f}"
                )

        return violations

    def evaluate_envelope(self, bounds: BoundingBox) -> Dict[str, Any]:
        violations = self.validate_bounds(bounds)
        has_wcs = (
            self.wcs_origin_x is not None
            and self.wcs_origin_y is not None
        )
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "machine_limits_status": "verified" if has_wcs else "unavailable",
        }


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


def strip_header_and_footer(gcode_text: str) -> List[str]:
    """
    Strips dialect header (G21 G90 G94...) and footer (M5, G0 park, M2/M02/M30)
    from a standalone operation snippet so it can be cleanly stitched or arrayed.
    Comments and whitespace on termination or park lines do not defeat stripping.
    """
    lines = [line.strip() for line in gcode_text.splitlines() if line.strip()]
    cleaned: List[str] = []
    for line in lines:
        upper = line.upper()
        code_only = _strip_comments(line).upper()

        if upper.startswith("(GENERATED BY") or upper.startswith("(TARGET:"):
            continue
        if "G21 G90" in code_only or "G20 G90" in code_only or "G21 G91" in code_only or "G20 G91" in code_only:
            continue
        # Strip any M2 / M02 / M30 program end command regardless of inline comments
        tokens = code_only.split()
        if any(tok in ("M2", "M02", "M30") for tok in tokens):
            continue
        # Strip standalone footer park or footer retract lines
        if "(PARK)" in upper or "(RETRACT TO CLEARANCE)" in upper or "(PROGRAM END)" in upper:
            continue
        if "(SPINDLE STOP)" in upper and code_only == "M5":
            continue

        cleaned.append(line)

    while cleaned and _strip_comments(cleaned[-1]).upper() == "M5":
        cleaned.pop()

    return cleaned
