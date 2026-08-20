"""
Manual Jog & Machine Control Generator Engine.
Supports:
- Directional incremental jog commands ($J for Grbl/Smoothie and G91 for Standard)
- Work Coordinate System (WCS) zeroing (G10 L20 P1)
- Safe Go-to-Origin sequences (retract Z, move XY, lower Z)
- Manual Spindle start/stop control commands (M3/M4/M5)
"""
from typing import Dict, Any, List, Optional


def generate_jog_command(
    axis: str,
    distance: float,
    feed_rate: float = 1000.0,
    units: str = "mm",
    dialect: str = "grbl",
) -> Dict[str, Any]:
    """
    Generates a single-axis or multi-axis incremental jog command.
    """
    axis_clean = axis.upper().strip()
    valid_axes = ["X", "Y", "Z", "XY", "-XY", "X-Y", "-X-Y"]

    if feed_rate <= 0:
        raise ValueError("Jog feed rate must be greater than zero.")
    if distance == 0:
        raise ValueError("Jog distance cannot be zero.")

    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    dialect_clean = (dialect or "grbl").lower().strip()

    # Build axis string
    if axis_clean in ("X", "Y", "Z"):
        motion_part = f"{axis_clean}{distance:+.3f}"
    elif axis_clean == "XY":
        motion_part = f"X{abs(distance):+.3f} Y{abs(distance):+.3f}"
    elif axis_clean == "-XY":
        motion_part = f"X{-abs(distance):+.3f} Y{abs(distance):+.3f}"
    elif axis_clean == "X-Y":
        motion_part = f"X{abs(distance):+.3f} Y{-abs(distance):+.3f}"
    elif axis_clean == "-X-Y":
        motion_part = f"X{-abs(distance):+.3f} Y{-abs(distance):+.3f}"

    else:
        # Custom formatted axis part passed directly (e.g. "X10 Y5")
        motion_part = axis_clean

    if dialect_clean in ("grbl", "grblhal", "fluidnc", "smoothie", "smoothieware"):
        gcode = f"$J=G91 {unit_cmd} {motion_part} F{feed_rate:.1f}"
    else:
        # Standard G-code incremental move
        gcode = f"G91 {unit_cmd} G1 {motion_part} F{feed_rate:.1f}\nG90"

    return {
        "command_type": "jog_step",
        "axis": axis_clean,
        "distance": distance,
        "feed_rate": feed_rate,
        "gcode": gcode,
    }


def generate_zero_wcs_command(
    axes: Optional[List[str]] = None,
    wcs_slot: int = 1,  # 1 = G54
) -> Dict[str, Any]:
    """
    Generates G10 L20 command to zero specified axes in active WCS.
    """
    if not axes:
        axes = ["X", "Y", "Z"]

    valid_axes = [a.upper().strip() for a in axes if a.upper().strip() in ("X", "Y", "Z")]
    if not valid_axes:
        valid_axes = ["X", "Y", "Z"]

    parts = [f"G10 L20 P{wcs_slot}"]
    for a in valid_axes:
        parts.append(f"{a}0.000")

    gcode = " ".join(parts)
    return {
        "command_type": "zero_wcs",
        "axes": valid_axes,
        "wcs_slot": wcs_slot,
        "gcode": gcode,
    }


def generate_goto_origin_command(
    safe_z_retract: float = 5.0,
    units: str = "mm",
) -> Dict[str, Any]:
    """
    Generates a safe 2-stage rapid return to Work Coordinate Origin (X0 Y0).
    1. Retract Z to safe clearance height
    2. Rapid XY to X0 Y0
    """
    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    lines = [
        f"{unit_cmd} G90 G54 (Ensure absolute WCS 1 mode)",
        f"G0 Z{abs(safe_z_retract):.3f} (Retract to safe clearance)",
        "G0 X0.000 Y0.000 (Rapid to X0 Y0 Part Origin)",
    ]
    return {
        "command_type": "goto_origin",
        "safe_z_retract": safe_z_retract,
        "gcode": "\n".join(lines),
    }


def generate_spindle_manual_command(
    rpm: int = 16000,
    state: bool = True,
    clockwise: bool = True,
) -> Dict[str, Any]:
    """
    Generates manual spindle on/off G-code commands.
    """
    if not state:
        gcode = "M5 (Spindle Stop)"
    else:
        cmd = "M3" if clockwise else "M4"
        gcode = f"{cmd} S{int(rpm)} (Spindle ON at {int(rpm)} RPM)"

    return {
        "command_type": "spindle_control",
        "state": state,
        "rpm": rpm,
        "clockwise": clockwise,
        "gcode": gcode,
    }
