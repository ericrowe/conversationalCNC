import math
from typing import List, Tuple, Optional, Dict, Any
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope
from .drilling import ROUTER_DIAL_MAPS

# Standard Thread Standards Database (Metric ISO and Imperial UNC/UNF)
THREAD_STANDARDS: Dict[str, Dict[str, Any]] = {
    # Metric ISO Coarse (pitch in mm, nominal dia in mm)
    "M2x0.4": {"type": "metric", "nominal_dia": 2.0, "pitch": 0.4, "tap_drill_dia": 1.6},
    "M2.5x0.45": {"type": "metric", "nominal_dia": 2.5, "pitch": 0.45, "tap_drill_dia": 2.05},
    "M3x0.5": {"type": "metric", "nominal_dia": 3.0, "pitch": 0.5, "tap_drill_dia": 2.5},
    "M4x0.7": {"type": "metric", "nominal_dia": 4.0, "pitch": 0.7, "tap_drill_dia": 3.3},
    "M5x0.8": {"type": "metric", "nominal_dia": 5.0, "pitch": 0.8, "tap_drill_dia": 4.2},
    "M6x1.0": {"type": "metric", "nominal_dia": 6.0, "pitch": 1.0, "tap_drill_dia": 5.0},
    "M8x1.25": {"type": "metric", "nominal_dia": 8.0, "pitch": 1.25, "tap_drill_dia": 6.8},
    "M8x1.0": {"type": "metric", "nominal_dia": 8.0, "pitch": 1.0, "tap_drill_dia": 7.0},
    "M10x1.5": {"type": "metric", "nominal_dia": 10.0, "pitch": 1.5, "tap_drill_dia": 8.5},
    "M10x1.25": {"type": "metric", "nominal_dia": 10.0, "pitch": 1.25, "tap_drill_dia": 8.8},
    "M12x1.75": {"type": "metric", "nominal_dia": 12.0, "pitch": 1.75, "tap_drill_dia": 10.2},
    "M12x1.5": {"type": "metric", "nominal_dia": 12.0, "pitch": 1.5, "tap_drill_dia": 10.5},
    "M14x2.0": {"type": "metric", "nominal_dia": 14.0, "pitch": 2.0, "tap_drill_dia": 12.0},
    "M16x2.0": {"type": "metric", "nominal_dia": 16.0, "pitch": 2.0, "tap_drill_dia": 14.0},
    "M20x2.5": {"type": "metric", "nominal_dia": 20.0, "pitch": 2.5, "tap_drill_dia": 17.5},

    # Imperial UNC (Coarse - dimensions converted to mm)
    "#2-56 UNC": {"type": "imperial_unc", "nominal_dia": 2.184, "pitch": 25.4 / 56.0, "tpi": 56, "tap_drill_dia": 1.85},
    "#4-40 UNC": {"type": "imperial_unc", "nominal_dia": 2.845, "pitch": 25.4 / 40.0, "tpi": 40, "tap_drill_dia": 2.35},
    "#6-32 UNC": {"type": "imperial_unc", "nominal_dia": 3.505, "pitch": 25.4 / 32.0, "tpi": 32, "tap_drill_dia": 2.85},
    "#8-32 UNC": {"type": "imperial_unc", "nominal_dia": 4.166, "pitch": 25.4 / 32.0, "tpi": 32, "tap_drill_dia": 3.50},
    "#10-24 UNC": {"type": "imperial_unc", "nominal_dia": 4.826, "pitch": 25.4 / 24.0, "tpi": 24, "tap_drill_dia": 3.90},
    "1/4-20 UNC": {"type": "imperial_unc", "nominal_dia": 6.350, "pitch": 25.4 / 20.0, "tpi": 20, "tap_drill_dia": 5.10},
    "5/16-18 UNC": {"type": "imperial_unc", "nominal_dia": 7.938, "pitch": 25.4 / 18.0, "tpi": 18, "tap_drill_dia": 6.60},
    "3/8-16 UNC": {"type": "imperial_unc", "nominal_dia": 9.525, "pitch": 25.4 / 16.0, "tpi": 16, "tap_drill_dia": 8.00},
    "7/16-14 UNC": {"type": "imperial_unc", "nominal_dia": 11.112, "pitch": 25.4 / 14.0, "tpi": 14, "tap_drill_dia": 9.40},
    "1/2-13 UNC": {"type": "imperial_unc", "nominal_dia": 12.700, "pitch": 25.4 / 13.0, "tpi": 13, "tap_drill_dia": 10.80},
    "5/8-11 UNC": {"type": "imperial_unc", "nominal_dia": 15.875, "pitch": 25.4 / 11.0, "tpi": 11, "tap_drill_dia": 13.50},
    "3/4-10 UNC": {"type": "imperial_unc", "nominal_dia": 19.050, "pitch": 25.4 / 10.0, "tpi": 10, "tap_drill_dia": 16.50},

    # Imperial UNF (Fine)
    "#10-32 UNF": {"type": "imperial_unf", "nominal_dia": 4.826, "pitch": 25.4 / 32.0, "tpi": 32, "tap_drill_dia": 4.10},
    "1/4-28 UNF": {"type": "imperial_unf", "nominal_dia": 6.350, "pitch": 25.4 / 28.0, "tpi": 28, "tap_drill_dia": 5.50},
    "5/16-24 UNF": {"type": "imperial_unf", "nominal_dia": 7.938, "pitch": 25.4 / 24.0, "tpi": 24, "tap_drill_dia": 6.90},
    "3/8-24 UNF": {"type": "imperial_unf", "nominal_dia": 9.525, "pitch": 25.4 / 24.0, "tpi": 24, "tap_drill_dia": 8.50},
    "1/2-20 UNF": {"type": "imperial_unf", "nominal_dia": 12.700, "pitch": 25.4 / 20.0, "tpi": 20, "tap_drill_dia": 11.50},
}


