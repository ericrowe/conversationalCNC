"""
Independent G-Code Modal State, GRBL Dialect & 2D Swept-Tool Geometry Verification Oracle
(CNC-013, V2-004, V2-005, V2-006).
Does NOT import or reuse any geometry helper from backend/app/generators.
Independently parses G-code blocks, tracks modal state (G20/G21, G90/G91, G17/G18/G19, G94, F, XYZ, M-codes),
and validates:
- Arc start-to-center vs end-to-center radius equality (|rs - re| <= arc_tol) and rs > 0
- Arc sweep direction validity
- Finite numeric words (no NaN / inf)
- Single final program termination (M2 / M02 / M30) and zero motion after termination
- Safe Z >= expected_clearance_z before XY rapid (G0) positioning moves
- Safe Z >= expected_clearance_z before M5 spindle stop (when require_retract_before_m5=True)
- GRBL dialect command restrictions (no G73/G81/G82/G83 canned cycles or M6 tool changes when dialect='grbl')
- 2D Swept-Disk Stock Interference verification (verify_contour_no_stock_gouge)
"""
import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


PAREN_COMMENT_RE = re.compile(r"\([^)]*\)")
WORD_RE = re.compile(
    r"([A-Za-z])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[+-]?(?:nan|inf))",
    re.IGNORECASE,
)


@dataclass
class ArcRecord:
    line_no: int
    raw_line: str
    motion: str  # "G2" or "G3"
    start_xy: Tuple[float, float]
    end_xy: Tuple[float, float]
    center_xy: Tuple[float, float]
    r_start: float
    r_end: float
    sweep_rad: float
    z: float = 0.0


@dataclass
class GCodeValidationReport:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    arcs: List[ArcRecord] = field(default_factory=list)
    termination_lines: List[int] = field(default_factory=list)
    moves_after_termination: List[int] = field(default_factory=list)
    unsafe_xy_rapids: List[int] = field(default_factory=list)
    unsafe_spindle_stops: List[int] = field(default_factory=list)
    unsupported_dialect_codes: List[str] = field(default_factory=list)
    bounds: Dict[str, float] = field(default_factory=dict)
    modal_state: Dict[str, object] = field(default_factory=dict)


def strip_gcode_comments(line: str) -> str:
    """Strips both (...) inline comments and ; trailing comments."""
    no_parens = PAREN_COMMENT_RE.sub("", line)
    if ";" in no_parens:
        no_parens = no_parens.split(";", 1)[0]
    return no_parens.strip()


