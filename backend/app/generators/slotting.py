"""
Linear and Arc Slotting G-Code Generator.
Supports:
- Straight linear slots (start to end coordinate with slot width)
- Circular arc slots (center, radius, start angle, arc span, width)
- Depth stepdowns with safe retracts
- Full slotting (tool diameter == slot width) and wider slot profiling
- Grbl and Standard controller dialects
"""
import math
from typing import List, Tuple, Optional
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope

ROUTER_DIAL_MAPS = {
    "dewalt_611": {1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000},
    "makita_rt0701": {1: 10000, 2: 12000, 3: 17000, 4: 22000, 5: 27000, 6: 30000},
}


def generate_linear_slot(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    slot_width: float,
    target_depth_z: float = -3.0,
    stepdown_z: float = 1.0,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 200.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    tool_diameter: float = 3.175,
    tool_number: int = 1,
    tool_name: str = "",
    units: str = "mm",
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
    Generates G-code for a straight linear slot.
    """
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be greater than zero.")
    if slot_width < tool_diameter - 1e-4:
        raise ValueError(f"Slot width ({slot_width}mm) cannot be smaller than tool diameter ({tool_diameter}mm).")

    slot_length = math.hypot(end_x - start_x, end_y - start_y)
    if slot_length < 0.001:
        raise ValueError("Slot start and end points must be distinct.")

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    actual_target_depth = -abs(target_depth_z)
    total_depth = abs(start_z - actual_target_depth)
    num_passes = math.ceil(total_depth / stepdown_z)
    z_step = total_depth / num_passes

    # Compute bounding box
    half_w = slot_width / 2.0
    dx = end_x - start_x
    dy = end_y - start_y
    angle = math.atan2(dy, dx)
    perp_angle = angle + math.pi / 2.0

    ox = half_w * math.cos(perp_angle)
    oy = half_w * math.sin(perp_angle)

    corner_pts = [
        (start_x + ox, start_y + oy),
        (end_x + ox, end_y + oy),
        (end_x - ox, end_y - oy),
        (start_x - ox, start_y - oy),
    ]

    min_x = min(p[0] for p in corner_pts)
    max_x = max(p[0] for p in corner_pts)
    min_y = min(p[1] for p in corner_pts)
    max_y = max(p[1] for p in corner_pts)

    warnings: List[str] = []
    if work_envelope:
        if min_x < 0 or max_x > work_envelope.work_area_x or min_y < 0 or max_y > work_envelope.work_area_y:
            warnings.append(
                f"Slot bounds [{min_x:.1f}, {min_y:.1f}] to [{max_x:.1f}, {max_y:.1f}] "
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
            comment=f"Operation: Linear Slot ({slot_length:.1f}mm length, {slot_width:.2f}mm width, Depth={actual_target_depth:.2f}mm)",
        )
    )
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"Endmill D{tool_diameter:.3f}mm",
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

    # Tool offset for wider slot passes
    excess_width = slot_width - tool_diameter
    num_side_offsets = 0
    if excess_width > 0.05:
        # Profile both sides of slot
        offset_dist = excess_width / 2.0
        num_side_offsets = 1

    current_z = start_z
    for p_idx in range(1, num_passes + 1):
        target_pass_z = round(start_z - (p_idx * z_step), 4)
        lines.append(f"\n( --- Pass {p_idx}/{num_passes} at Z = {target_pass_z:.3f} mm --- )")

        if num_side_offsets == 0:
            # Single centerline slot pass
            lines.append(f"G0 X{start_x:.3f} Y{start_y:.3f}")
            lines.append(f"G0 Z{(current_z + 1.0):.3f}")
            lines.append(f"G1 Z{target_pass_z:.3f} F{plunge_feed:.1f}")
            lines.append(f"G1 X{end_x:.3f} Y{end_y:.3f} F{feed_rate_xy:.1f}")
        else:
            # Center pass followed by side clearing passes
            offset_dist = excess_width / 2.0
            side_ox = offset_dist * math.cos(perp_angle)
            side_oy = offset_dist * math.sin(perp_angle)

            # Center plunge and slot cut
            lines.append(f"G0 X{start_x:.3f} Y{start_y:.3f}")
            lines.append(f"G0 Z{(current_z + 1.0):.3f}")
            lines.append(f"G1 Z{target_pass_z:.3f} F{plunge_feed:.1f}")
            lines.append(f"G1 X{end_x:.3f} Y{end_y:.3f} F{feed_rate_xy:.1f}")

            # Left offset pass
            lines.append(f"G1 X{(end_x + side_ox):.3f} Y{(end_y + side_oy):.3f}")
            lines.append(f"G1 X{(start_x + side_ox):.3f} Y{(start_y + side_oy):.3f}")

            # Right offset pass
            lines.append(f"G1 X{(start_x - side_ox):.3f} Y{(start_y - side_oy):.3f}")
            lines.append(f"G1 X{(end_x - side_ox):.3f} Y{(end_y - side_oy):.3f}")

        lines.append(f"G0 Z{retract_z:.3f}")
        current_z = target_pass_z

    lines.extend(postprocessor.format_footer(park_x=park_x, park_y=park_y, park_z=park_z or retract_z))
    gcode_text = "\n".join(lines)

    bounds = BoundingBox(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        min_z=actual_target_depth,
        max_z=retract_z,
    )

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=round(num_passes * 6.0, 1),
        warnings=warnings,
    )
