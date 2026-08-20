import math
from typing import List, Tuple, Optional
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope

ROUTER_DIAL_MAPS = {
    "dewalt_611": {
        1: 16000,
        2: 18200,
        3: 20400,
        4: 22600,
        5: 24800,
        6: 27000,
    },
    "makita_rt0701": {
        1: 10000,
        2: 12000,
        3: 17000,
        4: 22000,
        5: 27000,
        6: 30000,
    },
}


def compute_bolt_circle_holes(
    center_x: float,
    center_y: float,
    diameter: float,
    num_holes: int,
    start_angle_deg: float = 0.0,
    arc_span_deg: float = 360.0,
) -> List[Tuple[float, float]]:
    """
    Computes (X, Y) coordinates for a bolt circle / PCD pattern.
    """
    if num_holes < 1:
        raise ValueError("Number of holes must be at least 1.")
    if diameter <= 0:
        raise ValueError("Bolt circle diameter must be greater than zero.")

    radius = diameter / 2.0
    holes: List[Tuple[float, float]] = []

    if abs(arc_span_deg - 360.0) < 1e-5 or num_holes == 1:
        step_angle = 360.0 / num_holes
    else:
        step_angle = arc_span_deg / (num_holes - 1)

    for i in range(num_holes):
        angle_deg = start_angle_deg + (i * step_angle)
        rad = math.radians(angle_deg)
        x = center_x + radius * math.cos(rad)
        y = center_y + radius * math.sin(rad)
        holes.append((round(x, 4), round(y, 4)))

    return holes


def compute_grid_holes(
    origin_x: float,
    origin_y: float,
    num_x: int,
    num_y: int,
    spacing_x: float,
    spacing_y: float,
    angle_deg: float = 0.0,
) -> List[Tuple[float, float]]:
    """
    Computes (X, Y) coordinates for a matrix grid array of holes with serpentine rapid pathing.
    """
    if num_x < 1 or num_y < 1:
        raise ValueError("Grid columns (num_x) and rows (num_y) must be at least 1.")

    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    holes: List[Tuple[float, float]] = []

    for row in range(num_y):
        for col in range(num_x):
            # Serpentine / Zigzag ordering to optimize rapid traverse
            effective_col = col if row % 2 == 0 else (num_x - 1 - col)
            lx = effective_col * spacing_x
            ly = row * spacing_y

            gx = origin_x + (lx * cos_a - ly * sin_a)
            gy = origin_y + (lx * sin_a + ly * cos_a)
            holes.append((round(gx, 4), round(gy, 4)))

    return holes


