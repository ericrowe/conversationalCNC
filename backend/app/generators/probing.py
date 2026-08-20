"""
Probing & Machine Setup Generator (Homing, Z-Touch Plate, and Corner XYZ Probing).
Supports:
- 2-Stage Z-Touch Plate Probing Macro (Fast search + Slow fine precision touch)
- 3-Axis Corner XYZ Touch Block Macro with tool radius & block lip offset compensation
- In-Program Z-Probe Routine with M0 safety interlocks before spindle start
- Machine Homing ($H) and coordinate state verification
"""
from typing import Dict, Any, List, Optional


def generate_z_probe_macro(
    plate_thickness: float = 14.85,
    search_dist: float = 30.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    retract_height: float = 20.0,
    wcs_slot: int = 1,  # 1 = G54
    units: str = "mm",
) -> Dict[str, Any]:
    """
    Generates a 2-stage Z-probe touch plate macro for Grbl / Standard controllers.
    """
    if plate_thickness < 0:
        raise ValueError("Touch plate thickness cannot be negative.")
    if fast_feed <= 0 or slow_feed <= 0:
        raise ValueError("Probing feed rates must be positive.")

    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    lines = [
        "( =================================================== )",
        "( >>> CONVERSATIONAL CNC: 2-STAGE Z-PROBE MACRO <<< )",
        f"( Target Touch Plate Thickness: {plate_thickness:.3f} {units} )",
        "( =================================================== )",
        f"{unit_cmd} G90 G94 (Absolute distance mode)",
        f"G54 (Ensure WCS 1 active)",
        "",
        "( --- Fast Search Probe --- )",
        "G91 (Incremental mode for probing)",
        f"G38.2 Z-{abs(search_dist):.3f} F{fast_feed:.1f} (Fast probe downward)",
        "G0 Z1.500 (Small lift off plate)",
        "",
        "( --- Precision Fine Touch Probe --- )",
        f"G38.2 Z-3.000 F{slow_feed:.1f} (Slow precision touch)",
        f"G10 L20 P{wcs_slot} Z{plate_thickness:.3f} (Set WCS Z to plate thickness)",
        f"G0 Z{retract_height:.3f} (Retract to safe clearance)",
        "G90 (Return to absolute mode)",
        "( Z-Zero calibrated successfully! )",
    ]

    return {
        "macro_name": "z_probe_touch_plate",
        "plate_thickness": plate_thickness,
        "retract_height": retract_height,
        "gcode": "\n".join(lines),
        "line_count": len(lines),
    }


