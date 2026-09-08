"""
Probing & Machine Setup Generator (Homing, Z-Touch Plate, Corner XYZ, Bore & Boss Center).
Supports:
- 2-Stage Z-Touch Plate Probing Macro (Fast search + Slow fine precision touch)
- 3-Axis Corner XYZ Touch Block Macro with 4-corner orientation support & tool radius compensation
- In-Bore 4-Point Circle Center Probing Macro
- Outside Boss 4-Point Cylinder Center Probing Macro
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
    corner: str = "front_left",  # 'front_left', 'front_right', 'back_left', 'back_right'
    search_dist: float = 25.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    retract_z: float = 15.0,
    wcs_slot: int = 1,
    units: str = "mm",
) -> Dict[str, Any]:
    """
    Generates a full 3-axis Corner XYZ touch block macro with 4-corner orientation support.
    
    Corner Orientations:
    - front_left (Lower-Left):  X-, Y- outer approach -> probes X+, Y+ -> sets X=-(Lip+R), Y=-(Lip+R)
    - front_right (Lower-Right): X+, Y- outer approach -> probes X-, Y+ -> sets X=+(Lip+R), Y=-(Lip+R)
    - back_left (Upper-Left):   X-, Y+ outer approach -> probes X+, Y- -> sets X=-(Lip+R), Y=+(Lip+R)
    - back_right (Upper-Right): X+, Y+ outer approach -> probes X-, Y- -> sets X=+(Lip+R), Y=+(Lip+R)
    """
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be positive.")

    radius = tool_diameter / 2.0
    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    corner_norm = (corner or "front_left").lower().strip().replace(" ", "_").replace("-", "_")

    # Determine probing vector signs and zero offset signs
    is_left = "left" in corner_norm or corner_norm in ("ll", "ul")
    is_front = "front" in corner_norm or corner_norm in ("ll", "lr")

    # Offset from corner origin to plate touch point
    x_offset_sign = -1.0 if is_left else 1.0
    y_offset_sign = -1.0 if is_front else 1.0

    # Approach direction outside block
    x_outer_sign = -1.0 if is_left else 1.0
    y_outer_sign = -1.0 if is_front else 1.0

    # Probe motion direction into block
    x_probe_sign = 1.0 if is_left else -1.0
    y_probe_sign = 1.0 if is_front else -1.0

    x_zero_val = x_offset_sign * (radius + block_x_lip)
    y_zero_val = y_offset_sign * (radius + block_y_lip)

    x_approach_dist = x_outer_sign * (radius + block_x_lip + 5.0)
    y_approach_dist = y_outer_sign * (radius + block_y_lip + 5.0)

    lines = [
        "( =================================================== )",
        "( >>> CONVERSATIONAL CNC: CORNER XYZ PROBE MACRO <<< )",
        f"( Corner: {corner_norm.upper()} | Tool Dia: {tool_diameter:.3f}mm | Plate Z: {plate_thickness:.3f}mm )",
        f"( Block Lip X: {block_x_lip:.3f}mm | Lip Y: {block_y_lip:.3f}mm )",
        "( =================================================== )",
        f"{unit_cmd} G90 G94",
        f"G54",
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
        f"G0 X{x_approach_dist:.3f} (Move outside X edge)",
        f"G0 Z{plate_thickness / 2.0:.3f} (Lower to edge mid-height)",
        "G91",
        f"G38.2 X{x_probe_sign * abs(search_dist):.3f} F{fast_feed:.1f} (Probe towards X block)",
        f"G0 X{-x_probe_sign * 1.500:.3f}",
        f"G38.2 X{x_probe_sign * 3.000:.3f} F{slow_feed:.1f}",
        f"G10 L20 P{wcs_slot} X{x_zero_val:.3f} (Set X zero with tool offset)",
        f"G0 X{-x_probe_sign * 5.000:.3f}",
        "G90",
        f"G0 Z{retract_z:.3f} (Retract Z)",
        "",
        "( --- Step 3: Probe Y Edge --- )",
        f"G0 X{x_offset_sign * (block_x_lip + 5.0):.3f} (Move inside X)",
        f"G0 Y{y_approach_dist:.3f} (Move outside Y edge)",
        f"G0 Z{plate_thickness / 2.0:.3f} (Lower to edge mid-height)",
        "G91",
        f"G38.2 Y{y_probe_sign * abs(search_dist):.3f} F{fast_feed:.1f} (Probe towards Y block)",
        f"G0 Y{-y_probe_sign * 1.500:.3f}",
        f"G38.2 Y{y_probe_sign * 3.000:.3f} F{slow_feed:.1f}",
        f"G10 L20 P{wcs_slot} Y{y_zero_val:.3f} (Set Y zero with tool offset)",
        f"G0 Y{-y_probe_sign * 5.000:.3f}",
        "G90",
        f"G0 Z{retract_z:.3f}",
        f"G0 X0.000 Y0.000 (Move to newly calibrated XYZ Part Zero)",
        f"( Corner {corner_norm.upper()} XYZ Zero successfully calibrated! )",
    ]

    return {
        "macro_name": f"corner_xyz_probe_{corner_norm}",
        "corner": corner_norm,
        "tool_diameter": tool_diameter,
        "plate_thickness": plate_thickness,
        "gcode": "\n".join(lines),
        "line_count": len(lines),
    }


def generate_bore_center_probe_macro(
    approx_diameter: float = 50.0,
    tool_diameter: float = 6.35,
    search_dist: float = 30.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    retract_z: float = 10.0,
    wcs_slot: int = 1,
    units: str = "mm",
) -> Dict[str, Any]:
    """
    Generates a 4-point inside circle / bore center probing routine.
    Positions tool at approx center of bore at safe Z, lowers into cavity,
    probes X- and X+, centers X, probes Y- and Y+, centers Y, and sets X0 Y0.
    """
    if approx_diameter <= 0:
        raise ValueError("Approximate bore diameter must be positive.")
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be positive.")

    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    max_search = min(abs(search_dist), approx_diameter * 0.75)

    lines = [
        "( ========================================================= )",
        "( >>> CONVERSATIONAL CNC: IN-BORE 4-POINT CENTER PROBE  <<< )",
        f"( Approx Dia: {approx_diameter:.3f}mm | Tool Dia: {tool_diameter:.3f}mm )",
        "( ========================================================= )",
        f"{unit_cmd} G90 G94",
        f"G54",
        f"G0 Z{retract_z:.3f} (Ensure Safe Z)",
        "",
        "( --- Probe X- Inside Wall --- )",
        "G91",
        f"G38.2 X-{max_search:.3f} F{fast_feed:.1f}",
        "G0 X1.500",
        f"G38.2 X-3.000 F{slow_feed:.1f}",
        "#1 = #5061 (Record X- touch point)",
        "G0 X5.000 (Retract from wall)",
        "G90",
        "",
        "( --- Probe X+ Inside Wall --- )",
        "G91",
        f"G38.2 X{max_search:.3f} F{fast_feed:.1f}",
        "G0 X-1.500",
        f"G38.2 X3.000 F{slow_feed:.1f}",
        "#2 = #5061 (Record X+ touch point)",
        "G0 X-5.000",
        "G90",
        "",
        "( --- Calculate & Move to X Center --- )",
        "#3 = [[#1 + #2] / 2.0]",
        "G0 X#3 (Move to X Centerline)",
        "",
        "( --- Probe Y- Inside Wall --- )",
        "G91",
        f"G38.2 Y-{max_search:.3f} F{fast_feed:.1f}",
        "G0 Y1.500",
        f"G38.2 Y-3.000 F{slow_feed:.1f}",
        "#4 = #5062 (Record Y- touch point)",
        "G0 Y5.000",
        "G90",
        "",
        "( --- Probe Y+ Inside Wall --- )",
        "G91",
        f"G38.2 Y{max_search:.3f} F{fast_feed:.1f}",
        "G0 Y-1.500",
        f"G38.2 Y3.000 F{slow_feed:.1f}",
        "#5 = #5062 (Record Y+ touch point)",
        "G0 Y-5.000",
        "G90",
        "",
        "( --- Calculate & Move to Y Center --- )",
        "#6 = [[#4 + #5] / 2.0]",
        "G0 Y#6 (Move to Y Centerline)",
        f"G10 L20 P{wcs_slot} X0.000 Y0.000 (Set True Hole Center X0 Y0)",
        f"G0 Z{retract_z:.3f} (Retract to Clearance)",
        "( Hole Center X0 Y0 calibrated successfully! )",
    ]

    return {
        "macro_name": "in_bore_center_probe",
        "approx_diameter": approx_diameter,
        "tool_diameter": tool_diameter,
        "gcode": "\n".join(lines),
        "line_count": len(lines),
    }


def generate_boss_center_probe_macro(
    approx_diameter: float = 40.0,
    tool_diameter: float = 6.35,
    search_dist: float = 15.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    retract_z: float = 15.0,
    wcs_slot: int = 1,
    units: str = "mm",
) -> Dict[str, Any]:
    """
    Generates a 4-point outside cylinder / boss center probing routine.
    """
    if approx_diameter <= 0:
        raise ValueError("Approximate boss diameter must be positive.")
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be positive.")

    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    radius = tool_diameter / 2.0
    half_dia = approx_diameter / 2.0
    safe_standoff = half_dia + radius + 5.0

    lines = [
        "( ========================================================= )",
        "( >>> CONVERSATIONAL CNC: OUTSIDE BOSS 4-POINT CENTER PROBE <<< )",
        f"( Approx Boss Dia: {approx_diameter:.3f}mm | Tool Dia: {tool_diameter:.3f}mm )",
        "( ========================================================= )",
        f"{unit_cmd} G90 G94",
        f"G54",
        f"G0 Z{retract_z:.3f}",
        "",
        "( --- Probe X- Outside Boss Wall --- )",
        f"G0 X-{safe_standoff:.3f} Y0.000",
        "G0 Z-5.000 (Lower to probing height)",
        "G91",
        f"G38.2 X{abs(search_dist):.3f} F{fast_feed:.1f}",
        "G0 X-1.500",
        f"G38.2 X3.000 F{slow_feed:.1f}",
        "#1 = #5061 (Record X- outer contact point)",
        "G0 X-5.000",
        "G90",
        f"G0 Z{retract_z:.3f}",
        "",
        "( --- Probe X+ Outside Boss Wall --- )",
        f"G0 X{safe_standoff:.3f} Y0.000",
        "G0 Z-5.000",
        "G91",
        f"G38.2 X-{abs(search_dist):.3f} F{fast_feed:.1f}",
        "G0 X1.500",
        f"G38.2 X-3.000 F{slow_feed:.1f}",
        "#2 = #5061 (Record X+ outer contact point)",
        "G0 X5.000",
        "G90",
        f"G0 Z{retract_z:.3f}",
        "",
        "( --- Calculate & Move to X Center --- )",
        "#3 = [[#1 + #2] / 2.0]",
        "G0 X#3 Y0.000",
        "",
        "( --- Probe Y- Outside Boss Wall --- )",
        f"G0 X#3 Y-{safe_standoff:.3f}",
        "G0 Z-5.000",
        "G91",
        f"G38.2 Y{abs(search_dist):.3f} F{fast_feed:.1f}",
        "G0 Y-1.500",
        f"G38.2 Y3.000 F{slow_feed:.1f}",
        "#4 = #5062 (Record Y- outer contact point)",
        "G0 Y-5.000",
        "G90",
        f"G0 Z{retract_z:.3f}",
        "",
        "( --- Probe Y+ Outside Boss Wall --- )",
        f"G0 X#3 Y{safe_standoff:.3f}",
        "G0 Z-5.000",
        "G91",
        f"G38.2 Y-{abs(search_dist):.3f} F{fast_feed:.1f}",
        "G0 Y1.500",
        f"G38.2 Y-3.000 F{slow_feed:.1f}",
        "#5 = #5062 (Record Y+ outer contact point)",
        "G0 Y5.000",
        "G90",
        f"G0 Z{retract_z:.3f}",
        "",
        "( --- Move to True Boss Center --- )",
        "#6 = [[#4 + #5] / 2.0]",
        "G0 X#3 Y#6",
        f"G10 L20 P{wcs_slot} X0.000 Y0.000 (Set Boss Center X0 Y0)",
        f"G0 Z{retract_z:.3f}",
        "( Boss Center X0 Y0 calibrated successfully! )",
    ]

    return {
        "macro_name": "outside_boss_center_probe",
        "approx_diameter": approx_diameter,
        "tool_diameter": tool_diameter,
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
    Generates standard Grbl machine homing sequence ($H) and coordinate inspection.
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
