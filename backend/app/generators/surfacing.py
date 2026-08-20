import math
from typing import List, Tuple, Optional
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope
from .drilling import ROUTER_DIAL_MAPS

def generate_surfacing(
    length_x: float,
    width_y: float,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    origin_mode: str = "corner",  # "corner" (lower-left) or "center"
    total_depth_z: float = 1.0,
    stepdown_z: float = 0.5,
    tool_diameter: float = 25.4,
    stepover_percent: float = 70.0,
    cut_direction: str = "zigzag",  # "zigzag" (bidirectional) or "climb_oneway" (unidirectional)
    overtravel: float = 2.0,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 1500.0,
    plunge_feed: float = 300.0,
    rapid_feed: float = 5000.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    units: str = "mm",
    tool_number: int = 1,
    tool_name: str = "",
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
    Pure Python G-Code Generator for Workpiece & Spoilboard Surfacing / Facing.
    
    Generates deterministic, dialect-compliant G-code for flattening stock surfaces
    or resurfacing spoilboards using surfacing bits / flycutters / endmills.
    
    Features:
    - Zig-Zag (fastest bidirectional) or One-Way (uniform climb finish)
    - Corner or Center datum origin
    - Configurable overtravel clearance past stock boundaries
    - Multi-pass Z stepdowns
    - Soft limit boundary checks & Grbl safety compliant
    """
    if length_x <= 0:
        raise ValueError("Stock length (X) must be greater than zero.")

    if width_y <= 0:
        raise ValueError("Stock width (Y) must be greater than zero.")

    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be greater than zero.")

    if stepdown_z <= 0:
        raise ValueError("Stepdown (Z) must be greater than zero.")

    if stepover_percent <= 0 or stepover_percent > 95:
        raise ValueError("Stepover percentage must be between 1% and 95%.")

    if feed_rate_xy <= 0:
        raise ValueError("Cutting feed rate must be greater than zero.")

    if plunge_feed <= 0:
        raise ValueError("Plunge feed rate must be greater than zero.")

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    warnings: List[str] = []
    effective_spindle_speed = spindle_speed
    resolved_dial = router_dial

    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if effective_spindle_speed < min_spindle_rpm:
            warnings.append(
                f"Requested speed ({effective_spindle_speed} RPM) is below {router_model.replace('_', ' ').title()} minimum speed ({min_spindle_rpm} RPM). Clamped to {min_spindle_rpm} RPM (Dial 1)."
            )
            effective_spindle_speed = min_spindle_rpm

        if resolved_dial is None:
            resolved_dial = min(dial_map.keys(), key=lambda d: abs(dial_map[d] - effective_spindle_speed))

    final_target_z = start_z - abs(total_depth_z)
    effective_retract_z = max(retract_z, start_z + 1.0)
    total_depth = abs(start_z - final_target_z)

    num_z_passes = max(1, int(math.ceil(total_depth / stepdown_z)))
    actual_stepdown = total_depth / num_z_passes

    # Compute stock boundary
    if origin_mode == "center":
        stock_min_x = origin_x - (length_x / 2.0)
        stock_max_x = origin_x + (length_x / 2.0)
        stock_min_y = origin_y - (width_y / 2.0)
        stock_max_y = origin_y + (width_y / 2.0)
    else:  # corner
        stock_min_x = origin_x
        stock_max_x = origin_x + length_x
        stock_min_y = origin_y
        stock_max_y = origin_y + width_y

    tool_radius = tool_diameter / 2.0
    stepover_dist = tool_diameter * (stepover_percent / 100.0)

    # Tool center path bounds along X (including overtravel)
    x_min_cut = stock_min_x - tool_radius - overtravel
    x_max_cut = stock_max_x + tool_radius + overtravel

    # Y track lines covering full width
    y_start_cut = stock_min_y + tool_radius - (stepover_dist * 0.3)
    y_end_cut = stock_max_y - tool_radius + (stepover_dist * 0.3)

    y_tracks: List[float] = []
    curr_y = y_start_cut
    while curr_y <= y_end_cut:
        y_tracks.append(round(curr_y, 3))
        curr_y += stepover_dist

    if not y_tracks or y_tracks[-1] < y_end_cut:
        y_tracks.append(round(y_end_cut, 3))

    lines: List[str] = []

    # 1. Header
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: Surfacing / Facing ({length_x:.1f}x{width_y:.1f}mm, Depth={total_depth:.2f}mm, {cut_direction})",
        )
    )

    # 2. Tool
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"Surfacing Bit D{tool_diameter:.2f}mm",
        )
    )

    # 3. Spindle
    lines.extend(
        postprocessor.format_spindle_start(
            rpm=effective_spindle_speed,
            clockwise=True,
            dwell_seconds=spindle_dwell_seconds,
            spindle_type=spindle_type,
            router_model=router_model,
            router_dial=resolved_dial,
        )
    )
    lines.append("")

    # 4. Safe Z
    lines.append(postprocessor.format_rapid(z=effective_retract_z, comment="Safe Z clearance"))

    # Bounds
    bounds_min_x = x_min_cut - tool_radius
    bounds_max_x = x_max_cut + tool_radius
    bounds_min_y = stock_min_y
    bounds_max_y = stock_max_y
    if park_x is not None:
        bounds_min_x = min(bounds_min_x, park_x)
        bounds_max_x = max(bounds_max_x, park_x)
    if park_y is not None:
        bounds_min_y = min(bounds_min_y, park_y)
        bounds_max_y = max(bounds_max_y, park_y)

    bounds = BoundingBox(
        min_x=bounds_min_x,
        max_x=bounds_max_x,
        min_y=bounds_min_y,
        max_y=bounds_max_y,
        min_z=final_target_z,
        max_z=effective_retract_z,
    )

    if work_envelope:
        env_violations = work_envelope.validate_bounds(bounds)
        if env_violations:
            warnings.extend(env_violations)

    total_rapid_dist = abs(effective_retract_z)
    total_feed_dist = 0.0
    total_dwell_time = spindle_dwell_seconds

    current_x = 0.0
    current_y = 0.0
    current_z = effective_retract_z

    # 5. Generate passes for each Z layer
    for z_step in range(1, num_z_passes + 1):
        curr_layer_z = start_z - (z_step * actual_stepdown)
        if z_step == num_z_passes:
            curr_layer_z = final_target_z

        lines.append(f"(--- Z Layer {z_step}/{num_z_passes} at Z{curr_layer_z:.3f} ---)")

        if cut_direction == "zigzag":
            # Start at first Y track, x_min_cut
            start_track_y = y_tracks[0]
            lines.append(postprocessor.format_rapid(x=x_min_cut, y=start_track_y))
            lines.append(postprocessor.format_rapid(z=start_z + 0.5))
            lines.append(postprocessor.format_linear(z=curr_layer_z, feed_rate=plunge_feed))
            total_feed_dist += abs(start_z + 0.5 - curr_layer_z)

            current_x = x_min_cut
            current_y = start_track_y
            current_z = curr_layer_z

            for idx, y_pos in enumerate(y_tracks):
                if idx > 0:
                    # Stepover in Y
                    lines.append(postprocessor.format_linear(y=y_pos, feed_rate=feed_rate_xy, comment="Stepover"))
                    total_feed_dist += abs(y_pos - current_y)
                    current_y = y_pos

                # Cut pass across X
                if idx % 2 == 0:
                    target_x = x_max_cut
                else:
                    target_x = x_min_cut

                lines.append(postprocessor.format_linear(x=target_x, feed_rate=feed_rate_xy, comment=f"Pass {idx+1}/{len(y_tracks)}"))
                total_feed_dist += abs(target_x - current_x)
                current_x = target_x

            # Lift to clearance at end of layer
            lines.append(postprocessor.format_rapid(z=effective_retract_z))
            total_rapid_dist += abs(effective_retract_z - curr_layer_z)
            current_z = effective_retract_z

        else:  # climb_oneway
            for idx, y_pos in enumerate(y_tracks):
                # Rapid to start of this pass at safe Z
                lines.append(postprocessor.format_rapid(x=x_min_cut, y=y_pos))
                lines.append(postprocessor.format_rapid(z=start_z + 0.5))
                lines.append(postprocessor.format_linear(z=curr_layer_z, feed_rate=plunge_feed))
                total_feed_dist += abs(start_z + 0.5 - curr_layer_z)

                # Cut line across X
                lines.append(postprocessor.format_linear(x=x_max_cut, feed_rate=feed_rate_xy, comment=f"Pass {idx+1}/{len(y_tracks)}"))
                total_feed_dist += abs(x_max_cut - x_min_cut)

                # Retract back up to safe Z
                lines.append(postprocessor.format_rapid(z=effective_retract_z))
                total_rapid_dist += abs(effective_retract_z - curr_layer_z)

            current_x = x_max_cut
            current_y = y_tracks[-1]
            current_z = effective_retract_z

        lines.append("")

    # Footer
    effective_park_z = park_z if park_z is not None else effective_retract_z
    footer_lines = postprocessor.format_footer(
        park_z=effective_park_z, park_x=park_x, park_y=park_y
    )
    lines.extend(footer_lines)

    if park_x is not None and park_y is not None:
        total_rapid_dist += math.hypot(park_x - current_x, park_y - current_y)

    estimated_time = (
        (total_rapid_dist / rapid_feed * 60.0)
        + (total_feed_dist / feed_rate_xy * 60.0)
        + total_dwell_time
    )

    gcode_str = "\n".join(lines)

    return GCodeProgram(
        gcode=gcode_str,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=estimated_time,
        warnings=warnings,
    )
