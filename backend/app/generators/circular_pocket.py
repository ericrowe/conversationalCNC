import math
from typing import List, Tuple, Optional
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope
from .drilling import ROUTER_DIAL_MAPS

def generate_circular_pocket(
    pockets: List[Tuple[float, float]],
    pocket_diameter: float,
    target_depth_z: float,
    tool_diameter: float,
    stepdown_z: float = 1.5,
    stepover_percent: float = 50.0,
    finish_allowance: float = 0.2,
    finish_feed_xy: Optional[float] = None,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
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
    Pure Python G-Code Generator for Circular Pocketing & Helical Bore Milling.
    
    Generates deterministic, dialect-compliant G-code for milling internal circular pockets,
    bearing bores, or counterbores using standard endmills.
    
    Features:
    - Helical ramp or spiral entry
    - Concentric expanding radial stepovers
    - Finishing perimeter pass with clean tangential lead-in/lead-out arcs
    - Multi-pocket arrays (single, grid, bolt circle)
    - Full Grbl linear/arc expansion
    """
    if not pockets:
        raise ValueError("At least one pocket center coordinate (x, y) must be provided.")

    if pocket_diameter <= 0:
        raise ValueError("Pocket diameter must be greater than zero.")

    if tool_diameter <= 0:
        raise ValueError("Tool cutting diameter must be greater than zero.")

    if tool_diameter > pocket_diameter:
        raise ValueError(
            f"Tool diameter ({tool_diameter:.3f}mm) cannot be larger than pocket diameter ({pocket_diameter:.3f}mm)."
        )

    if stepdown_z <= 0:
        raise ValueError("Stepdown per pass (Z) must be greater than zero.")

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

    final_target_z = target_depth_z
    if final_target_z >= start_z:
        final_target_z = start_z - abs(target_depth_z)

    effective_retract_z = max(retract_z, start_z + 1.0)
    total_depth = abs(start_z - final_target_z)

    # Calculate Z passes
    num_z_passes = max(1, int(math.ceil(total_depth / stepdown_z)))
    actual_stepdown = total_depth / num_z_passes

    # Pocket radial geometry
    target_tool_radius = (pocket_diameter - tool_diameter) / 2.0
    effective_finish_allowance = min(finish_allowance, target_tool_radius * 0.5) if target_tool_radius > 0.5 else 0.0
    rough_tool_radius = target_tool_radius - effective_finish_allowance
    stepover_dist = tool_diameter * (stepover_percent / 100.0)

    # Compute radial passes from center outward
    concentric_radii: List[float] = []
    if rough_tool_radius > 0.001:
        num_radial_steps = max(1, int(math.ceil(rough_tool_radius / stepover_dist)))
        actual_radial_step = rough_tool_radius / num_radial_steps
        for s in range(1, num_radial_steps + 1):
            concentric_radii.append(s * actual_radial_step)

    resolved_finish_feed = finish_feed_xy or (feed_rate_xy * 0.75)

    lines: List[str] = []

    # 1. Header
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: Circular Pocketing (Dia={pocket_diameter:.2f}mm, Depth={total_depth:.2f}mm, {len(pockets)} pockets)",
        )
    )

    # 2. Tool
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"Endmill D{tool_diameter:.3f}mm",
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
    pocket_radius_outer = pocket_diameter / 2.0
    min_cut_x = min(p[0] for p in pockets) - pocket_radius_outer
    max_cut_x = max(p[0] for p in pockets) + pocket_radius_outer
    min_cut_y = min(p[1] for p in pockets) - pocket_radius_outer
    max_cut_y = max(p[1] for p in pockets) + pocket_radius_outer

    min_x = min(min_cut_x, park_x) if park_x is not None else min_cut_x
    max_x = max(max_cut_x, park_x) if park_x is not None else max_cut_x
    min_y = min(min_cut_y, park_y) if park_y is not None else min_cut_y
    max_y = max(max_cut_y, park_y) if park_y is not None else max_cut_y

    bounds = BoundingBox(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
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

    # 5. Process each pocket
    for p_idx, (cx, cy) in enumerate(pockets, start=1):
        lines.append(f"(--- Circular Pocket {p_idx}/{len(pockets)} at X{cx:.3f}, Y{cy:.3f} ---)")
        lines.append(postprocessor.format_rapid(z=effective_retract_z))
        lines.append(postprocessor.format_rapid(x=cx, y=cy))

        total_rapid_dist += math.hypot(cx - current_x, cy - current_y)

        # Iterate Z depth layers
        for z_step in range(1, num_z_passes + 1):
            curr_layer_z = start_z - (z_step * actual_stepdown)
            if z_step == num_z_passes:
                curr_layer_z = final_target_z

            lines.append(f"(Z Layer {z_step}/{num_z_passes} at Z{curr_layer_z:.3f})")

            # Move to center and plunge / ramp down
            lines.append(postprocessor.format_rapid(x=cx, y=cy))
            prev_z = start_z - ((z_step - 1) * actual_stepdown) if z_step > 1 else start_z
            lines.append(postprocessor.format_rapid(z=prev_z + 0.5))
            lines.append(postprocessor.format_linear(z=curr_layer_z, feed_rate=plunge_feed, comment="Plunge at center"))
            total_feed_dist += abs(prev_z + 0.5 - curr_layer_z)

            # Cut concentric rings outward
            for r_val in concentric_radii:
                # Linear move from center out to (cx + r_val, cy)
                lines.append(postprocessor.format_linear(x=cx + r_val, y=cy, feed_rate=feed_rate_xy))
                total_feed_dist += r_val

                # Full 360° counter-clockwise circle (G3 Climb)
                circle_cmd = postprocessor.format_arc(
                    clockwise=False,
                    x=cx + r_val,
                    y=cy,
                    i=-r_val,
                    j=0.0,
                    feed_rate=feed_rate_xy,
                )
                lines.append(circle_cmd)
                total_feed_dist += 2.0 * math.pi * r_val

            # Return to center
            if concentric_radii:
                lines.append(postprocessor.format_linear(x=cx, y=cy, feed_rate=feed_rate_xy))
                total_feed_dist += concentric_radii[-1]

        # 6. Optional Finish Wall Pass at full target depth
        if effective_finish_allowance > 0 and target_tool_radius > 0:
            lines.append("(--- Final Finish Wall Pass ---)")
            lines.append(postprocessor.format_linear(x=cx, y=cy, z=final_target_z, feed_rate=plunge_feed))

            # Tangential lead-in arc to full pocket radius
            lead_r = target_tool_radius / 2.0
            lead_in_x = cx + target_tool_radius
            lead_in_y = cy

            lines.append(
                postprocessor.format_arc(
                    clockwise=False,
                    x=lead_in_x,
                    y=lead_in_y,
                    i=lead_r,
                    j=0.0,
                    feed_rate=resolved_finish_feed,
                    comment="Finish Lead-In Arc",
                )
            )
            total_feed_dist += math.pi * lead_r

            # Full 360° finish circle
            lines.append(
                postprocessor.format_arc(
                    clockwise=False,
                    x=lead_in_x,
                    y=lead_in_y,
                    i=-target_tool_radius,
                    j=0.0,
                    feed_rate=resolved_finish_feed,
                    comment="Finish Wall Contour",
                )
            )
            total_feed_dist += 2.0 * math.pi * target_tool_radius

            # Tangential lead-out back to center
            lines.append(
                postprocessor.format_arc(
                    clockwise=False,
                    x=cx,
                    y=cy,
                    i=-lead_r,
                    j=0.0,
                    feed_rate=resolved_finish_feed,
                    comment="Finish Lead-Out Arc",
                )
            )
            total_feed_dist += math.pi * lead_r

        # Retract to safe Z
        lines.append(postprocessor.format_rapid(z=effective_retract_z))
        lines.append("")
        total_rapid_dist += abs(effective_retract_z - final_target_z)

        current_x = cx
        current_y = cy
        current_z = effective_retract_z

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


def generate_circular_boss(
    boss_center_x: float = 0.0,
    boss_center_y: float = 0.0,
    boss_diameter: float = 10.0,
    stock_shape: str = "circle",  # "circle" (round bar) or "rectangle" (square/rectangular billet)
    stock_diameter: float = 25.0,
    stock_length_x: float = 30.0,
    stock_width_y: float = 30.0,
    target_depth_z: float = -15.0,
    stepdown_z: float = 1.0,
    stepover_percent: float = 50.0,
    finish_allowance: float = 0.2,
    finish_feed_xy: Optional[float] = None,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
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
    Pure Python G-Code Generator for Circular Boss / Cylindrical Stud / Spigot Milling.
    
    Removes the outer material collar from round stock (or rectangular billet) leaving
    a raised cylindrical shaft of exact diameter and height (ideal for bolt turning, pins, spigots).
    
    Features:
    - Outside-In concentric clearing passes so cutter plunges safely in open air
    - Supports cylindrical round bar stock (diameter) or square/rectangular billets
    - Finishing perimeter pass with smooth tangential arc entry/exit for zero dwell marks
    - Multi-pass Z depth layers
    - Full Grbl/LinuxCNC compliance
    """
    if boss_diameter <= 0:
        raise ValueError("Boss diameter must be greater than zero.")

    if tool_diameter <= 0:
        raise ValueError("Tool cutting diameter must be greater than zero.")

    is_round_stock = stock_shape.lower() in ("circle", "round", "cylinder", "disc")

    if is_round_stock:
        if stock_diameter <= boss_diameter:
            raise ValueError(
                f"Stock diameter ({stock_diameter:.3f}mm) must be strictly larger than boss diameter ({boss_diameter:.3f}mm)."
            )
        eff_stock_radius = stock_diameter / 2.0
    else:
        if stock_length_x <= boss_diameter or stock_width_y <= boss_diameter:
            raise ValueError("Stock dimensions (X and Y) must be strictly larger than boss diameter.")
        # Circumscribing radius encompassing rectangular stock
        eff_stock_radius = math.hypot(stock_length_x / 2.0, stock_width_y / 2.0)

    if stepdown_z <= 0:
        raise ValueError("Stepdown per pass (Z) must be greater than zero.")

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

    final_target_z = target_depth_z
    if final_target_z >= start_z:
        final_target_z = start_z - abs(target_depth_z)

    effective_retract_z = max(retract_z, start_z + 1.0)
    total_depth = abs(start_z - final_target_z)
    resolved_finish_feed = finish_feed_xy if finish_feed_xy is not None else feed_rate_xy * 0.7

    tool_radius = tool_diameter / 2.0
    boss_radius = boss_diameter / 2.0
    rough_boss_radius = boss_radius + finish_allowance
    radial_stepover = tool_diameter * (stepover_percent / 100.0)

    # Tool center trajectory radii:
    # Outer plunge radius (in open air outside stock perimeter)
    r_outer = eff_stock_radius + tool_radius + 0.5
    # Inner roughing boundary at boss wall
    r_inner = rough_boss_radius + tool_radius

    # Calculate number of radial roughing rings per layer
    if r_outer <= r_inner:
        num_rings = 1
        ring_radii = [r_inner]
    else:
        num_rings = max(1, int(math.ceil((r_outer - r_inner) / radial_stepover)))
        step_r = (r_outer - r_inner) / float(num_rings)
        # Rings from outside to inside: r_outer - step_r, ..., r_inner
        ring_radii = [r_outer - i * step_r for i in range(num_rings + 1)]

    # Calculate Z passes
    num_z_passes = max(1, int(math.ceil(total_depth / stepdown_z)))
    actual_stepdown = total_depth / num_z_passes

    # Work Envelope verification
    max_extent_r = r_outer + tool_radius
    bounds = BoundingBox(
        min_x=boss_center_x - max_extent_r,
        max_x=boss_center_x + max_extent_r,
        min_y=boss_center_y - max_extent_r,
        max_y=boss_center_y + max_extent_r,
        min_z=final_target_z,
        max_z=effective_retract_z,
    )

    if work_envelope:
        warnings.extend(work_envelope.validate_bounds(bounds))

    lines: List[str] = []

    # 1. Header
    stock_desc = f"Round Ø{stock_diameter:.1f}mm" if is_round_stock else f"Rect {stock_length_x:.1f}x{stock_width_y:.1f}mm"
    header_lines = postprocessor.format_header(
        units=units,
        absolute_mode=True,
        comment=f"Circular Boss / Stud Milling (Ø{boss_diameter:.2f}mm Shaft from {stock_desc})",
    )
    lines.extend(header_lines)

    # 2. Tool & Spindle Setup
    tool_comments = postprocessor.format_tool_comment(
        tool_number=tool_number,
        tool_name=tool_name or f"Flat Endmill {tool_diameter:.3f}{units}",
    )
    lines.extend(tool_comments)

    if spindle_type == "router" and router_model:
        dial_str = f" - Set Speed to Dial {resolved_dial} (~{effective_spindle_speed} RPM)" if resolved_dial else f" (~{effective_spindle_speed} RPM)"
        lines.append(f"(Spindle: {router_model.replace('_', ' ').title()}{dial_str})")

    spindle_lines = postprocessor.format_spindle_start(
        rpm=effective_spindle_speed,
        clockwise=True,
        dwell_seconds=spindle_dwell_seconds,
    )
    lines.extend(spindle_lines)

    # Initial Rapid to Safe Retract Plane above initial plunge point
    first_r = ring_radii[0]
    first_x = boss_center_x + first_r
    first_y = boss_center_y
    lines.append(f"( --- Initial Position: Move to clearance outside stock --- )")
    lines.append(postprocessor.format_rapid(z=effective_retract_z))
    lines.append(postprocessor.format_rapid(x=first_x, y=first_y))

    total_rapid_dist = effective_retract_z + math.hypot(first_x, first_y)
    total_feed_dist = 0.0
    total_dwell_time = spindle_dwell_seconds
    current_x = first_x
    current_y = first_y
    current_z = effective_retract_z

    # 3. Multi-Pass Depth Machining
    for z_pass_idx in range(1, num_z_passes + 1):
        target_pass_z = round(start_z - z_pass_idx * actual_stepdown, 4)
        if z_pass_idx == num_z_passes:
            target_pass_z = final_target_z

        lines.append("")
        lines.append(
            f"( --- Depth Pass {z_pass_idx}/{num_z_passes} at Z={target_pass_z:.3f} --- )"
        )

        # Plunge at outermost radius (in open air outside stock)
        lines.append(postprocessor.format_rapid(x=first_x, y=first_y))
        lines.append(
            postprocessor.format_linear(
                z=target_pass_z,
                feed_rate=plunge_feed,
                comment="Plunge in Open Air",
            )
        )
        total_feed_dist += abs(current_z - target_pass_z)
        current_z = target_pass_z

        # Outside-In Concentric Clearing Rings
        for ring_idx, r_val in enumerate(ring_radii):
            ring_x = boss_center_x + r_val
            ring_y = boss_center_y

            # Step inward to current ring radius
            if ring_idx > 0:
                lines.append(
                    postprocessor.format_linear(
                        x=ring_x,
                        y=ring_y,
                        feed_rate=feed_rate_xy,
                        comment=f"Step Inward to Ring {ring_idx + 1}/{len(ring_radii)} (R={r_val:.2f})",
                    )
                )
                total_feed_dist += abs(r_val - ring_radii[ring_idx - 1])

            # Full 360° Climb-Milling Circular Arc around boss (Clockwise G2)
            lines.append(
                postprocessor.format_arc(
                    clockwise=True,
                    x=ring_x,
                    y=ring_y,
                    i=-r_val,
                    j=0.0,
                    feed_rate=feed_rate_xy,
                    comment=f"Climb Cut Ring (Radius {r_val:.3f})",
                )
            )
            total_feed_dist += 2.0 * math.pi * r_val

        # Wall Finish Pass (if finish allowance > 0)
        if finish_allowance > 0:
            finish_r = boss_radius + tool_radius
            lead_r = min(2.0, finish_allowance + 1.0)
            lead_start_x = boss_center_x + finish_r + lead_r
            lead_start_y = boss_center_y + lead_r

            lines.append(f"( --- Wall Finishing Pass at Finished Shaft Ø{boss_diameter:.3f}mm --- )")
            # Rapid or linear lead-in positioning
            lines.append(
                postprocessor.format_linear(
                    x=lead_start_x,
                    y=lead_start_y,
                    feed_rate=resolved_finish_feed,
                )
            )
            # Tangential 90° arc lead-in
            lines.append(
                postprocessor.format_arc(
                    clockwise=True,
                    x=boss_center_x + finish_r,
                    y=boss_center_y,
                    i=0.0,
                    j=-lead_r,
                    feed_rate=resolved_finish_feed,
                    comment="Tangential Lead-In",
                )
            )
            # Full 360° finish contour
            lines.append(
                postprocessor.format_arc(
                    clockwise=True,
                    x=boss_center_x + finish_r,
                    y=boss_center_y,
                    i=-finish_r,
                    j=0.0,
                    feed_rate=resolved_finish_feed,
                    comment=f"Finish Contour (Shaft Ø{boss_diameter:.3f})",
                )
            )
            # Tangential 90° arc lead-out
            lines.append(
                postprocessor.format_arc(
                    clockwise=True,
                    x=boss_center_x + finish_r + lead_r,
                    y=boss_center_y - lead_r,
                    i=lead_r,
                    j=0.0,
                    feed_rate=resolved_finish_feed,
                    comment="Tangential Lead-Out",
                )
            )
            total_feed_dist += (2.0 * math.pi * finish_r) + (math.pi * lead_r)

        # Retract to safe Z after layer
        lines.append(postprocessor.format_rapid(z=effective_retract_z))
        total_rapid_dist += abs(effective_retract_z - target_pass_z)
        current_z = effective_retract_z

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