def validate_gcode_program(
    gcode_text: str,
    expected_clearance_z: Optional[float] = None,
    arc_tol: float = 0.003,
    dialect: Optional[str] = None,
    require_retract_before_m5: bool = False,
) -> GCodeValidationReport:
    errors: List[str] = []
    warnings: List[str] = []
    arcs: List[ArcRecord] = []
    termination_lines: List[int] = []
    moves_after_termination: List[int] = []
    unsafe_xy_rapids: List[int] = []
    unsafe_spindle_stops: List[int] = []
    unsupported_dialect_codes: List[str] = []

    units: Optional[str] = None
    unit_history: List[str] = []
    distance_mode = "G90"
    distance_history: List[str] = []
    plane = "G17"
    plane_history: List[str] = []
    feed_mode = "G94"
    motion_mode: Optional[str] = None
    feed_rate: float = 0.0

    curr_x: float = 0.0
    curr_y: float = 0.0
    curr_z: float = 0.0
    z_known: bool = False
    has_cut_below_clearance: bool = False
    terminated: bool = False

    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")
    min_z, max_z = float("inf"), float("-inf")

    dialect_norm = dialect.lower().strip() if dialect else None
    is_grbl_family = dialect_norm in ("grbl", "grblhal", "fluidnc", "smoothie", "smoothieware")

    for line_no, raw_line in enumerate(gcode_text.splitlines(), 1):
        stripped_raw = raw_line.strip()
        if not stripped_raw:
            continue

        upper_raw = stripped_raw.upper()
        if "(ERROR GENERATING " in upper_raw or "(UNKNOWN OPERATION TYPE:" in upper_raw:
            errors.append(f"Line {line_no}: Leaked generator failure comment: {stripped_raw}")

        code_part = strip_gcode_comments(stripped_raw)
        if not code_part:
            continue

        if any(bad in code_part.lower() for bad in ("nan", "inf")):
            errors.append(f"Line {line_no}: Non-finite numeric token in '{code_part}'")
            continue

        words = WORD_RE.findall(code_part)
        if not words:
            continue

        line_g_motion: Optional[str] = None
        line_words: Dict[str, float] = {}
        line_m_codes: List[int] = []

        for letter_raw, val_str in words:
            letter = letter_raw.upper()
            try:
                val = float(val_str)
            except ValueError:
                errors.append(f"Line {line_no}: Invalid numeric value '{letter}{val_str}'")
                continue

            if not math.isfinite(val):
                errors.append(f"Line {line_no}: Non-finite value '{letter}{val_str}'")
                continue

            if letter == "G":
                g_int = int(round(val))
                if g_int == 20:
                    if units is not None and units != "inch":
                        errors.append(f"Line {line_no}: Unexpected mid-program unit change from {units} to inch (G20)")
                    units = "inch"
                    unit_history.append("G20")
                elif g_int == 21:
                    if units is not None and units != "mm":
                        errors.append(f"Line {line_no}: Unexpected mid-program unit change from {units} to mm (G21)")
                    units = "mm"
                    unit_history.append("G21")
                elif g_int == 90:
                    distance_mode = "G90"
                    distance_history.append("G90")
                elif g_int == 91:
                    distance_mode = "G91"
                    distance_history.append("G91")
                elif g_int in (17, 18, 19):
                    plane = f"G{g_int}"
                    plane_history.append(plane)
                elif g_int in (0, 1, 2, 3):
                    line_g_motion = f"G{g_int}"
                    motion_mode = line_g_motion
                elif g_int in (73, 81, 82, 83):
                    if is_grbl_family:
                        code_str = f"G{g_int}"
                        unsupported_dialect_codes.append(code_str)
                        errors.append(f"Line {line_no}: Unsupported canned cycle {code_str} for GRBL dialect")
                elif g_int == 94:
                    feed_mode = "G94"
                elif g_int in (4, 10, 28, 38, 53, 54, 55, 56, 57, 58, 59, 80):
                    pass
                else:
                    warnings.append(f"Line {line_no}: Unrecognized G-code G{g_int}")
            elif letter == "M":
                m_int = int(round(val))
                line_m_codes.append(m_int)
                if m_int == 6 and is_grbl_family:
                    unsupported_dialect_codes.append("M6")
                    errors.append(f"Line {line_no}: Unsupported automatic tool change M6 for GRBL dialect")
                if m_int == 5 and require_retract_before_m5 and expected_clearance_z is not None:
                    if has_cut_below_clearance and (not z_known or curr_z < expected_clearance_z - 1e-4):
                        unsafe_spindle_stops.append(line_no)
                        errors.append(
                            f"Line {line_no}: Spindle stop M5 executed at Z={curr_z:.3f} below safe clearance {expected_clearance_z:.3f}"
                        )
                if m_int in (2, 30):
                    termination_lines.append(line_no)
                    terminated = True
            elif letter == "F":
                if val <= 0:
                    errors.append(f"Line {line_no}: Non-positive feed rate F{val}")
                feed_rate = val
            else:
                line_words[letter] = val

        has_xyz_move = any(k in line_words for k in ("X", "Y", "Z", "I", "J", "K"))
        active_motion = line_g_motion or (motion_mode if has_xyz_move else None)

        if terminated and has_xyz_move and line_no not in termination_lines:
            moves_after_termination.append(line_no)
            errors.append(f"Line {line_no}: Motion command after program termination (M2/M30): '{code_part}'")

        if active_motion in ("G0", "G1", "G2", "G3") and has_xyz_move:
            start_x, start_y, start_z_pos = curr_x, curr_y, curr_z
            if distance_mode == "G90":
                end_x = line_words.get("X", curr_x)
                end_y = line_words.get("Y", curr_y)
                end_z = line_words.get("Z", curr_z)
            else:
                end_x = curr_x + line_words.get("X", 0.0)
                end_y = curr_y + line_words.get("Y", 0.0)
                end_z = curr_z + line_words.get("Z", 0.0)

            if "Z" in line_words:
                z_known = True
                if expected_clearance_z is not None and end_z < expected_clearance_z - 1e-4:
                    has_cut_below_clearance = True

            # Check safe Z clearance on non-zero lateral XY rapid moves
            if (
                active_motion == "G0"
                and ("X" in line_words or "Y" in line_words)
                and "Z" not in line_words
                and math.hypot(end_x - start_x, end_y - start_y) > 1e-5
                and expected_clearance_z is not None
            ):
                if not z_known or curr_z < expected_clearance_z - 1e-4:
                    unsafe_xy_rapids.append(line_no)
                    errors.append(
                        f"Line {line_no}: Rapid XY move at Z={curr_z:.3f} below clearance {expected_clearance_z:.3f}"
                    )

            if active_motion in ("G1", "G2", "G3") and feed_rate <= 0:
                errors.append(f"Line {line_no}: Cutting move {active_motion} without active feed rate")

            if active_motion in ("G2", "G3"):
                if plane != "G17":
                    errors.append(f"Line {line_no}: Arc {active_motion} emitted outside G17 plane (active={plane})")
                elif "I" in line_words or "J" in line_words:
                    i_val = line_words.get("I", 0.0)
                    j_val = line_words.get("J", 0.0)
                    cx = start_x + i_val
                    cy = start_y + j_val
                    rs = math.hypot(start_x - cx, start_y - cy)
                    re_dist = math.hypot(end_x - cx, end_y - cy)
                    if rs <= 1e-6 or re_dist <= 1e-6:
                        errors.append(f"Line {line_no}: Degenerate zero-radius arc (rs={rs:.4f}, re={re_dist:.4f})")
                    elif abs(rs - re_dist) > arc_tol:
                        errors.append(
                            f"Line {line_no}: Arc radius mismatch on '{code_part}': "
                            f"r_start={rs:.4f} vs r_end={re_dist:.4f} (diff={abs(rs - re_dist):.4f} > {arc_tol})"
                        )

                    a0 = math.atan2(start_y - cy, start_x - cx)
                    a1 = math.atan2(end_y - cy, end_x - cx)
                    if active_motion == "G2":
                        sweep = (a0 - a1) % (2.0 * math.pi)
                    else:
                        sweep = (a1 - a0) % (2.0 * math.pi)
                    if sweep < 1e-6:
                        sweep = 2.0 * math.pi

                    arcs.append(
                        ArcRecord(
                            line_no=line_no,
                            raw_line=stripped_raw,
                            motion=active_motion,
                            start_xy=(start_x, start_y),
                            end_xy=(end_x, end_y),
                            center_xy=(cx, cy),
                            r_start=rs,
                            r_end=re_dist,
                            sweep_rad=sweep,
                            z=end_z,
                        )
                    )
                    # Include arc extrema in bounding box
                    for cardinal_ang in (0.0, math.pi / 2.0, math.pi, -math.pi / 2.0):
                        if active_motion == "G2":
                            rel = (a0 - cardinal_ang) % (2.0 * math.pi)
                        else:
                            rel = (cardinal_ang - a0) % (2.0 * math.pi)
                        if rel <= sweep + 1e-6:
                            px = cx + rs * math.cos(cardinal_ang)
                            py = cy + rs * math.sin(cardinal_ang)
                            min_x, max_x = min(min_x, px), max(max_x, px)
                            min_y, max_y = min(min_y, py), max(max_y, py)
                elif "R" in line_words:
                    r_val = abs(line_words["R"])
                    chord = math.hypot(end_x - start_x, end_y - start_y)
                    if r_val <= 0 or chord > 2.0 * r_val + arc_tol:
                        errors.append(f"Line {line_no}: Invalid R-format arc (R={r_val:.4f}, chord={chord:.4f})")
                else:
                    errors.append(f"Line {line_no}: {active_motion} missing both I/J and R center words")

            for px, py, pz in ((start_x, start_y, start_z_pos), (end_x, end_y, end_z)):
                min_x, max_x = min(min_x, px), max(max_x, px)
                min_y, max_y = min(min_y, py), max(max_y, py)
                if z_known:
                    min_z, max_z = min(min_z, pz), max(max_z, pz)

            curr_x, curr_y, curr_z = end_x, end_y, end_z

    if len(termination_lines) == 0:
        errors.append("Program missing M2/M02/M30 termination command")
    elif len(termination_lines) > 1:
        errors.append(f"Program has {len(termination_lines)} M2/M30 termination commands at lines {termination_lines}")

    bounds_dict = {
        "min_x": 0.0 if min_x == float("inf") else round(min_x, 4),
        "max_x": 0.0 if max_x == float("-inf") else round(max_x, 4),
        "min_y": 0.0 if min_y == float("inf") else round(min_y, 4),
        "max_y": 0.0 if max_y == float("-inf") else round(max_y, 4),
        "min_z": 0.0 if min_z == float("inf") else round(min_z, 4),
        "max_z": 0.0 if max_z == float("-inf") else round(max_z, 4),
    }

    return GCodeValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        arcs=arcs,
        termination_lines=termination_lines,
        moves_after_termination=moves_after_termination,
        unsafe_xy_rapids=unsafe_xy_rapids,
        unsafe_spindle_stops=unsafe_spindle_stops,
        unsupported_dialect_codes=unsupported_dialect_codes,
        bounds=bounds_dict,
        modal_state={
            "units": units or "mm",
            "unit_history": unit_history,
            "distance_mode": distance_mode,
            "distance_history": distance_history,
            "plane": plane,
            "plane_history": plane_history,
            "feed_mode": feed_mode,
            "feed_rate": feed_rate,
            "final_xyz": (curr_x, curr_y, curr_z),
        },
    )


