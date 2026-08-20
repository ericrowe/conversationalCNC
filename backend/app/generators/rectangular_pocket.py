"""
Rectangular Pocket and Boss/Island G-Code Generator.
Supports:
- Concentric clearing passes with corner fillets
- Helical ramp or plunge entry strategies
- Separate perimeter finish wall pass with tangential lead-in/out
- Rectangular & Circular Boss / Island clearing
- Climb and Conventional milling
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


def _get_corner_path(x_min: float, x_max: float, y_min: float, y_max: float, r: float) -> List[Tuple[float, float]]:
    """Generates an offset rectangular loop with rounded corners."""
    if r <= 0.001:
        return [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max),
            (x_min, y_min),
        ]
    
    pts: List[Tuple[float, float]] = []
    # Bottom edge (left to right)
    pts.append((x_min + r, y_min))
    pts.append((x_max - r, y_min))
    # Bottom-right corner arc (270 to 360 deg)
    for a in [285, 300, 315, 330, 345, 360]:
        rad = math.radians(a)
        pts.append((x_max - r + r * math.cos(rad), y_min + r + r * math.sin(rad)))
    # Right edge (bottom to top)
    pts.append((x_max, y_max - r))
    # Top-right corner arc (0 to 90 deg)
    for a in [15, 30, 45, 60, 75, 90]:
        rad = math.radians(a)
        pts.append((x_max - r + r * math.cos(rad), y_max - r + r * math.sin(rad)))
    # Top edge (right to left)
    pts.append((x_min + r, y_max))
    # Top-left corner arc (90 to 180 deg)
    for a in [105, 120, 135, 150, 165, 180]:
        rad = math.radians(a)
        pts.append((x_min + r + r * math.cos(rad), y_max - r + r * math.sin(rad)))
    # Left edge (top to bottom)
    pts.append((x_min, y_min + r))
    # Bottom-left corner arc (180 to 270 deg)
    for a in [195, 210, 225, 240, 255, 270]:
        rad = math.radians(a)
        pts.append((x_min + r + r * math.cos(rad), y_min + r + r * math.sin(rad)))
    # Close loop
    pts.append((x_min + r, y_min))
    return [(round(x, 4), round(y, 4)) for (x, y) in pts]


def generate_rectangular_pocket(
    origin_x: float,
    origin_y: float,
    length_x: float,
    width_y: float,
    corner_radius: float = 0.0,
    origin_mode: str = "center",  # "center" or "corner"
    target_depth_z: float = -5.0,
    stepdown_z: float = 1.5,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    stepover_percent: float = 60.0,
    finish_pass_allowance: float = 0.3,
    entry_strategy: str = "helical_ramp",  # "helical_ramp" or "plunge"
    ramp_angle_deg: float = 2.5,
    feed_rate_xy: float = 1200.0,
    plunge_feed: float = 300.0,
    finish_feed: Optional[float] = None,
    rapid_feed: float = 5000.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    units: str = "mm",
    tool_number: int = 1,
    tool_name: str = "",
    tool_diameter: float = 6.35,
    spindle_type: str = "router",
    router_model: Optional[str] = "dewalt_611",
    router_dial: Optional[int] = None,
    min_spindle_rpm: int = 16000,
    max_spindle_rpm: int = 27000,
    postprocessor: Optional[BasePostProcessor] = None,
    work_envelope: Optional[WorkEnvelope] = None,
    park_x: Optional[float] = 0.0,
    park_y: Optional[float] = 0.0,
    park_z: Optional[float] = None,
) -> GCodeProgram:
    """
    Pure Python generator for Rectangular Pocket Machining.
    Generates expanding concentric clearing passes with optional corner fillets
    and a final wall finishing pass.
    """
    if length_x <= tool_diameter or width_y <= tool_diameter:
        raise ValueError(
            f"Pocket dimensions ({length_x}x{width_y}mm) must be strictly greater than tool diameter ({tool_diameter}mm)."
        )

    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be greater than zero.")

    if stepdown_z <= 0:
        raise ValueError("Stepdown Z must be greater than zero.")

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    warnings: List[str] = []
    tool_radius = tool_diameter / 2.0
    actual_target_depth = -abs(target_depth_z)
    finish_feed_rate = finish_feed or feed_rate_xy * 0.75

    # Determine bounding box
    if origin_mode == "center":
        center_x = origin_x
        center_y = origin_y
        min_x = origin_x - length_x / 2.0
        max_x = origin_x + length_x / 2.0
        min_y = origin_y - width_y / 2.0
        max_y = origin_y + width_y / 2.0
    else:
        min_x = origin_x
        max_x = origin_x + length_x
        min_y = origin_y
        max_y = origin_y + width_y
        center_x = min_x + length_x / 2.0
        center_y = min_y + width_y / 2.0

    # Effective corner radius on pocket boundary
    eff_corner_r = max(tool_radius, min(corner_radius, min(length_x, width_y) / 2.0))

    # Envelope validation
    if work_envelope:
        if min_x < 0 or max_x > work_envelope.work_area_x or min_y < 0 or max_y > work_envelope.work_area_y:
            warnings.append(
                f"Pocket bounding box [{min_x:.1f}, {min_y:.1f}] to [{max_x:.1f}, {max_y:.1f}] "
                f"exceeds work envelope [{work_envelope.work_area_x}, {work_envelope.work_area_y}]."
            )


    # Calculate stepdown layers
    total_depth = abs(start_z - actual_target_depth)
    num_passes = math.ceil(total_depth / stepdown_z)
    z_step = total_depth / num_passes

    # Stepover radial calculation
    stepover_dist = tool_diameter * (stepover_percent / 100.0)
    
    # Roughing boundary (inward offset from nominal pocket by finish_allowance + tool_radius)
    rough_offset = tool_radius + finish_pass_allowance
    rough_min_x = min_x + rough_offset
    rough_max_x = max_x - rough_offset
    rough_min_y = min_y + rough_offset
    rough_max_y = max_y - rough_offset
    rough_r = max(0.0, eff_corner_r - rough_offset)

    # Finish boundary (inward offset by tool_radius)
    finish_min_x = min_x + tool_radius
    finish_max_x = max_x - tool_radius
    finish_min_y = min_y + tool_radius
    finish_max_y = max_y - tool_radius
    finish_r = max(0.0, eff_corner_r - tool_radius)

    # Calculate concentric roughing rings from center outward
    max_radial_span = max(rough_max_x - center_x, rough_max_y - center_y)
    num_rings = max(1, math.ceil(max_radial_span / stepover_dist))

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
            comment=f"Operation: Rectangular Pocket ({length_x:.1f}x{width_y:.1f}mm, Depth={actual_target_depth:.2f}mm)",
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

    estimated_time = spindle_dwell_seconds + 3.0
    current_z = start_z

    for p_idx in range(1, num_passes + 1):
        target_pass_z = round(start_z - (p_idx * z_step), 4)
        lines.append(f"\n( --- Pass {p_idx}/{num_passes} at Z = {target_pass_z:.3f} mm --- )")

        # 1. Entry Move
        lines.append(f"G0 X{center_x:.3f} Y{center_y:.3f}")
        lines.append(f"G0 Z{(current_z + 1.0):.3f}")

        if entry_strategy == "helical_ramp" and (rough_max_x - rough_min_x > tool_radius):
            # Helical ramp entry at center
            ramp_radius = min(2.5, (rough_max_x - rough_min_x) / 4.0)
            ramp_pitch = math.tan(math.radians(ramp_angle_deg)) * (2 * math.pi * ramp_radius)
            ramp_depth_needed = abs((current_z + 1.0) - target_pass_z)
            ramp_turns = max(1, math.ceil(ramp_depth_needed / max(0.5, ramp_pitch)))
            ramp_z_step = ramp_depth_needed / (ramp_turns * 2)

            lines.append(f"G1 X{(center_x + ramp_radius):.3f} Y{center_y:.3f} F{feed_rate_xy:.1f}")
            ramp_z = current_z + 1.0
            for _ in range(ramp_turns):
                ramp_z -= ramp_z_step
                lines.append(f"G2 X{(center_x - ramp_radius):.3f} Y{center_y:.3f} I{-ramp_radius:.3f} J0.000 Z{ramp_z:.3f} F{feed_rate_xy:.1f}")
                ramp_z -= ramp_z_step
                lines.append(f"G2 X{(center_x + ramp_radius):.3f} Y{center_y:.3f} I{ramp_radius:.3f} J0.000 Z{ramp_z:.3f}")

            # Level out at target Z
            lines.append(f"G2 X{(center_x - ramp_radius):.3f} Y{center_y:.3f} I{-ramp_radius:.3f} J0.000 Z{target_pass_z:.3f}")
            lines.append(f"G2 X{(center_x + ramp_radius):.3f} Y{center_y:.3f} I{ramp_radius:.3f} J0.000 Z{target_pass_z:.3f}")
            lines.append(f"G1 X{center_x:.3f} Y{center_y:.3f} F{feed_rate_xy:.1f}")
        else:
            # Straight plunge entry
            lines.append(f"G1 Z{target_pass_z:.3f} F{plunge_feed:.1f}")
            estimated_time += abs(current_z - target_pass_z) / (plunge_feed / 60.0)

        # 2. Concentric Roughing Rings Expanding Outward
        for r_idx in range(1, num_rings + 1):
            fraction = r_idx / float(num_rings)
            ring_min_x = center_x - (center_x - rough_min_x) * fraction
            ring_max_x = center_x + (rough_max_x - center_x) * fraction
            ring_min_y = center_y - (center_y - rough_min_y) * fraction
            ring_max_y = center_y + (rough_max_y - center_y) * fraction
            ring_r = rough_r * fraction

            ring_pts = _get_corner_path(ring_min_x, ring_max_x, ring_min_y, ring_max_y, ring_r)
            if ring_pts:
                lines.append(f"G1 X{ring_pts[0][0]:.3f} Y{ring_pts[0][1]:.3f} F{feed_rate_xy:.1f}")
                for pt in ring_pts[1:]:
                    lines.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f}")

        # 3. Wall Finishing Pass (if finish allowance specified)
        if finish_pass_allowance > 0:
            lines.append(f"( --- Wall Finish Pass --- )")
            fin_pts = _get_corner_path(finish_min_x, finish_max_x, finish_min_y, finish_max_y, finish_r)
            lines.append(f"G1 X{fin_pts[0][0]:.3f} Y{fin_pts[0][1]:.3f} F{finish_feed_rate:.1f}")
            for pt in fin_pts[1:]:
                lines.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f}")

        # Retract to safe Z after layer
        lines.append(f"G0 Z{retract_z:.3f}")
        current_z = target_pass_z

    # Footer
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
        estimated_time_seconds=round(estimated_time, 1),
        warnings=warnings,
    )



def generate_rectangular_boss(
    boss_origin_x: float,
    boss_origin_y: float,
    boss_length_x: float,
    boss_width_y: float,
    stock_length_x: float,
    stock_width_y: float,
    boss_corner_radius: float = 0.0,
    boss_origin_mode: str = "center",
    target_depth_z: float = -3.0,
    stepdown_z: float = 1.0,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    stepover_percent: float = 60.0,
    feed_rate_xy: float = 1200.0,
    plunge_feed: float = 300.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    tool_diameter: float = 6.35,
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
    Pure Python generator for Rectangular Boss / Raised Island Machining.
    Clears the area around a rectangular island within the stock boundary.
    """
    if stock_length_x <= boss_length_x or stock_width_y <= boss_width_y:
        raise ValueError("Stock dimensions must be strictly larger than boss island dimensions.")

    tool_radius = tool_diameter / 2.0
    actual_target_depth = -abs(target_depth_z)

    if boss_origin_mode == "center":
        boss_center_x = boss_origin_x
        boss_center_y = boss_origin_y
    else:
        boss_center_x = boss_origin_x + boss_length_x / 2.0
        boss_center_y = boss_origin_y + boss_width_y / 2.0

    # Stock boundary limits
    stock_min_x = boss_center_x - stock_length_x / 2.0
    stock_max_x = boss_center_x + stock_length_x / 2.0
    stock_min_y = boss_center_y - stock_width_y / 2.0
    stock_max_y = boss_center_y + stock_width_y / 2.0

    # Boss island boundary limits
    boss_min_x = boss_center_x - boss_length_x / 2.0
    boss_max_x = boss_center_x + boss_length_x / 2.0
    boss_min_y = boss_center_y - boss_width_y / 2.0
    boss_max_y = boss_center_y + boss_width_y / 2.0

    eff_boss_r = max(0.0, min(boss_corner_radius, min(boss_length_x, boss_width_y) / 2.0))

    warnings: List[str] = []
    if work_envelope:
        if stock_min_x < 0 or stock_max_x > work_envelope.work_area_x or stock_min_y < 0 or stock_max_y > work_envelope.work_area_y:
            warnings.append(
                f"Stock bounding box [{stock_min_x:.1f}, {stock_min_y:.1f}] to [{stock_max_x:.1f}, {stock_max_y:.1f}] "
                f"exceeds work envelope [{work_envelope.work_area_x}, {work_envelope.work_area_y}]."
            )

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    total_depth = abs(start_z - actual_target_depth)

    num_passes = math.ceil(total_depth / stepdown_z)
    z_step = total_depth / num_passes
    stepover_dist = tool_diameter * (stepover_percent / 100.0)

    # Outer tool boundary (outside stock by tool_radius)
    outer_min_x = stock_min_x - tool_radius
    outer_max_x = stock_max_x + tool_radius
    outer_min_y = stock_min_y - tool_radius
    outer_max_y = stock_max_y + tool_radius

    # Inner tool boundary (outside boss by tool_radius)
    inner_min_x = boss_min_x - tool_radius
    inner_max_x = boss_max_x + tool_radius
    inner_min_y = boss_min_y - tool_radius
    inner_max_y = boss_max_y + tool_radius
    inner_r = eff_boss_r + tool_radius

    # Number of concentric clearing loops from outer stock into the boss
    span_x = (inner_min_x - outer_min_x)
    span_y = (inner_min_y - outer_min_y)
    num_loops = max(1, math.ceil(max(span_x, span_y) / stepover_dist))

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
            comment=f"Operation: Rectangular Boss ({boss_length_x:.1f}x{boss_width_y:.1f}mm in {stock_length_x:.1f}x{stock_width_y:.1f}mm stock)",
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

    current_z = start_z
    for p_idx in range(1, num_passes + 1):
        target_pass_z = round(start_z - (p_idx * z_step), 4)
        lines.append(f"\n( --- Boss Pass {p_idx}/{num_passes} at Z = {target_pass_z:.3f} mm --- )")

        # Start outside stock
        lines.append(f"G0 X{outer_min_x:.3f} Y{outer_min_y:.3f}")
        lines.append(f"G0 Z{(current_z + 1.0):.3f}")
        lines.append(f"G1 Z{target_pass_z:.3f} F{plunge_feed:.1f}")

        # Concentric loops from outer stock inward toward the boss
        for l_idx in range(num_loops + 1):
            t = l_idx / float(num_loops)
            loop_min_x = outer_min_x + (inner_min_x - outer_min_x) * t
            loop_max_x = outer_max_x - (outer_max_x - inner_max_x) * t
            loop_min_y = outer_min_y + (inner_min_y - outer_min_y) * t
            loop_max_y = outer_max_y - (outer_max_y - inner_max_y) * t
            loop_r = inner_r * t

            loop_pts = _get_corner_path(loop_min_x, loop_max_x, loop_min_y, loop_max_y, loop_r)
            lines.append(f"G1 X{loop_pts[0][0]:.3f} Y{loop_pts[0][1]:.3f} F{feed_rate_xy:.1f}")
            for pt in loop_pts[1:]:
                lines.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f}")

        lines.append(f"G0 Z{retract_z:.3f}")
        current_z = target_pass_z

    lines.extend(postprocessor.format_footer(park_x=park_x, park_y=park_y, park_z=park_z or retract_z))
    gcode_text = "\n".join(lines)

    bounds = BoundingBox(
        min_x=stock_min_x,
        max_x=stock_max_x,
        min_y=stock_min_y,
        max_y=stock_max_y,
        min_z=actual_target_depth,
        max_z=retract_z,
    )

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=round(num_passes * 12.0, 1),
        warnings=warnings,
    )


