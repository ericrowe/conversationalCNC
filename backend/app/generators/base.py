import inspect
import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..postprocessors import get_postprocessor, BasePostProcessor

_PAREN_COMMENT_RE = re.compile(r"\([^)]*\)")
_WORD_RE = re.compile(
    r"([A-Za-z])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
    re.IGNORECASE,
)

VALID_UNITS_MAP = {
    "mm": "mm",
    "metric": "mm",
    "inch": "inch",
    "in": "inch",
    "imperial": "inch",
}


def normalize_units(units: str = "mm") -> str:
    """Validates and normalizes unit strings ('mm' or 'inch'). Fails closed on invalid units."""
    if not isinstance(units, str) or not units.strip():
        raise ValueError(f"Invalid units '{units}'. Supported units: mm, inch.")
    norm = units.lower().strip()
    if norm not in VALID_UNITS_MAP:
        raise ValueError(
            f"Unsupported unit system '{units}'. Supported units: mm, metric, inch, imperial."
        )
    return VALID_UNITS_MAP[norm]


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


def compute_gcode_bounds(gcode_text: str, initial_z: float = 0.0) -> BoundingBox:
    """
    Computes the full 3D bounding box over all rapid (G0), linear (G1), and circular arc (G2/G3)
    trajectories in a G-code program, including approach/retract moves, park moves, and arc extrema.
    """
    curr_x, curr_y, curr_z = 0.0, 0.0, initial_z
    z_seen = False
    xy_seen = False
    distance_mode = "G90"
    motion_mode: Optional[str] = None

    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")
    min_z, max_z = float("inf"), float("-inf")

    for raw_line in gcode_text.splitlines():
        code_part = _strip_comments(raw_line)
        if not code_part:
            continue
        words = _WORD_RE.findall(code_part)
        if not words:
            continue

        line_motion: Optional[str] = None
        line_words: Dict[str, float] = {}
        for letter_raw, val_str in words:
            letter = letter_raw.upper()
            val = float(val_str)
            if letter == "G":
                g_int = int(round(val))
                if g_int == 90:
                    distance_mode = "G90"
                elif g_int == 91:
                    distance_mode = "G91"
                elif g_int in (0, 1, 2, 3):
                    line_motion = f"G{g_int}"
                    motion_mode = line_motion
            else:
                line_words[letter] = val

        has_xyz = any(k in line_words for k in ("X", "Y", "Z", "I", "J"))
        active_motion = line_motion or (motion_mode if has_xyz else None)
        if active_motion in ("G0", "G1", "G2", "G3") and has_xyz:
            sx, sy, sz = curr_x, curr_y, curr_z
            if distance_mode == "G90":
                ex = line_words.get("X", curr_x)
                ey = line_words.get("Y", curr_y)
                ez = line_words.get("Z", curr_z)
            else:
                ex = curr_x + line_words.get("X", 0.0)
                ey = curr_y + line_words.get("Y", 0.0)
                ez = curr_z + line_words.get("Z", 0.0)

            if "X" in line_words or "Y" in line_words:
                if xy_seen:
                    min_x, max_x = min(min_x, sx), max(max_x, sx)
                    min_y, max_y = min(min_y, sy), max(max_y, sy)
                min_x, max_x = min(min_x, ex), max(max_x, ex)
                min_y, max_y = min(min_y, ey), max(max_y, ey)
                xy_seen = True

            if "Z" in line_words:
                if z_seen:
                    min_z, max_z = min(min_z, sz), max(max_z, sz)
                min_z, max_z = min(min_z, ez), max(max_z, ez)
                z_seen = True

            if active_motion in ("G2", "G3") and ("I" in line_words or "J" in line_words):
                cx = sx + line_words.get("I", 0.0)
                cy = sy + line_words.get("J", 0.0)
                r = math.hypot(sx - cx, sy - cy)
                a0 = math.atan2(sy - cy, sx - cx)
                a1 = math.atan2(ey - cy, ex - cx)
                sweep = (a0 - a1) % (2.0 * math.pi) if active_motion == "G2" else (a1 - a0) % (2.0 * math.pi)
                if sweep < 1e-6:
                    sweep = 2.0 * math.pi
                for card in (0.0, math.pi / 2.0, math.pi, -math.pi / 2.0):
                    rel = (a0 - card) % (2.0 * math.pi) if active_motion == "G2" else (card - a0) % (2.0 * math.pi)
                    if rel <= sweep + 1e-6:
                        px = cx + r * math.cos(card)
                        py = cy + r * math.sin(card)
                        min_x, max_x = min(min_x, px), max(max_x, px)
                        min_y, max_y = min(min_y, py), max(max_y, py)

            curr_x, curr_y, curr_z = ex, ey, ez

    return BoundingBox(
        min_x=0.0 if min_x == float("inf") else min_x,
        max_x=0.0 if max_x == float("-inf") else max_x,
        min_y=0.0 if min_y == float("inf") else min_y,
        max_y=0.0 if max_y == float("-inf") else max_y,
        min_z=0.0 if min_z == float("inf") else min_z,
        max_z=0.0 if max_z == float("-inf") else max_z,
    )


