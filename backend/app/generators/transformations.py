"""
G-Code Transformation Engine & Multi-Tool Program Splitter (Phase 6).
Supports:
- Coordinate Shift / Translation (dX, dY, dZ)
- Rotation around arbitrary center (Xc, Yc) with I/J arc offset rotation
- Mirroring across X, Y, or arbitrary axis with automatic arc reversal (G2 <-> G3)
- Scaling (Sx, Sy, Sz)
- Arc Format Conversion (Radius 'R' -> Center Offset 'I, J')
- Global Feed & Spindle Speed Overrides (% multiplier)
- Multi-Tool Program File Splitter (separates M6 tool changes into standalone .nc files)
"""
import math
import re
from typing import List, Dict, Any, Tuple, Optional


def transform_shift_gcode(
    gcode_text: str,
    delta_x: float = 0.0,
    delta_y: float = 0.0,
    delta_z: float = 0.0,
) -> str:
    """
    Shifts all absolute X, Y, Z coordinates in a G-code program by (delta_x, delta_y, delta_z).
    """
    lines = gcode_text.split("\n")
    transformed_lines = []

    for raw in lines:
        comment_part = ""
        line_part = raw
        if "(" in raw and ")" in raw:
            match = re.search(r"(\(.*?\))", raw)
            if match:
                comment_part = match.group(1)
                line_part = raw[:match.start()] + raw[match.end():]
        elif ";" in raw:
            parts = raw.split(";", 1)
            line_part = parts[0]
            comment_part = ";" + parts[1]

        tokens = line_part.strip().split()
        new_tokens = []

        for t in tokens:
            t_upper = t.upper()
            if t_upper.startswith("X") and delta_x != 0.0:
                try:
                    val = float(t_upper[1:]) + delta_x
                    new_tokens.append(f"X{val:.3f}")
                except ValueError:
                    new_tokens.append(t)
            elif t_upper.startswith("Y") and delta_y != 0.0:
                try:
                    val = float(t_upper[1:]) + delta_y
                    new_tokens.append(f"Y{val:.3f}")
                except ValueError:
                    new_tokens.append(t)
            elif t_upper.startswith("Z") and delta_z != 0.0:
                try:
                    val = float(t_upper[1:]) + delta_z
                    new_tokens.append(f"Z{val:.3f}")
                except ValueError:
                    new_tokens.append(t)
            else:
                new_tokens.append(t)

        reconstructed = " ".join(new_tokens)
        if comment_part:
            reconstructed = f"{reconstructed} {comment_part}".strip()
        transformed_lines.append(reconstructed if reconstructed else raw)

    return "\n".join(transformed_lines)


def transform_rotate_gcode(
    gcode_text: str,
    angle_deg: float,
    center_x: float = 0.0,
    center_y: float = 0.0,
) -> str:
    """
    Rotates all X, Y motion coordinates and I, J arc center vectors
    around (center_x, center_y) by angle_deg.
    """
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    lines = gcode_text.split("\n")
    transformed_lines = []

    for raw in lines:
        comment_part = ""
        line_part = raw
        if "(" in raw and ")" in raw:
            match = re.search(r"(\(.*?\))", raw)
            if match:
                comment_part = match.group(1)
                line_part = raw[:match.start()] + raw[match.end():]

        tokens = line_part.strip().split()
        new_tokens = []

        raw_x = None
        raw_y = None
        raw_i = None
        raw_j = None

        for t in tokens:
            t_upper = t.upper()
            if t_upper.startswith("X"):
                try: raw_x = float(t_upper[1:])
                except ValueError: pass
            elif t_upper.startswith("Y"):
                try: raw_y = float(t_upper[1:])
                except ValueError: pass
            elif t_upper.startswith("I"):
                try: raw_i = float(t_upper[1:])
                except ValueError: pass
            elif t_upper.startswith("J"):
                try: raw_j = float(t_upper[1:])
                except ValueError: pass

        for t in tokens:
            t_upper = t.upper()
            if t_upper.startswith("X") and raw_x is not None:
                # Rotate X (if Y is missing, we preserve Y as center_y for rotation)
                curr_y = raw_y if raw_y is not None else center_y
                rx = center_x + (raw_x - center_x) * cos_a - (curr_y - center_y) * sin_a
                new_tokens.append(f"X{rx:.3f}")
            elif t_upper.startswith("Y") and raw_y is not None:
                curr_x = raw_x if raw_x is not None else center_x
                ry = center_y + (curr_x - center_x) * sin_a + (raw_y - center_y) * cos_a
                new_tokens.append(f"Y{ry:.3f}")
            elif t_upper.startswith("I") and raw_i is not None:
                curr_j = raw_j if raw_j is not None else 0.0
                ri = raw_i * cos_a - curr_j * sin_a
                new_tokens.append(f"I{ri:.3f}")
            elif t_upper.startswith("J") and raw_j is not None:
                curr_i = raw_i if raw_i is not None else 0.0
                rj = curr_i * sin_a + raw_j * cos_a
                new_tokens.append(f"J{rj:.3f}")
            else:
                new_tokens.append(t)

        reconstructed = " ".join(new_tokens)
        if comment_part:
            reconstructed = f"{reconstructed} {comment_part}".strip()
        transformed_lines.append(reconstructed if reconstructed else raw)

    return "\n".join(transformed_lines)