def verify_contour_no_stock_gouge(
    nominal_segments: List[Dict[str, Any]],
    start_point: Tuple[float, float],
    tool_diameter: float,
    finish_allowance: float,
    gcode_text: str,
    samples_per_segment: int = 80,
    gouge_tol: float = 0.005,
) -> Dict[str, Any]:
    """
    Independent 2D swept-tool verification oracle (V2-005).
    1. Densely samples the nominal workpiece contour segments (lines and arcs).
    2. Parses all cutting moves (G1/G2/G3 at Z < 0, excluding lead-in/lead-out moves) from gcode_text
       and densely samples the tool-center path.
    3. Computes the minimum Euclidean distance from the tool centerpath to the nominal finished contour.
       If min_distance < (tool_diameter / 2 + finish_allowance - gouge_tol), the cutter has gouged
       into protected finished stock!
    """
    required_clearance = (tool_diameter / 2.0) + finish_allowance

    # 1. Sample nominal contour
    nom_pts: List[Tuple[float, float]] = []
    cx, cy = float(start_point[0]), float(start_point[1])
    for seg in nominal_segments:
        stype = (seg.get("type") or "line").lower().strip()
        nx, ny = float(seg["x"]), float(seg["y"])
        if stype == "line":
            for k in range(samples_per_segment + 1):
                t = k / float(samples_per_segment)
                nom_pts.append((cx + t * (nx - cx), cy + t * (ny - cy)))
        elif stype == "arc":
            cw = bool(seg.get("cw", False))
            acx = cx + float(seg.get("i", 0.0))
            acy = cy + float(seg.get("j", 0.0))
            r = math.hypot(cx - acx, cy - acy)
            a0 = math.atan2(cy - acy, cx - acx)
            a1 = math.atan2(ny - acy, nx - acx)
            sweep = (a0 - a1) % (2.0 * math.pi) if cw else (a1 - a0) % (2.0 * math.pi)
            if sweep < 1e-6:
                sweep = 2.0 * math.pi
            for k in range(samples_per_segment + 1):
                t = k / float(samples_per_segment)
                ang = a0 - t * sweep if cw else a0 + t * sweep
                nom_pts.append((acx + r * math.cos(ang), acy + r * math.sin(ang)))
        cx, cy = nx, ny

    # 2. Sample emitted contour cutting moves from G-code
    tool_pts: List[Tuple[float, float]] = []
    tx, ty, tz = 0.0, 0.0, 5.0
    motion = "G0"
    for raw_line in gcode_text.splitlines():
        upper_raw = raw_line.upper()
        is_lead = "LEAD-IN" in upper_raw or "LEAD-OUT" in upper_raw or "LEAD IN" in upper_raw or "LEAD OUT" in upper_raw
        code_part = strip_gcode_comments(raw_line)
        if not code_part:
            continue
        words = {k.upper(): float(v) for k, v in WORD_RE.findall(code_part)}
        for k, v in WORD_RE.findall(code_part):
            if k.upper() == "G" and int(round(float(v))) in (0, 1, 2, 3):
                motion = f"G{int(round(float(v)))}"
        nx = words.get("X", tx)
        ny = words.get("Y", ty)
        nz = words.get("Z", tz)

        if motion in ("G1", "G2", "G3") and nz < -1e-4 and ("X" in words or "Y" in words) and not is_lead:
            if motion == "G1":
                for k in range(samples_per_segment + 1):
                    t = k / float(samples_per_segment)
                    tool_pts.append((tx + t * (nx - tx), ty + t * (ny - ty)))
            else:
                cw = motion == "G2"
                acx = tx + words.get("I", 0.0)
                acy = ty + words.get("J", 0.0)
                r = math.hypot(tx - acx, ty - acy)
                a0 = math.atan2(ty - acy, tx - acx)
                a1 = math.atan2(ny - acy, nx - acx)
                sweep = (a0 - a1) % (2.0 * math.pi) if cw else (a1 - a0) % (2.0 * math.pi)
                if sweep < 1e-6:
                    sweep = 2.0 * math.pi
                for k in range(samples_per_segment + 1):
                    t = k / float(samples_per_segment)
                    ang = a0 - t * sweep if cw else a0 + t * sweep
                    tool_pts.append((acx + r * math.cos(ang), acy + r * math.sin(ang)))

        tx, ty, tz = nx, ny, nz

    if not tool_pts or not nom_pts:
        return {
            "gouge_free": False,
            "min_distance": 0.0,
            "required_clearance": required_clearance,
            "max_gouge_depth": required_clearance,
        }

    min_dist = float("inf")
    for px, py in tool_pts:
        for nx, ny in nom_pts:
            d = math.hypot(px - nx, py - ny)
            if d < min_dist:
                min_dist = d

    max_gouge = max(0.0, required_clearance - min_dist)
    return {
        "gouge_free": min_dist >= (required_clearance - gouge_tol),
        "min_distance": round(min_dist, 5),
        "required_clearance": round(required_clearance, 5),
        "max_gouge_depth": round(max_gouge, 5),
    }