def generate_helical_thread_milling(
    holes: List[Tuple[float, float]],
    nominal_diameter: float,
    pitch: float,
    thread_length: float,
    tool_diameter: float,
    thread_type: str = "internal",  # "internal" (tapped hole) or "external" (stud/rod)
    thread_hand: str = "right_hand",  # "right_hand" or "left_hand"
    milling_direction: str = "bottom_to_top",  # "bottom_to_top" (climb) or "top_to_bottom"
    radial_passes: int = 1,
    spring_passes: int = 0,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 300.0,
    plunge_feed: float = 200.0,
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
    Pure Python G-Code Generator for Helical Thread Milling.
    
    Generates deterministic, dialect-compliant G-code for internal tapped holes or external
    threaded studs using single-point or multi-tooth thread mills.
    
    Features:
    - Internal & External thread geometry
    - Right-hand / Left-hand threads
    - Bottom-to-Top climb milling (standard) or Top-to-Bottom
    - Multi-pass radial stepovers (roughing passes + finish pass + spring passes)
    - Tangential 180° semi-circular helical lead-in & lead-out arcs for smooth, burr-free entry/exit
    - Multi-hole patterns (single, grid, bolt circle)
    - Full Grbl 3D helical interpolation compliance (G2/G3 with X Y Z I J)
    """
    if not holes:
        raise ValueError("At least one thread hole coordinate (x, y) must be provided.")

    if nominal_diameter <= 0:
        raise ValueError("Nominal thread diameter must be greater than zero.")

    if pitch <= 0:
        raise ValueError("Thread pitch must be greater than zero.")

    if thread_length <= 0:
        raise ValueError("Thread length must be greater than zero.")

    if tool_diameter <= 0:
        raise ValueError("Tool cutting diameter must be greater than zero.")

    if thread_type == "internal" and tool_diameter >= nominal_diameter:
        raise ValueError(
            f"Tool diameter ({tool_diameter:.3f}mm) must be strictly less than thread diameter ({nominal_diameter:.3f}mm) for internal thread milling."
        )

    if radial_passes < 1:
        radial_passes = 1

    if spring_passes < 0:
        spring_passes = 0

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    warnings: List[str] = []
    effective_spindle_speed = spindle_speed
    resolved_dial = router_dial

    # Router dial mapping & limits
    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if effective_spindle_speed < min_spindle_rpm:
            warnings.append(
                f"Requested speed ({effective_spindle_speed} RPM) is below {router_model.replace('_', ' ').title()} minimum speed ({min_spindle_rpm} RPM). Clamped to {min_spindle_rpm} RPM (Dial 1)."
            )
            effective_spindle_speed = min_spindle_rpm

        if resolved_dial is None:
            resolved_dial = min(dial_map.keys(), key=lambda d: abs(dial_map[d] - effective_spindle_speed))

    effective_retract_z = max(retract_z, start_z + 1.0)
    z_bottom = start_z - thread_length

    # Calculate number of full helical revolutions
    # Each full 360° circle travels 1 pitch in Z.
    num_revolutions = max(1, int(math.ceil(thread_length / pitch)))

    # Determine arc direction (Climb vs Conventional, RH vs LH, Bottom-to-Top vs Top-to-Bottom)
    if thread_type == "internal":
        if thread_hand == "right_hand":
            is_ccw = (milling_direction == "bottom_to_top")
        else:
            is_ccw = (milling_direction != "bottom_to_top")
    else:  # external
        if thread_hand == "right_hand":
            is_ccw = (milling_direction != "bottom_to_top")
        else:
            is_ccw = (milling_direction == "bottom_to_top")

    # Thread radial depth calculation (ISO 60° thread standard: single thread depth ≈ 0.5413 * P)
    radial_thread_depth = 0.54127 * pitch

    # Calculate target cutting radius (tool center path radius)
    if thread_type == "internal":
        target_final_radius = (nominal_diameter - tool_diameter) / 2.0
        initial_pre_hole_radius = max(0.05, target_final_radius - radial_thread_depth)
    else:  # external
        target_final_radius = (nominal_diameter + tool_diameter) / 2.0
        initial_pre_hole_radius = target_final_radius + radial_thread_depth

    # Check for valid geometry
    if thread_type == "internal" and target_final_radius <= 0.01:
        raise ValueError(
            f"Tool diameter ({tool_diameter:.3f}mm) is too large for thread diameter ({nominal_diameter:.3f}mm)."
        )

    # Compute radial passes list
    pass_radii: List[float] = []
    if radial_passes == 1:
        pass_radii.append(target_final_radius)
    else:
        for p in range(1, radial_passes + 1):
            fraction = p / radial_passes
            if thread_type == "internal":
                r_k = initial_pre_hole_radius + fraction * (target_final_radius - initial_pre_hole_radius)
            else:
                r_k = initial_pre_hole_radius - fraction * (initial_pre_hole_radius - target_final_radius)
            pass_radii.append(r_k)

    # Add spring passes at final radius
    for _ in range(spring_passes):
        pass_radii.append(target_final_radius)

    lines: List[str] = []

    # 1. Header block
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: Helical Thread Milling ({thread_type.title()} {nominal_diameter}mm x {pitch}mm, {len(holes)} holes)",
        )
    )

    # 2. Tool information
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"Thread Mill D{tool_diameter:.3f}mm",
        )
    )

    # 3. Spindle activation
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

    # 4. Safe Z clearance
    lines.append(postprocessor.format_rapid(z=effective_retract_z, comment="Safe Z clearance"))

    # Track bounding box
    max_outer_radius = target_final_radius + (tool_diameter / 2.0)
    min_cut_x = min(h[0] for h in holes) - max_outer_radius
    max_cut_x = max(h[0] for h in holes) + max_outer_radius
    min_cut_y = min(h[1] for h in holes) - max_outer_radius
    max_cut_y = max(h[1] for h in holes) + max_outer_radius

    min_x = min(min_cut_x, park_x) if park_x is not None else min_cut_x
    max_x = max(max_cut_x, park_x) if park_x is not None else max_cut_x
    min_y = min(min_cut_y, park_y) if park_y is not None else min_cut_y
    max_y = max(max_cut_y, park_y) if park_y is not None else max_cut_y

    bounds = BoundingBox(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        min_z=z_bottom,
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

    # 5. Generate Toolpath for each hole/stud location
    for h_idx, (hx, hy) in enumerate(holes, start=1):
        lines.append(f"(--- Thread {h_idx}/{len(holes)} at X{hx:.3f}, Y{hy:.3f} ---)")

        # Rapid move to center at safe retract plane
        lines.append(postprocessor.format_rapid(z=effective_retract_z))
        lines.append(postprocessor.format_rapid(x=hx, y=hy))

        xy_traverse = math.hypot(hx - current_x, hy - current_y)
        total_rapid_dist += xy_traverse + abs(effective_retract_z - current_z)

        # Loop through each radial pass
        for p_idx, cut_radius in enumerate(pass_radii, start=1):
            is_spring = (p_idx > radial_passes)
            pass_label = f"Spring Pass {p_idx - radial_passes}" if is_spring else f"Radial Pass {p_idx}/{radial_passes} (R={cut_radius:.3f}mm)"
            lines.append(f"({pass_label})")

            if milling_direction == "bottom_to_top":
                # Rapid plunge down center of hole to bottom depth
                lines.append(postprocessor.format_rapid(z=start_z + 1.0))
                lines.append(postprocessor.format_linear(z=z_bottom, feed_rate=plunge_feed, comment="Plunge to bottom in center"))
                total_feed_dist += abs(start_z + 1.0 - z_bottom)

                # Tangential 180° semi-circular lead-in arc from center (hx, hy) to (hx + cut_radius, hy)
                lead_radius = cut_radius / 2.0
                lead_in_end_x = hx + cut_radius
                lead_in_end_y = hy
                lead_in_end_z = z_bottom + (0.5 * pitch)

                lead_in_cmd = postprocessor.format_arc(
                    clockwise=not is_ccw,
                    x=lead_in_end_x,
                    y=lead_in_end_y,
                    z=lead_in_end_z,
                    i=lead_radius,
                    j=0.0,
                    feed_rate=feed_rate_xy,
                    comment="Smooth 180 deg Lead-In Arc",
                )
                lines.append(lead_in_cmd)
                total_feed_dist += math.pi * lead_radius

                # Full 360° helical revolutions moving up in Z
                curr_z_rev = lead_in_end_z
                for rev in range(1, num_revolutions + 1):
                    next_z_rev = curr_z_rev + pitch
                    helix_cmd = postprocessor.format_arc(
                        clockwise=not is_ccw,
                        x=lead_in_end_x,
                        y=lead_in_end_y,
                        z=next_z_rev,
                        i=-cut_radius,
                        j=0.0,
                        feed_rate=feed_rate_xy,
                        comment=f"Helical Pitch {rev}/{num_revolutions}",
                    )
                    lines.append(helix_cmd)
                    total_feed_dist += 2.0 * math.pi * cut_radius
                    curr_z_rev = next_z_rev

                # Tangential 180° semi-circular lead-out arc back to center (hx, hy)
                lead_out_end_z = curr_z_rev + (0.5 * pitch)
                lead_out_cmd = postprocessor.format_arc(
                    clockwise=not is_ccw,
                    x=hx,
                    y=hy,
                    z=lead_out_end_z,
                    i=-lead_radius,
                    j=0.0,
                    feed_rate=feed_rate_xy,
                    comment="Smooth 180 deg Lead-Out Arc to Center",
                )
                lines.append(lead_out_cmd)
                total_feed_dist += math.pi * lead_radius

                # Retract to safe Z in center
                lines.append(postprocessor.format_rapid(z=effective_retract_z))
                total_rapid_dist += abs(effective_retract_z - lead_out_end_z)

            else:  # top_to_bottom
                # Rapid to start Z above hole
                lines.append(postprocessor.format_rapid(z=start_z + 1.0))
                lines.append(postprocessor.format_linear(z=start_z, feed_rate=plunge_feed))

                # Lead-in from center at top
                lead_radius = cut_radius / 2.0
                lead_in_end_x = hx + cut_radius
                lead_in_end_y = hy
                lead_in_end_z = start_z - (0.5 * pitch)

                lead_in_cmd = postprocessor.format_arc(
                    clockwise=not is_ccw,
                    x=lead_in_end_x,
                    y=lead_in_end_y,
                    z=lead_in_end_z,
                    i=lead_radius,
                    j=0.0,
                    feed_rate=feed_rate_xy,
                    comment="Lead-In Arc",
                )
                lines.append(lead_in_cmd)
                total_feed_dist += math.pi * lead_radius

                # Helical revolutions ramping down
                curr_z_rev = lead_in_end_z
                for rev in range(1, num_revolutions + 1):
                    next_z_rev = curr_z_rev - pitch
                    helix_cmd = postprocessor.format_arc(
                        clockwise=not is_ccw,
                        x=lead_in_end_x,
                        y=lead_in_end_y,
                        z=next_z_rev,
                        i=-cut_radius,
                        j=0.0,
                        feed_rate=feed_rate_xy,
                        comment=f"Helical Pitch {rev}/{num_revolutions}",
                    )
                    lines.append(helix_cmd)
                    total_feed_dist += 2.0 * math.pi * cut_radius
                    curr_z_rev = next_z_rev

                # Lead-out back to center
                lead_out_end_z = curr_z_rev - (0.5 * pitch)
                lead_out_cmd = postprocessor.format_arc(
                    clockwise=not is_ccw,
                    x=hx,
                    y=hy,
                    z=lead_out_end_z,
                    i=-lead_radius,
                    j=0.0,
                    feed_rate=feed_rate_xy,
                    comment="Lead-Out Arc",
                )
                lines.append(lead_out_cmd)
                total_feed_dist += math.pi * lead_radius

                # Retract to safe Z in center
                lines.append(postprocessor.format_rapid(z=effective_retract_z))
                total_rapid_dist += abs(effective_retract_z - lead_out_end_z)

        lines.append("")
        current_x = hx
        current_y = hy
        current_z = effective_retract_z

    # 6. Program Footer / Park
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