def generate_corner_xyz_probe_macro(
    tool_diameter: float = 6.35,
    plate_thickness: float = 14.85,
    block_x_lip: float = 10.0,
    block_y_lip: float = 10.0,
    search_dist: float = 25.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    retract_z: float = 15.0,
    wcs_slot: int = 1,
    units: str = "mm",
) -> Dict[str, Any]:
    """
    Generates a full 3-axis Corner XYZ touch block macro.
    1. Probes Z surface -> sets Z = plate_thickness
    2. Moves outside X edge -> probes X -> sets X = -(tool_radius + block_x_lip)
    3. Moves outside Y edge -> probes Y -> sets Y = -(tool_radius + block_y_lip)
    4. Moves to (0,0) at safe Z clearance.
    """
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be positive.")

    radius = tool_diameter / 2.0
    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"

    lines = [
        "( =================================================== )",
        "( >>> CONVERSATIONAL CNC: CORNER XYZ PROBE MACRO <<< )",
        f"( Tool Dia: {tool_diameter:.3f}mm | Plate Z: {plate_thickness:.3f}mm )",
        f"( Block Lip X: {block_x_lip:.3f}mm | Lip Y: {block_y_lip:.3f}mm )",
        "( =================================================== )",
        f"{unit_cmd} G90 G94",
        "G54",
        "",
        "( --- Step 1: Probe Z Surface --- )",
        "G91",
        f"G38.2 Z-{abs(search_dist):.3f} F{fast_feed:.1f}",
        "G0 Z1.500",
        f"G38.2 Z-3.000 F{slow_feed:.1f}",
        f"G10 L20 P{wcs_slot} Z{plate_thickness:.3f}",
        f"G0 Z{retract_z:.3f}",
        "G90",
        "",
        "( --- Step 2: Probe X Edge --- )",
        f"G0 X-{(radius + block_x_lip + 5.0):.3f} (Move outside X edge)",
        f"G0 Z{plate_thickness / 2.0:.3f} (Lower to edge mid-height)",
        "G91",
        f"G38.2 X{abs(search_dist):.3f} F{fast_feed:.1f} (Probe towards X block)",
        "G0 X-1.500",
        f"G38.2 X3.000 F{slow_feed:.1f}",
        f"G10 L20 P{wcs_slot} X-{(radius + block_x_lip):.3f} (Set X zero with tool offset)",
        "G0 X-5.000",
        "G90",
        f"G0 Z{retract_z:.3f} (Retract Z)",
        "",
        "( --- Step 3: Probe Y Edge --- )",
        f"G0 X{block_x_lip + 5.0:.3f} (Move inside X)",
        f"G0 Y-{(radius + block_y_lip + 5.0):.3f} (Move outside Y edge)",
        f"G0 Z{plate_thickness / 2.0:.3f} (Lower to edge mid-height)",
        "G91",
        f"G38.2 Y{abs(search_dist):.3f} F{fast_feed:.1f} (Probe towards Y block)",
        "G0 Y-1.500",
        f"G38.2 Y3.000 F{slow_feed:.1f}",
        f"G10 L20 P{wcs_slot} Y-{(radius + block_y_lip):.3f} (Set Y zero with tool offset)",
        "G0 Y-5.000",
        "G90",
        f"G0 Z{retract_z:.3f}",
        f"G0 X0.000 Y0.000 (Move to newly calibrated XYZ Part Zero)",
        "( Corner XYZ Zero successfully calibrated! )",
    ]

    return {
        "macro_name": "corner_xyz_probe",
        "tool_diameter": tool_diameter,
        "plate_thickness": plate_thickness,
        "gcode": "\n".join(lines),
        "line_count": len(lines),
    }


def generate_in_program_probe_block(
    plate_thickness: float = 14.85,
    search_dist: float = 30.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    retract_z: float = 20.0,
) -> List[str]:
    """
    Generates in-program probing routine with M0 safety pauses for operator clip attachment and removal.
    """
    return [
        "( ======================================================== )",
        "( >>> STEP 1: ATTACH Z-PROBE CLIP TO BIT & PLACE PLATE <<< )",
        "( ======================================================== )",
        "M0 (Paused: Attach probe clip to collet, place plate on stock, then press Cycle Start)",
        "G91 (Incremental mode for probing)",
        f"G38.2 Z-{abs(search_dist):.3f} F{fast_feed:.1f} (Fast probe)",
        "G0 Z1.500",
        f"G38.2 Z-3.000 F{slow_feed:.1f} (Fine precision touch)",
        f"G10 L20 P1 Z{plate_thickness:.3f} (Set G54 Z zero)",
        f"G0 Z{retract_z:.3f} (Safe clearance retract)",
        "G90 (Return to absolute mode)",
        "( ======================================================== )",
        "( >>> STEP 2: REMOVE PROBE CLIP & TOUCH PLATE NOW!     <<< )",
        "( ======================================================== )",
        "M0 (Paused: Remove clip and touch plate from stock, then press Cycle Start to begin cutting)",
        "",
    ]


def generate_homing_macro() -> Dict[str, Any]:
    """
    Generates standard Grbl homing command sequence ($H) and coordinate inspection.
    """
    lines = [
        "( =================================================== )",
        "( >>> CONVERSATIONAL CNC: MACHINE HOMING CYCLE    <<< )",
        "( =================================================== )",
        "$H (Initiate homing cycle on limit switches)",
        "G21 G90 (Metric absolute mode)",
        "G54 (Activate Work Coordinate System 1)",
        "$G (Print parser modal state)",
    ]
    return {
        "macro_name": "homing_cycle",
        "gcode": "\n".join(lines),
        "line_count": len(lines),
    }