def generate_straight_plunge(

    holes: List[Tuple[float, float]],
    target_depth_z: float,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    plunge_feed: float = 200.0,
    rapid_feed: float = 5000.0,
    spindle_speed: int = 16000,
    dwell_seconds: float = 0.0,
    spindle_dwell_seconds: float = 2.0,
    approach_clearance: float = 1.0,
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
    Pure Python G-Code Generator for Straight-Plunge Hole Drilling.
    
    Generates deterministic, dialect-compliant G-code for drilling a single hole or
    an array of holes, expanding linear motions for Grbl or using canned cycles when available.
    Supports manual trim routers (e.g. DeWalt DWP611 with dial settings) and VFD spindles.
    """
    if not holes:
        raise ValueError("At least one hole coordinate (x, y) must be provided.")

    if plunge_feed <= 0:
        raise ValueError("Plunge feed rate must be greater than zero.")

    if spindle_speed <= 0:
        raise ValueError("Spindle speed must be greater than zero.")

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    warnings: List[str] = []
    effective_spindle_speed = spindle_speed
    resolved_dial = router_dial

    # Router-specific dial mapping & RPM limits
    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if effective_spindle_speed < min_spindle_rpm:
            warnings.append(
                f"Requested speed ({effective_spindle_speed} RPM) is below {router_model.replace('_', ' ').title()} minimum speed ({min_spindle_rpm} RPM). Clamped to {min_spindle_rpm} RPM (Dial 1)."
            )
            effective_spindle_speed = min_spindle_rpm

        if resolved_dial is None:
            resolved_dial = min(dial_map.keys(), key=lambda d: abs(dial_map[d] - effective_spindle_speed))

    # Ensure target depth is lower than start_z
    final_target_z = target_depth_z
    if final_target_z >= start_z:
        # If passed as a positive depth magnitude (e.g. 5mm deep), convert to negative coordinate
        final_target_z = start_z - abs(target_depth_z)

    # Ensure retract plane is above start_z
    effective_retract_z = max(retract_z, start_z + approach_clearance)

    lines: List[str] = []

    # 1. Header block
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: Straight Plunge Drilling ({len(holes)} holes)",
        )
    )

    # 2. Tool information
    lines.extend(postprocessor.format_tool_comment(tool_number=tool_number, tool_name=tool_name))

    # 3. Spindle activation & spin-up
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

    # 4. Initial move to safe retract plane
    lines.append(postprocessor.format_rapid(z=effective_retract_z, comment="Safe Z clearance"))

    # Track motion for bounding box & runtime estimation
    all_x = [h[0] for h in holes]
    all_y = [h[1] for h in holes]
    if park_x is not None:
        all_x.append(park_x)
    if park_y is not None:
        all_y.append(park_y)

    bounds = BoundingBox(
        min_x=min(all_x),
        max_x=max(all_x),
        min_y=min(all_y),
        max_y=max(all_y),
        min_z=final_target_z,
        max_z=effective_retract_z,
    )

    # Validate work envelope if provided
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

    # 5. Drill Holes
    for i, (hx, hy) in enumerate(holes, start=1):
        lines.append(f"(--- Hole {i}/{len(holes)} at X{hx:.3f}, Y{hy:.3f} ---)")
        drill_block = postprocessor.format_straight_drill(
            x=hx,
            y=hy,
            start_z=start_z,
            target_depth_z=final_target_z,
            retract_z=effective_retract_z,
            plunge_feed=plunge_feed,
            dwell_seconds=dwell_seconds,
            approach_clearance=approach_clearance,
        )
        lines.extend(drill_block)
        lines.append("")

        # Calculate travel metrics for this hole
        xy_dist = math.hypot(hx - current_x, hy - current_y)
        approach_dist = abs(effective_retract_z - (start_z + approach_clearance))
        plunge_dist = abs((start_z + approach_clearance) - final_target_z)
        retract_dist = abs(effective_retract_z - final_target_z)

        total_rapid_dist += xy_dist + approach_dist + retract_dist
        total_feed_dist += plunge_dist
        total_dwell_time += dwell_seconds

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

    # Estimate runtime (seconds): rapid distance / rapid feed + feed distance / feed rate + dwell
    estimated_time = (
        (total_rapid_dist / rapid_feed * 60.0)
        + (total_feed_dist / plunge_feed * 60.0)
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


def generate_peck_drilling(
    holes: List[Tuple[float, float]],
    target_depth_z: float,
    peck_depth: float,
    peck_retract_type: str = "full_retract",  # "full_retract" (G83 chip clear) or "chip_break" (G73)
    start_z: float = 0.0,
    retract_z: float = 5.0,
    plunge_feed: float = 200.0,
    rapid_feed: float = 5000.0,
    spindle_speed: int = 16000,
    dwell_seconds: float = 0.0,
    spindle_dwell_seconds: float = 2.0,
    approach_clearance: float = 1.0,
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
    Pure Python G-Code Generator for Peck Drilling (Deep Hole Drilling).
    
    Generates deterministic, dialect-compliant G-code for deep hole peck drilling,
    expanding linear motions with chip clearance for Grbl, or using native G83/G73 canned cycles.
    """
    if not holes:
        raise ValueError("At least one hole coordinate (x, y) must be provided.")

    if plunge_feed <= 0:
        raise ValueError("Plunge feed rate must be greater than zero.")

    if spindle_speed <= 0:
        raise ValueError("Spindle speed must be greater than zero.")

    if peck_depth <= 0:
        raise ValueError("Peck depth (Q) must be greater than zero.")

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

    effective_retract_z = max(retract_z, start_z + approach_clearance)

    lines: List[str] = []

    # 1. Header block
    cycle_name = "Chip Breaking (G73)" if peck_retract_type == "chip_break" else "Deep Hole Chip Clearing (G83)"
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: Peck Drilling - {cycle_name} ({len(holes)} holes, Q={peck_depth:.2f}mm)",
        )
    )

    # 2. Tool information
    lines.extend(postprocessor.format_tool_comment(tool_number=tool_number, tool_name=tool_name))

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

    # 4. Initial move to safe retract plane
    lines.append(postprocessor.format_rapid(z=effective_retract_z, comment="Safe Z clearance"))

    # Bounds
    all_x = [h[0] for h in holes]
    all_y = [h[1] for h in holes]
    if park_x is not None:
        all_x.append(park_x)
    if park_y is not None:
        all_y.append(park_y)

    bounds = BoundingBox(
        min_x=min(all_x),
        max_x=max(all_x),
        min_y=min(all_y),
        max_y=max(all_y),
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

    total_hole_depth = abs(start_z - final_target_z)
    num_pecks = max(1, int(math.ceil(total_hole_depth / peck_depth)))

    # 5. Drill Holes
    for i, (hx, hy) in enumerate(holes, start=1):
        lines.append(f"(--- Peck Hole {i}/{len(holes)} at X{hx:.3f}, Y{hy:.3f} ---)")
        peck_block = postprocessor.format_peck_drill(
            x=hx,
            y=hy,
            start_z=start_z,
            target_depth_z=final_target_z,
            peck_depth=peck_depth,
            retract_z=effective_retract_z,
            plunge_feed=plunge_feed,
            dwell_seconds=dwell_seconds,
            approach_clearance=approach_clearance,
            peck_retract_type=peck_retract_type,
        )
        lines.extend(peck_block)
        lines.append("")

        xy_dist = math.hypot(hx - current_x, hy - current_y)
        total_rapid_dist += xy_dist + (num_pecks * 2 * total_hole_depth)
        total_feed_dist += total_hole_depth
        total_dwell_time += dwell_seconds

        current_x = hx
        current_y = hy
        current_z = effective_retract_z

    # 6. Footer
    effective_park_z = park_z if park_z is not None else effective_retract_z
    footer_lines = postprocessor.format_footer(
        park_z=effective_park_z, park_x=park_x, park_y=park_y
    )
    lines.extend(footer_lines)

    if park_x is not None and park_y is not None:
        total_rapid_dist += math.hypot(park_x - current_x, park_y - current_y)

    estimated_time = (
        (total_rapid_dist / rapid_feed * 60.0)
        + (total_feed_dist / plunge_feed * 60.0)
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