@dataclass
class WorkEnvelope:
    work_area_x: float
    work_area_y: float
    work_area_z: float
    wcs_origin_x: Optional[float] = None
    wcs_origin_y: Optional[float] = None
    wcs_origin_z: Optional[float] = None
    machine_min_x: float = 0.0
    machine_max_x: Optional[float] = None
    machine_min_y: float = 0.0
    machine_max_y: Optional[float] = None
    machine_min_z: Optional[float] = None
    machine_max_z: Optional[float] = None
    tool_length_offset: float = 0.0
    strict_mode: bool = False

    def validate_bounds(self, bounds: BoundingBox) -> List[str]:
        """
        Validates toolpath bounding box against work envelope and (when WCS origin is known)
        absolute machine coordinates (including asymmetric Z limits and tool_length_offset).
        """
        violations: List[str] = []

        eff_max_x = self.machine_max_x if self.machine_max_x is not None else self.work_area_x
        eff_max_y = self.machine_max_y if self.machine_max_y is not None else self.work_area_y
        eff_min_z = self.machine_min_z if self.machine_min_z is not None else -self.work_area_z
        eff_max_z = self.machine_max_z if self.machine_max_z is not None else self.work_area_z

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
            if mach_min_x < self.machine_min_x:
                violations.append(
                    f"Machine X coordinate {mach_min_x:.2f} is below minimum {self.machine_min_x:.2f}"
                )
            if mach_max_x > eff_max_x:
                violations.append(
                    f"Machine X coordinate {mach_max_x:.2f} exceeds work envelope max {eff_max_x:.2f}"
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
            if mach_min_y < self.machine_min_y:
                violations.append(
                    f"Machine Y coordinate {mach_min_y:.2f} is below minimum {self.machine_min_y:.2f}"
                )
            if mach_max_y > eff_max_y:
                violations.append(
                    f"Machine Y coordinate {mach_max_y:.2f} exceeds work envelope max {eff_max_y:.2f}"
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

        if self.wcs_origin_z is not None:
            mach_min_z = self.wcs_origin_z + bounds.min_z + self.tool_length_offset
            mach_max_z = self.wcs_origin_z + bounds.max_z + self.tool_length_offset
            if mach_min_z < eff_min_z:
                violations.append(
                    f"Machine Z coordinate {mach_min_z:.2f} (with tool_length_offset={self.tool_length_offset:.2f}) "
                    f"is below machine_min_z {eff_min_z:.2f}"
                )
            if mach_max_z > eff_max_z:
                violations.append(
                    f"Machine Z coordinate {mach_max_z:.2f} (with tool_length_offset={self.tool_length_offset:.2f}) "
                    f"exceeds machine_max_z {eff_max_z:.2f}"
                )

        return violations

    def evaluate_envelope(self, bounds: BoundingBox) -> Dict[str, Any]:
        """
        Tri-state envelope evaluation contract (R2-003):
        - 'VERIFIED': All axes have known work-to-machine offsets (wcs_origin_x/y/z) and 0 violations.
        - 'PARTIAL_UNKNOWN': Relative spans pass, but machine WCS offsets are incomplete/unknown
                             (unless strict_mode=True, which promotes missing offsets to 'FAILED').
        - 'FAILED': Any span or machine-limit violation occurred (or strict_mode=True with missing offsets).
        """
        violations = self.validate_bounds(bounds)
        has_xy_wcs = self.wcs_origin_x is not None and self.wcs_origin_y is not None
        has_full_wcs = has_xy_wcs and (
            self.wcs_origin_z is not None
            or (self.machine_min_z is None and self.machine_max_z is None and self.tool_length_offset == 0.0)
        )

        if violations:
            status = "FAILED"
        elif has_full_wcs and self.wcs_origin_z is not None:
            status = "VERIFIED"
        elif self.strict_mode:
            status = "FAILED"
            violations.append(
                "Strict envelope mode requires known wcs_origin_x, wcs_origin_y, and wcs_origin_z offsets."
            )
        else:
            status = "PARTIAL_UNKNOWN"

        return {
            "status": status,
            "valid": status != "FAILED",
            "violations": violations,
            "requires_operator_acknowledgment": status == "PARTIAL_UNKNOWN",
            "machine_limits_status": "verified" if has_xy_wcs and status != "FAILED" else "unavailable",
        }


@dataclass
class MachiningContext:
    """
    Explicit, validated shared machining context propagated across standalone and sequenced
    conversational generators (R2-002).
    """

    machine_id: str = "default_grbl"
    units: str = "mm"
    dialect: str = "grbl"
    spindle_type: str = "router"
    router_model: Optional[str] = "dewalt_611"
    router_dial: Optional[float] = None
    require_pause: bool = False
    safe_z_retract: float = 5.0
    start_z: float = 0.0
    feed_rate_xy: float = 800.0
    plunge_feed: float = 250.0
    spindle_speed: int = 16000
    tool_number: int = 1
    tool_name: str = "Endmill"
    tool_diameter: float = 3.175
    tool_length_offset: float = 0.0
    work_envelope: Optional[WorkEnvelope] = None
    postprocessor: Optional[BasePostProcessor] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.units = normalize_units(self.units)
        if self.postprocessor is None:
            self.postprocessor = get_postprocessor(self.dialect)
        self.dialect = (self.dialect or "grbl").lower().strip()
        if self.tool_diameter <= 0:
            raise ValueError(f"tool_diameter ({self.tool_diameter}) must be greater than zero.")
        if self.safe_z_retract <= self.start_z:
            raise ValueError(
                f"safe_z_retract ({self.safe_z_retract}) must be strictly above start_z ({self.start_z})."
            )
        if self.feed_rate_xy <= 0 or self.plunge_feed <= 0:
            raise ValueError("Feed rates must be strictly positive.")
        if self.spindle_speed <= 0:
            raise ValueError("spindle_speed must be strictly positive.")

    def apply_to_params(self, raw_params: Dict[str, Any], target_func: Any) -> Dict[str, Any]:
        """
        Merges this MachiningContext with operation parameters and maps canonical context
        keys onto the target generator function's accepted signature without silent drops.
        """
        merged = dict(raw_params)
        merged.setdefault("units", self.units)
        merged["units"] = normalize_units(merged["units"])
        merged.setdefault("dialect", self.dialect)
        merged.setdefault("postprocessor", self.postprocessor)
        merged.setdefault("spindle_type", self.spindle_type)
        merged.setdefault("router_model", self.router_model)
        if self.router_dial is not None:
            merged.setdefault("router_dial", self.router_dial)
        merged.setdefault("require_pause", self.require_pause)
        merged.setdefault("tool_number", self.tool_number)
        merged.setdefault("tool_name", self.tool_name)
        merged.setdefault("tool_diameter", self.tool_diameter)
        merged.setdefault("spindle_speed", self.spindle_speed)
        if self.work_envelope is not None:
            merged.setdefault("work_envelope", self.work_envelope)

        # Canonical clearance Z propagation across all naming conventions
        clearance_val = float(
            merged.get("retract_z", merged.get("clearance_z", merged.get("safe_z_retract", self.safe_z_retract)))
        )
        merged.setdefault("safe_z_retract", clearance_val)
        merged.setdefault("retract_z", clearance_val)
        merged.setdefault("clearance_z", clearance_val)

        # Canonical feed propagation when explicitly present in context or params
        if "feed_rate" in merged and "feed_rate_xy" not in merged:
            merged["feed_rate_xy"] = float(merged["feed_rate"])
        if "plunge_rate" in merged and "plunge_feed" not in merged:
            merged["plunge_feed"] = float(merged["plunge_rate"])

        sig = inspect.signature(target_func)
        accepted_keys = set(sig.parameters.keys())
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if has_var_kw:
            return merged
        return {k: v for k, v in merged.items() if k in accepted_keys}


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
    Strips dialect header (G21 G90 G94...), sub-operation tool changes (T.. M6),
    and footer (M5, G0 park, M2/M02/M30) from a standalone operation snippet so it
    can be cleanly stitched or arrayed by the top-level sequencer.
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
        tokens = code_only.split()
        # Strip any M2 / M02 / M30 program end command or sub-operation M6 tool change
        if any(tok in ("M2", "M02", "M30", "M6", "M06") for tok in tokens):
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
