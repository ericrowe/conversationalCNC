"""
Independent G-Code Modal State & Geometry Verification Oracle (CNC-013).
Does NOT import or reuse any geometry helper from backend/app/generators.
Independently parses G-code blocks, tracks modal state (G20/G21, G90/G91, G17/G18/G19, F, XYZ, M-codes),
and validates:
- Arc start-to-center vs end-to-center radius equality (|rs - re| <= arc_tol) and rs > 0
- Arc sweep direction validity
- Finite numeric words (no NaN / inf)
- Single final program termination (M2 / M02 / M30) and zero motion after termination
- Safe Z >= expected_clearance_z before XY rapid (G0) positioning moves
- Absence of leaked error/unknown-op pseudo-comments
"""
import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict


PAREN_COMMENT_RE = re.compile(r"\([^)]*\)")
WORD_RE = re.compile(r"([A-Za-z])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[+-]?(?:nan|inf))", re.IGNORECASE)


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


@dataclass
class GCodeValidationReport:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    arcs: List[ArcRecord] = field(default_factory=list)
    termination_lines: List[int] = field(default_factory=list)
    moves_after_termination: List[int] = field(default_factory=list)
    unsafe_xy_rapids: List[int] = field(default_factory=list)
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
) -> GCodeValidationReport:
    errors: List[str] = []
    warnings: List[str] = []
    arcs: List[ArcRecord] = []
    termination_lines: List[int] = []
    moves_after_termination: List[int] = []
    unsafe_xy_rapids: List[int] = []

    units = "mm"
    distance_mode = "G90"
    plane = "G17"
    motion_mode: Optional[str] = None
    feed_rate: float = 0.0

    curr_x: float = 0.0
    curr_y: float = 0.0
    curr_z: float = 0.0
    z_known: bool = False
    terminated: bool = False

    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")
    min_z, max_z = float("inf"), float("-inf")

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
                    units = "inch"
                elif g_int == 21:
                    units = "mm"
                elif g_int == 90:
                    distance_mode = "G90"
                elif g_int == 91:
                    distance_mode = "G91"
                elif g_int in (17, 18, 19):
                    plane = f"G{g_int}"
                elif g_int in (0, 1, 2, 3):
                    line_g_motion = f"G{g_int}"
                    motion_mode = line_g_motion
                elif g_int in (4, 10, 28, 38, 53, 54, 55, 56, 57, 58, 59, 73, 80, 81, 83, 94):
                    pass
                else:
                    warnings.append(f"Line {line_no}: Unrecognized G-code G{g_int}")
            elif letter == "M":
                m_int = int(round(val))
                line_m_codes.append(m_int)
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

            if active_motion in ("G2", "G3") and plane == "G17":
                if "I" in line_words or "J" in line_words:
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
        bounds=bounds_dict,
        modal_state={
            "units": units,
            "distance_mode": distance_mode,
            "plane": plane,
            "feed_rate": feed_rate,
            "final_xyz": (curr_x, curr_y, curr_z),
        },
    )