def _sample_cutting_xy_points(gcode_text: str, samples_per_segment: int = 24) -> List[Tuple[float, float]]:
    """Independently samples XY positions along all G1/G2/G3 moves that cut below Z=0."""
    pts: List[Tuple[float, float]] = []
    tx, ty, tz = 0.0, 0.0, 5.0
    motion = "G0"
    for raw_line in gcode_text.splitlines():
        code_part = strip_gcode_comments(raw_line)
        if not code_part:
            continue
        words = {k.upper(): float(v) for k, v in WORD_RE.findall(code_part)}
        for k, v in WORD_RE.findall(code_part):
            if k.upper() == "G" and int(round(float(v))) in (0, 1, 2, 3):
                motion = f"G{int(round(float(v)))}"
        nx = words.get("X", tx)
        ny = words.get("Y", ty)
        nz = words.get("Z", tz)

        if motion in ("G1", "G2", "G3") and min(tz, nz) < -1e-4 and ("X" in words or "Y" in words):
            if motion == "G1":
                for k in range(samples_per_segment + 1):
                    t = k / float(samples_per_segment)
                    pts.append((tx + t * (nx - tx), ty + t * (ny - ty)))
            else:
                cw = motion == "G2"
                acx = tx + words.get("I", 0.0)
                acy = ty + words.get("J", 0.0)
                r = math.hypot(tx - acx, ty - acy)
                a0 = math.atan2(ty - acy, tx - acx)
                a1 = math.atan2(ny - acy, nx - acx)
                sweep = (a0 - a1) % (2.0 * math.pi) if cw else (a1 - a0) % (2.0 * math.pi)
                if sweep < 1e-6:
                    sweep = 2.0 * math.pi
                for k in range(samples_per_segment + 1):
                    t = k / float(samples_per_segment)
                    ang = a0 - t * sweep if cw else a0 + t * sweep
                    pts.append((acx + r * math.cos(ang), acy + r * math.sin(ang)))

        tx, ty, tz = nx, ny, nz
    return pts


