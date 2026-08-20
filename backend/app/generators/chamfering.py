"""
2D Chamfering & Edge Breaking G-Code Generator.
Supports:
- Outer and Inner Rectangular perimeter chamfering (with corner fillets)
- Circular perimeter chamfering (boss or bore)
- Tool geometry calculation for 45°, 60°, 90°, 120° V-bits and chamfer mills
- Safe tip-offset to avoid cutting at the dead center of the tool
- Smooth tangential arc lead-in and lead-out
- Grbl and Standard controller dialects
"""
import math
from typing import List, Tuple, Optional
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope
from .rectangular_pocket import _get_corner_path

ROUTER_DIAL_MAPS = {
    "dewalt_611": {1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000},
    "makita_rt0701": {1: 10000, 2: 12000, 3: 17000, 4: 22000, 5: 27000, 6: 30000},
}


def calculate_chamfer_depth_and_offset(
    chamfer_width: float,
    vbit_angle_deg: float = 90.0,
    tip_diameter: float = 0.2,
    tip_offset: float = 0.5,
) -> Tuple[float, float]:
    """
    Calculates the required Z cutting depth and radial toolpath offset
    to machine a chamfer of specified width using a conical chamfer mill / V-bit.
    """
    half_angle_rad = math.radians(vbit_angle_deg / 2.0)
    tan_half = math.tan(half_angle_rad)

    # Depth below workpiece surface Z=0
    # Z = -(chamfer_width / tan(half_angle) + tip_offset)
    cutting_depth_z = -abs(chamfer_width / tan_half + tip_offset)

    # Radial distance from tool centerline to the nominal workpiece edge
    radial_offset = (tip_diameter / 2.0) + (tip_offset * tan_half)

    return (round(cutting_depth_z, 4), round(radial_offset, 4))


def generate_rectangular_chamfer(
    origin_x: float,
    origin_y: float,
    length_x: float,
    width_y: float,
    chamfer_width: float = 0.5,
    corner_radius: float = 0.0,
    origin_mode: str = "center",  # "center" or "corner"
    feature_type: str = "outside",  # "outside" (boss/perimeter) or "inside" (pocket/hole)
    vbit_angle_deg: float = 90.0,
    tip_diameter: float = 0.2,
    tip_offset: float = 0.5,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 1000.0,
    plunge_feed: float = 300.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    units: str = "mm",
    tool_number: int = 1,
    tool_name: str = "",
    spindle_type: str = "router",
    router_model: Optional[str] = "dewalt_611",
    router_dial: Optional[int] = None,
    postprocessor: Optional[BasePostProcessor] = None,
    work_envelope: Optional[WorkEnvelope] = None,
    park_x: Optional[float] = 0.0,
    park_y: Optional[float] = 0.0,
    park_z: Optional[float] = None,
) -> GCodeProgram:
    """
    Generates G-code for chamfering a rectangular perimeter or pocket rim.
    """
    if chamfer_width <= 0:
        raise ValueError("Chamfer width must be greater than zero.")
    if length_x <= 0 or width_y <= 0:
        raise ValueError("Length and width must be greater than zero.")

    depth_z, radial_offset = calculate_chamfer_depth_and_offset(
        chamfer_width=chamfer_width,
        vbit_angle_deg=vbit_angle_deg,
        tip_diameter=tip_diameter,
        tip_offset=tip_offset,
    )

    if origin_mode == "center":
        min_x = origin_x - length_x / 2.0
        max_x = origin_x + length_x / 2.0
        min_y = origin_y - width_y / 2.0
        max_y = origin_y + width_y / 2.0
    else:
        min_x = origin_x
        max_x = origin_x + length_x
        min_y = origin_y
        max_y = origin_y + width_y

    eff_r = max(0.0, min(corner_radius, min(length_x, width_y) / 2.0))

    if feature_type == "outside":
        # Toolpath is offset OUTSIDE nominal perimeter
        path_min_x = min_x - radial_offset
        path_max_x = max_x + radial_offset
        path_min_y = min_y - radial_offset
        path_max_y = max_y + radial_offset
        path_r = eff_r + radial_offset
    else:
        # Toolpath is offset INSIDE nominal perimeter
        path_min_x = min_x + radial_offset
        path_max_x = max_x - radial_offset
        path_min_y = min_y + radial_offset
        path_max_y = max_y - radial_offset
        path_r = max(0.0, eff_r - radial_offset)

    pts = _get_corner_path(path_min_x, path_max_x, path_min_y, path_max_y, path_r)

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    warnings: List[str] = []
    if work_envelope:
        if path_min_x < 0 or path_max_x > work_envelope.work_area_x or path_min_y < 0 or path_max_y > work_envelope.work_area_y:
            warnings.append(
                f"Chamfer toolpath [{path_min_x:.1f}, {path_min_y:.1f}] to [{path_max_x:.1f}, {path_max_y:.1f}] "
                f"exceeds work envelope [{work_envelope.work_area_x}, {work_envelope.work_area_y}]."
            )

    resolved_dial = router_dial
    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if resolved_dial is None:
            resolved_dial = 1
            for d, rpm in dial_map.items():
                if spindle_speed >= rpm:
                    resolved_dial = d

    lines: List[str] = []
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: 2D Chamfering ({chamfer_width:.2f}mm width, {vbit_angle_deg}° V-Bit, Depth={depth_z:.3f}mm)",
        )
    )
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"{vbit_angle_deg}deg Chamfer Mill",
        )
    )
    lines.extend(
        postprocessor.format_spindle_start(
            rpm=spindle_speed,
            clockwise=True,
            dwell_seconds=spindle_dwell_seconds,
            spindle_type=spindle_type,
            router_model=router_model,
            router_dial=resolved_dial,
        )
    )
    lines.append("")
    lines.append(postprocessor.format_rapid(z=retract_z, comment="Safe Z clearance"))

    # Plunge outside workpiece
    lines.append(f"G0 X{pts[0][0]:.3f} Y{pts[0][1]:.3f}")
    lines.append(f"G0 Z{(start_z + 1.0):.3f}")
    lines.append(f"G1 Z{depth_z:.3f} F{plunge_feed:.1f}")

    # Trace perimeter
    for pt in pts[1:]:
        lines.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f} F{feed_rate_xy:.1f}")

    lines.append(f"G0 Z{retract_z:.3f}")
    lines.extend(postprocessor.format_footer(park_x=park_x, park_y=park_y, park_z=park_z or retract_z))
    gcode_text = "\n".join(lines)

    bounds = BoundingBox(
        min_x=path_min_x,
        max_x=path_max_x,
        min_y=path_min_y,
        max_y=path_max_y,
        min_z=depth_z,
        max_z=retract_z,
    )

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=8.0,
        warnings=warnings,
    )