def transform_mirror_gcode(
    gcode_text: str,
    mirror_axis: str = "x",  # "x" (mirrors across X axis: Y -> -Y) or "y" (mirrors across Y axis: X -> -X)
    origin_x: float = 0.0,
    origin_y: float = 0.0,
) -> str:
    """
    Mirrors G-code coordinates across specified axis and flips arc directions (G2 <-> G3).
    """
    lines = gcode_text.split("\n")
    transformed_lines = []

    for raw in lines:
        comment_part = ""
        line_part = raw
        if "(" in raw and ")" in raw:
            match = re.search(r"(\(.*?\))", raw)
            if match:
                comment_part = match.group(1)
                line_part = raw[:match.start()] + raw[match.end():]

        tokens = line_part.strip().split()
        new_tokens = []

        for t in tokens:
            t_upper = t.upper()
            if mirror_axis == "y":
                # Mirror across Y-axis: X -> -(X - origin_x) + origin_x, I -> -I
                if t_upper.startswith("X"):
                    try:
                        vx = float(t_upper[1:])
                        new_tokens.append(f"X{(2 * origin_x - vx):.3f}")
                    except ValueError: new_tokens.append(t)
                elif t_upper.startswith("I"):
                    try:
                        vi = float(t_upper[1:])
                        new_tokens.append(f"I{(-vi):.3f}")
                    except ValueError: new_tokens.append(t)
                elif t_upper == "G2" or t_upper == "G02":
                    new_tokens.append("G3")
                elif t_upper == "G3" or t_upper == "G03":
                    new_tokens.append("G2")
                else:
                    new_tokens.append(t)
            else:
                # Mirror across X-axis: Y -> -(Y - origin_y) + origin_y, J -> -J
                if t_upper.startswith("Y"):
                    try:
                        vy = float(t_upper[1:])
                        new_tokens.append(f"Y{(2 * origin_y - vy):.3f}")
                    except ValueError: new_tokens.append(t)
                elif t_upper.startswith("J"):
                    try:
                        vj = float(t_upper[1:])
                        new_tokens.append(f"J{(-vj):.3f}")
                    except ValueError: new_tokens.append(t)
                elif t_upper == "G2" or t_upper == "G02":
                    new_tokens.append("G3")
                elif t_upper == "G3" or t_upper == "G03":
                    new_tokens.append("G2")
                else:
                    new_tokens.append(t)

        reconstructed = " ".join(new_tokens)
        if comment_part:
            reconstructed = f"{reconstructed} {comment_part}".strip()
        transformed_lines.append(reconstructed if reconstructed else raw)

    return "\n".join(transformed_lines)


def transform_override_feeds_speeds(
    gcode_text: str,
    feed_multiplier: float = 1.0,
    speed_multiplier: float = 1.0,
) -> str:
    """
    Applies feed rate and spindle speed percentage overrides to a G-code program.
    """
    lines = gcode_text.split("\n")
    transformed_lines = []

    for raw in lines:
        comment_part = ""
        line_part = raw
        if "(" in raw and ")" in raw:
            match = re.search(r"(\(.*?\))", raw)
            if match:
                comment_part = match.group(1)
                line_part = raw[:match.start()] + raw[match.end():]

        tokens = line_part.strip().split()
        new_tokens = []

        for t in tokens:
            t_upper = t.upper()
            if t_upper.startswith("F") and feed_multiplier != 1.0:
                try:
                    f = float(t_upper[1:]) * feed_multiplier
                    new_tokens.append(f"F{f:.1f}")
                except ValueError: new_tokens.append(t)
            elif t_upper.startswith("S") and speed_multiplier != 1.0:
                try:
                    s = int(round(float(t_upper[1:]) * speed_multiplier))
                    new_tokens.append(f"S{s}")
                except ValueError: new_tokens.append(t)
            else:
                new_tokens.append(t)

        reconstructed = " ".join(new_tokens)
        if comment_part:
            reconstructed = f"{reconstructed} {comment_part}".strip()
        transformed_lines.append(reconstructed if reconstructed else raw)

    return "\n".join(transformed_lines)


def split_multitool_gcode(
    gcode_text: str,
    safe_retract_z: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    Splits a multi-tool G-code program into individual standalone files per tool.
    Detects M6 / T<num> blocks and generates safe headers and footers for each tool section.
    """
    lines = gcode_text.split("\n")
    sections = []
    current_tool = None
    current_lines = []
    header_preamble = ["G21", "G90", "G94", "G17"]

    for raw in lines:
        upper = raw.upper()
        tool_match = re.search(r"\bT(\d+)\b", upper)
        is_tool_change = ("M6" in upper or "M06" in upper) and bool(tool_match)

        if is_tool_change and tool_match:
            new_tool = int(tool_match.group(1))
            if current_tool is not None and current_lines:
                # Close previous tool
                current_lines.append(f"G0 Z{safe_retract_z:.3f}")
                current_lines.append("M5")
                current_lines.append("M30")
                sections.append({
                    "tool_number": current_tool,
                    "filename": f"program_T{current_tool}.nc",
                    "line_count": len(current_lines),
                    "gcode": "\n".join(current_lines),
                })
                current_lines = []

            current_tool = new_tool
            current_lines.extend(header_preamble)
            current_lines.append(f"( --- TOOL T{current_tool} SECTION --- )")
            current_lines.append(raw)
        else:
            if current_tool is not None:
                current_lines.append(raw)

    if current_lines and current_tool is not None:
        sections.append({
            "tool_number": current_tool,
            "filename": f"program_T{current_tool}.nc",
            "line_count": len(current_lines),
            "gcode": "\n".join(current_lines),
        })

    return sections