def _point_to_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _angle_in_arc_span(angle_rad: float, start_rad: float, sweep_rad: float) -> bool:
    """Checks whether angle_rad lies in [start_rad, start_rad + sweep_rad] (signed sweep)."""
    if sweep_rad >= 0:
        rel = (angle_rad - start_rad) % (2.0 * math.pi)
        return rel <= sweep_rad + 1e-9
    rel = (start_rad - angle_rad) % (2.0 * math.pi)
    return rel <= abs(sweep_rad) + 1e-9


def verify_swept_slot_containment(
    gcode_text: str,
    slot_width: float,
    tool_diameter: float,
    *,
    start_x: Optional[float] = None,
    start_y: Optional[float] = None,
    end_x: Optional[float] = None,
    end_y: Optional[float] = None,
    center_x: Optional[float] = None,
    center_y: Optional[float] = None,
    radius: Optional[float] = None,
    start_angle_deg: Optional[float] = None,
    end_angle_deg: Optional[float] = None,
    containment_tol: float = 0.01,
    samples_per_segment: int = 24,
) -> Dict[str, Any]:
    """
    Verifies that every swept tool disk position along cutting moves stays inside
    the declared linear capsule slot or circular arc slot.
    """
    pts = _sample_cutting_xy_points(gcode_text, samples_per_segment=samples_per_segment)
    max_center_offset = (slot_width - tool_diameter) / 2.0
    if not pts:
        return {
            "contained": False,
            "max_center_offset_seen": 0.0,
            "allowed_center_offset": round(max_center_offset, 5),
            "max_overcut": max_center_offset,
            "sampled_points": 0,
        }

    is_arc = center_x is not None and center_y is not None and radius is not None
    if is_arc:
        a0 = math.radians(float(start_angle_deg or 0.0))
        a1 = math.radians(float(end_angle_deg or 0.0))
        sweep = a1 - a0
        sx = float(center_x) + float(radius) * math.cos(a0)
        sy = float(center_y) + float(radius) * math.sin(a0)
        ex = float(center_x) + float(radius) * math.cos(a1)
        ey = float(center_y) + float(radius) * math.sin(a1)

    max_dist = 0.0
    for px, py in pts:
        if is_arc:
            ang = math.atan2(py - float(center_y), px - float(center_x))
            if _angle_in_arc_span(ang, a0, sweep):
                d = abs(math.hypot(px - float(center_x), py - float(center_y)) - float(radius))
            else:
                d = min(math.hypot(px - sx, py - sy), math.hypot(px - ex, py - ey))
        else:
            d = _point_to_segment_distance(
                px, py, float(start_x or 0.0), float(start_y or 0.0), float(end_x or 0.0), float(end_y or 0.0)
            )
        if d > max_dist:
            max_dist = d

    max_overcut = max(0.0, max_dist - max_center_offset)
    return {
        "contained": max_dist <= (max_center_offset + containment_tol),
        "max_center_offset_seen": round(max_dist, 5),
        "allowed_center_offset": round(max_center_offset, 5),
        "max_overcut": round(max_overcut, 5),
        "sampled_points": len(pts),
    }


def verify_swept_pocket_containment(
    gcode_text: str,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    tool_diameter: float,
    containment_tol: float = 0.01,
    samples_per_segment: int = 24,
) -> Dict[str, Any]:
    """
    Verifies that every swept tool disk position along cutting moves stays inside
    the declared rectangular pocket [min_x, max_x] x [min_y, max_y].
    """
    pts = _sample_cutting_xy_points(gcode_text, samples_per_segment=samples_per_segment)
    tool_r = tool_diameter / 2.0
    if not pts:
        return {"contained": False, "max_overcut": tool_r, "sampled_points": 0}

    max_overcut = 0.0
    for px, py in pts:
        over = max(
            (min_x + tool_r) - px,
            px - (max_x - tool_r),
            (min_y + tool_r) - py,
            py - (max_y - tool_r),
            0.0,
        )
        if over > max_overcut:
            max_overcut = over

    return {
        "contained": max_overcut <= containment_tol,
        "max_overcut": round(max_overcut, 5),
        "sampled_points": len(pts),
    }
