"""
Linear and Arc Slotting G-Code Generator.
Supports:
- Straight linear slots (start to end coordinate with slot width)
- Circular arc slots (center, radius, start angle, arc span, width)
- Depth stepdowns with safe retracts
- Full slotting (tool diameter == slot width), wider slot profiling, and adaptive trochoidal clearing
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


def _r4(val: float) -> float:
    return round(val, 4)


def _format_arc_ij(
    motion: str,
    cur_x: float,
    cur_y: float,
    end_x: float,
    end_y: float,
    center_x: float,
    center_y: float,
    feed: Optional[float] = None,
    z: Optional[float] = None,
    full_circle: bool = False,
) -> Optional[str]:
    """
    Formats a G2/G3 arc command with 4-decimal coordinates and I/J computed
    from the rounded start coordinate so |r_start - r_end| <= 0.002 mm.
    Skips degenerate partial arcs with chord < 0.001 mm.
    """
    sx, sy = _r4(cur_x), _r4(cur_y)
    ex, ey = _r4(end_x), _r4(end_y)
    if not full_circle and math.hypot(ex - sx, ey - sy) < 0.001:
        return None
    i_off = _r4(center_x - sx)
    j_off = _r4(center_y - sy)
    if math.hypot(i_off, j_off) < 0.001:
        return None
    parts = [f"{motion} X{ex:.4f} Y{ey:.4f} I{i_off:.4f} J{j_off:.4f}"]
    if z is not None:
        parts.append(f"Z{_r4(z):.4f}")
    if feed is not None:
        parts.append(f"F{feed:.1f}")
    return " ".join(parts)


def _validate_trochoidal_params(
    cutting_strategy: str,
    trochoidal_stepover_pct: float,
    slot_width: float,
    tool_diameter: float,
) -> None:
    if cutting_strategy not in ("conventional", "trochoidal"):
        raise ValueError(f"Unsupported cutting_strategy '{cutting_strategy}'. Must be 'conventional' or 'trochoidal'.")
    if not (5.0 <= trochoidal_stepover_pct <= 40.0):
        raise ValueError(
            f"trochoidal_stepover_pct ({trochoidal_stepover_pct}%) must be between 5.0% and 40.0%."
        )
    if cutting_strategy == "trochoidal" and slot_width < tool_diameter * 1.05:
        raise ValueError(
            "Trochoidal clearing requires slot_width >= 1.05 * tool_diameter "
            f"(got slot_width={slot_width:.3f}mm, tool_diameter={tool_diameter:.3f}mm)."
        )


def _resolve_router_dial(
    spindle_type: str,
    router_model: Optional[str],
    router_dial: Optional[int],
    spindle_speed: int,
) -> Optional[int]:
    resolved_dial = router_dial
    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if resolved_dial is None:
            resolved_dial = 1
            for d, rpm in dial_map.items():
                if spindle_speed >= rpm:
                    resolved_dial = d
    return resolved_dial


def _emit_trochoidal_entry(
    lines: List[str],
    cx: float,
    cy: float,
    ux: float,
    uy: float,
    r_loop: float,
    tool_diameter: float,
    span_length: float,
    cur_z: float,
    target_pass_z: float,
    feed_rate_xy: float,
    plunge_feed: float,
) -> None:
    """
    Enters to target_pass_z at loop center (cx, cy) without a 100%-engagement vertical plunge.
    Uses a helical Z-ramp when r_loop >= 0.25mm, otherwise a linear Z-ramp along the centerline.
    """
    lines.append(f"G0 X{_r4(cx):.4f} Y{_r4(cy):.4f}")
    start_ramp_z = cur_z + 1.0
    lines.append(f"G0 Z{_r4(start_ramp_z):.4f}")

    if r_loop >= 0.25:
        r_helix = min(r_loop, tool_diameter * 0.4)
        depth_needed = abs(start_ramp_z - target_pass_z)
        pitch_per_turn = max(0.25, 2.0 * math.pi * r_helix * math.tan(math.radians(3.0)))
        turns = max(1, math.ceil(depth_needed / pitch_per_turn))
        z_step = depth_needed / turns

        hx = cx + ux * r_helix
        hy = cy + uy * r_helix
        lines.append(f"G1 X{_r4(hx):.4f} Y{_r4(hy):.4f} F{plunge_feed:.1f}")
        ramp_z = start_ramp_z
        for _ in range(turns):
            ramp_z = max(target_pass_z, ramp_z - z_step)
            arc = _format_arc_ij("G3", hx, hy, hx, hy, cx, cy, z=ramp_z, full_circle=True)
            if arc:
                lines.append(arc)
        # Flat cleanup circle at target Z
        flat = _format_arc_ij("G3", hx, hy, hx, hy, cx, cy, feed=feed_rate_xy, full_circle=True)
        if flat:
            lines.append(flat)
        lines.append(f"G1 X{_r4(cx):.4f} Y{_r4(cy):.4f} F{feed_rate_xy:.1f}")
    else:
        ramp_dist = min(span_length, max(1.0, tool_diameter * 0.5))
        rx = cx + ux * ramp_dist
        ry = cy + uy * ramp_dist
        lines.append(f"G1 X{_r4(rx):.4f} Y{_r4(ry):.4f} Z{_r4(target_pass_z):.4f} F{plunge_feed:.1f}")
        lines.append(f"G1 X{_r4(cx):.4f} Y{_r4(cy):.4f} F{feed_rate_xy:.1f}")


def emit_linear_trochoidal_pass(
    lines: List[str],
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    slot_width: float,
    tool_diameter: float,
    trochoidal_stepover_pct: float,
    cur_z: float,
    target_pass_z: float,
    feed_rate_xy: float,
    plunge_feed: float,
    include_entry: bool = True,
) -> None:
    """
    Emits one Z-level trochoidal clearing pass + CCW G3 perimeter cleanup pass
    for a straight slot from (start_x, start_y) to (end_x, end_y).
    Shared by generate_linear_slot() and generate_rectangular_pocket().
    """
    dx = end_x - start_x
    dy = end_y - start_y
    slot_length = math.hypot(dx, dy)
    ux = dx / slot_length
    uy = dy / slot_length
    lx, ly = -uy, ux  # Left perpendicular unit vector
    rx, ry = uy, -ux  # Right perpendicular unit vector

    r_loop = (slot_width - tool_diameter) / 2.0
    pitch = tool_diameter * (trochoidal_stepover_pct / 100.0)
    num_steps = max(1, math.ceil(slot_length / pitch))
    centers = [
        (start_x + (k / float(num_steps)) * dx, start_y + (k / float(num_steps)) * dy)
        for k in range(num_steps + 1)
    ]

    if include_entry:
        _emit_trochoidal_entry(
            lines=lines,
            cx=centers[0][0],
            cy=centers[0][1],
            ux=ux,
            uy=uy,
            r_loop=r_loop,
            tool_diameter=tool_diameter,
            span_length=slot_length,
            cur_z=cur_z,
            target_pass_z=target_pass_z,
            feed_rate_xy=feed_rate_xy,
            plunge_feed=plunge_feed,
        )

    # Advancing G3 climb-milling circular loops with inward centerline retract/advance
    for idx, (cx, cy) in enumerate(centers):
        px = cx - ux * r_loop
        py = cy - uy * r_loop
        lines.append(f"G1 X{_r4(px):.4f} Y{_r4(py):.4f} F{feed_rate_xy:.1f}")
        loop_cmd = _format_arc_ij("G3", px, py, px, py, cx, cy, feed=feed_rate_xy, full_circle=True)
        if loop_cmd:
            lines.append(loop_cmd)
        lines.append(f"G1 X{_r4(cx):.4f} Y{_r4(cy):.4f} F{feed_rate_xy:.1f}")
        if idx + 1 < len(centers):
            nx, ny = centers[idx + 1]
            lines.append(f"G1 X{_r4(nx):.4f} Y{_r4(ny):.4f} F{feed_rate_xy:.1f}")

    # Continuous CCW (G3) perimeter cleanup pass along side walls and semicircular end caps
    end_left_x, end_left_y = end_x + lx * r_loop, end_y + ly * r_loop
    start_left_x, start_left_y = start_x + lx * r_loop, start_y + ly * r_loop
    start_right_x, start_right_y = start_x + rx * r_loop, start_y + ry * r_loop
    end_right_x, end_right_y = end_x + rx * r_loop, end_y + ry * r_loop

    lines.append(f"G1 X{_r4(end_left_x):.4f} Y{_r4(end_left_y):.4f} F{feed_rate_xy:.1f}")
    lines.append(f"G1 X{_r4(start_left_x):.4f} Y{_r4(start_left_y):.4f} F{feed_rate_xy:.1f}")
    cap_start = _format_arc_ij(
        "G3", start_left_x, start_left_y, start_right_x, start_right_y, start_x, start_y, feed=feed_rate_xy
    )
    if cap_start:
        lines.append(cap_start)
    lines.append(f"G1 X{_r4(end_right_x):.4f} Y{_r4(end_right_y):.4f} F{feed_rate_xy:.1f}")
    cap_end = _format_arc_ij(
        "G3", end_right_x, end_right_y, end_left_x, end_left_y, end_x, end_y, feed=feed_rate_xy
    )
    if cap_end:
        lines.append(cap_end)
    lines.append(f"G1 X{_r4(end_x):.4f} Y{_r4(end_y):.4f} F{feed_rate_xy:.1f}")


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
    rapid_feed: Optional[float] = None,
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
    cutting_strategy: str = "conventional",
    trochoidal_stepover_pct: float = 15.0,
    require_pause: bool = True,
) -> GCodeProgram:
    """
    Generates G-code for a straight linear slot (conventional or trochoidal).
    """
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be greater than zero.")
    if slot_width < tool_diameter - 1e-4:
        raise ValueError(f"Slot width ({slot_width}mm) cannot be smaller than tool diameter ({tool_diameter}mm).")

    slot_length = math.hypot(end_x - start_x, end_y - start_y)
    if slot_length < 0.001:
        raise ValueError("Slot start and end points must be distinct.")

    _validate_trochoidal_params(cutting_strategy, trochoidal_stepover_pct, slot_width, tool_diameter)

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    actual_target_depth = -abs(target_depth_z)
    total_depth = abs(start_z - actual_target_depth)
    num_passes = math.ceil(total_depth / stepdown_z)
    z_step = total_depth / num_passes

    # Compute bounding box (preserve exact conventional corner_pts bounds for backward compatibility)
    half_w = slot_width / 2.0
    dx = end_x - start_x
    dy = end_y - start_y
    angle = math.atan2(dy, dx)
    perp_angle = angle + math.pi / 2.0

    ox = half_w * math.cos(perp_angle)
    oy = half_w * math.sin(perp_angle)

    if cutting_strategy == "trochoidal":
        # Capsule bounds include semicircular end-caps of radius half_w
        min_x = min(start_x, end_x) - half_w
        max_x = max(start_x, end_x) + half_w
        min_y = min(start_y, end_y) - half_w
        max_y = max(start_y, end_y) + half_w
    else:
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

    bounds = BoundingBox(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        min_z=actual_target_depth,
        max_z=retract_z,
    )

    warnings: List[str] = []
    if work_envelope:
        warnings.extend(work_envelope.validate_bounds(bounds))

    resolved_dial = _resolve_router_dial(spindle_type, router_model, router_dial, spindle_speed)

    lines: List[str] = []
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=(
                f"Operation: Linear Slot [{cutting_strategy}] "
                f"({slot_length:.1f}mm length, {slot_width:.2f}mm width, Depth={actual_target_depth:.2f}mm)"
            ),
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

    excess_width = slot_width - tool_diameter
    num_side_offsets = 1 if excess_width > 0.05 else 0

    current_z = start_z
    for p_idx in range(1, num_passes + 1):
        target_pass_z = round(start_z - (p_idx * z_step), 4)
        lines.append(f"\n( --- Pass {p_idx}/{num_passes} at Z = {target_pass_z:.3f} mm --- )")

        if cutting_strategy == "trochoidal":
            emit_linear_trochoidal_pass(
                lines=lines,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                slot_width=slot_width,
                tool_diameter=tool_diameter,
                trochoidal_stepover_pct=trochoidal_stepover_pct,
                cur_z=current_z,
                target_pass_z=target_pass_z,
                feed_rate_xy=feed_rate_xy,
                plunge_feed=plunge_feed,
                include_entry=True,
            )
        elif num_side_offsets == 0:
            lines.append(f"G0 X{start_x:.3f} Y{start_y:.3f}")
            lines.append(f"G0 Z{(current_z + 1.0):.3f}")
            lines.append(f"G1 Z{target_pass_z:.3f} F{plunge_feed:.1f}")
            lines.append(f"G1 X{end_x:.3f} Y{end_y:.3f} F{feed_rate_xy:.1f}")
        else:
            offset_dist = excess_width / 2.0
            side_ox = offset_dist * math.cos(perp_angle)
            side_oy = offset_dist * math.sin(perp_angle)

            lines.append(f"G0 X{start_x:.3f} Y{start_y:.3f}")
            lines.append(f"G0 Z{(current_z + 1.0):.3f}")
            lines.append(f"G1 Z{target_pass_z:.3f} F{plunge_feed:.1f}")
            lines.append(f"G1 X{end_x:.3f} Y{end_y:.3f} F{feed_rate_xy:.1f}")

            lines.append(f"G1 X{(end_x + side_ox):.3f} Y{(end_y + side_oy):.3f}")
            lines.append(f"G1 X{(start_x + side_ox):.3f} Y{(start_y + side_oy):.3f}")

            lines.append(f"G1 X{(start_x - side_ox):.3f} Y{(start_y - side_oy):.3f}")
            lines.append(f"G1 X{(end_x - side_ox):.3f} Y{(end_y - side_oy):.3f}")

        lines.append(f"G0 Z{retract_z:.3f}")
        current_z = target_pass_z

    lines.extend(
        postprocessor.format_footer(
            park_x=park_x,
            park_y=park_y,
            park_z=park_z if park_z is not None else retract_z,
        )
    )
    gcode_text = "\n".join(lines)

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=round(num_passes * (12.0 if cutting_strategy == "trochoidal" else 6.0), 1),
        warnings=warnings,
    )


def generate_arc_slot(
    center_x: float,
    center_y: float,
    radius: float,
    start_angle_deg: float,
    end_angle_deg: float,
    slot_width: float,
    target_depth_z: float = -3.0,
    stepdown_z: float = 1.0,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 200.0,
    rapid_feed: Optional[float] = None,
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
    cutting_strategy: str = "conventional",
    trochoidal_stepover_pct: float = 15.0,
    require_pause: bool = True,
) -> GCodeProgram:
    """
    Generates G-code for a circular arc slot (conventional or trochoidal).
    """
    if tool_diameter <= 0:
        raise ValueError("Tool diameter must be greater than zero.")
    if radius <= 0:
        raise ValueError("Arc slot radius must be greater than zero.")
    if slot_width < tool_diameter - 1e-4:
        raise ValueError(f"Slot width ({slot_width}mm) cannot be smaller than tool diameter ({tool_diameter}mm).")
    if abs(end_angle_deg - start_angle_deg) < 0.01:
        raise ValueError("Arc slot start_angle_deg and end_angle_deg must be distinct.")

    _validate_trochoidal_params(cutting_strategy, trochoidal_stepover_pct, slot_width, tool_diameter)

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    actual_target_depth = -abs(target_depth_z)
    total_depth = abs(start_z - actual_target_depth)
    num_passes = math.ceil(total_depth / stepdown_z)
    z_step = total_depth / num_passes

    a0 = math.radians(start_angle_deg)
    a1 = math.radians(end_angle_deg)
    sweep = a1 - a0
    is_ccw = sweep >= 0
    arc_motion = "G3" if is_ccw else "G2"
    rev_arc_motion = "G2" if is_ccw else "G3"

    half_w = slot_width / 2.0
    r_loop = max(0.0, (slot_width - tool_diameter) / 2.0)

    # Sample centerline arc + half_w for tight bounding box
    sample_angles = [a0 + (k / 64.0) * sweep for k in range(65)]
    xs = [center_x + radius * math.cos(a) for a in sample_angles]
    ys = [center_y + radius * math.sin(a) for a in sample_angles]
    bounds = BoundingBox(
        min_x=min(xs) - half_w,
        max_x=max(xs) + half_w,
        min_y=min(ys) - half_w,
        max_y=max(ys) + half_w,
        min_z=actual_target_depth,
        max_z=retract_z,
    )

    warnings: List[str] = []
    if work_envelope:
        warnings.extend(work_envelope.validate_bounds(bounds))

    resolved_dial = _resolve_router_dial(spindle_type, router_model, router_dial, spindle_speed)

    lines: List[str] = []
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=(
                f"Operation: Arc Slot [{cutting_strategy}] "
                f"(R={radius:.2f}mm, {start_angle_deg:.1f}->{end_angle_deg:.1f}deg, W={slot_width:.2f}mm)"
            ),
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

    sx = center_x + radius * math.cos(a0)
    sy = center_y + radius * math.sin(a0)
    ex = center_x + radius * math.cos(a1)
    ey = center_y + radius * math.sin(a1)

    current_z = start_z
    for p_idx in range(1, num_passes + 1):
        target_pass_z = round(start_z - (p_idx * z_step), 4)
        lines.append(f"\n( --- Pass {p_idx}/{num_passes} at Z = {target_pass_z:.3f} mm --- )")

        if cutting_strategy == "trochoidal":
            # Outer-wall angular pitch scaling so outer wall engagement <= trochoidal_stepover_pct
            pitch_outer = tool_diameter * (trochoidal_stepover_pct / 100.0)
            pitch_center = pitch_outer * (radius / (radius + r_loop))
            arc_len = radius * abs(sweep)
            num_steps = max(1, math.ceil(arc_len / pitch_center))
            angles = [a0 + (k / float(num_steps)) * sweep for k in range(num_steps + 1)]

            # Tangent unit vector at start angle
            dir_sign = 1.0 if is_ccw else -1.0
            ux0 = -dir_sign * math.sin(a0)
            uy0 = dir_sign * math.cos(a0)
            _emit_trochoidal_entry(
                lines=lines,
                cx=sx,
                cy=sy,
                ux=ux0,
                uy=uy0,
                r_loop=r_loop,
                tool_diameter=tool_diameter,
                span_length=arc_len,
                cur_z=current_z,
                target_pass_z=target_pass_z,
                feed_rate_xy=feed_rate_xy,
                plunge_feed=plunge_feed,
            )

            for idx, ang in enumerate(angles):
                cx = center_x + radius * math.cos(ang)
                cy = center_y + radius * math.sin(ang)
                ux = -dir_sign * math.sin(ang)
                uy = dir_sign * math.cos(ang)
                px = cx - ux * r_loop
                py = cy - uy * r_loop
                lines.append(f"G1 X{_r4(px):.4f} Y{_r4(py):.4f} F{feed_rate_xy:.1f}")
                loop_cmd = _format_arc_ij("G3", px, py, px, py, cx, cy, feed=feed_rate_xy, full_circle=True)
                if loop_cmd:
                    lines.append(loop_cmd)
                lines.append(f"G1 X{_r4(cx):.4f} Y{_r4(cy):.4f} F{feed_rate_xy:.1f}")
                if idx + 1 < len(angles):
                    n_ang = angles[idx + 1]
                    nx = center_x + radius * math.cos(n_ang)
                    ny = center_y + radius * math.sin(n_ang)
                    step_arc = _format_arc_ij(arc_motion, cx, cy, nx, ny, center_x, center_y, feed=feed_rate_xy)
                    if step_arc:
                        lines.append(step_arc)

            # Continuous CCW perimeter cleanup pass around outer/inner arc walls & end-caps
            r_out = radius + r_loop
            r_in = max(0.001, radius - r_loop)
            out_end_x, out_end_y = center_x + r_out * math.cos(a1), center_y + r_out * math.sin(a1)
            out_start_x, out_start_y = center_x + r_out * math.cos(a0), center_y + r_out * math.sin(a0)
            in_start_x, in_start_y = center_x + r_in * math.cos(a0), center_y + r_in * math.sin(a0)
            in_end_x, in_end_y = center_x + r_in * math.cos(a1), center_y + r_in * math.sin(a1)

            lines.append(f"G1 X{_r4(out_end_x):.4f} Y{_r4(out_end_y):.4f} F{feed_rate_xy:.1f}")
            # Outer wall back to start, end-cap at start, inner wall to end, end-cap at end
            if is_ccw:
                # CCW slot: outer wall goes CW (G2) from a1 -> a0? No: CCW climb on outer wall is G2 (CW)
                # Wait: CCW tool orbit around slot interior: outer wall a0->a1 is G3, inner wall a1->a0 is G2!
                pass
            wall_to_start = _format_arc_ij(
                rev_arc_motion, out_end_x, out_end_y, out_start_x, out_start_y, center_x, center_y, feed=feed_rate_xy
            )
            if wall_to_start:
                lines.append(wall_to_start)
            cap_start_dir = "G3" if is_ccw else "G2"
            cap_start = _format_arc_ij(
                cap_start_dir, out_start_x, out_start_y, in_start_x, in_start_y, sx, sy, feed=feed_rate_xy
            )
            if cap_start:
                lines.append(cap_start)
            if r_in > 0.002:
                wall_to_end = _format_arc_ij(
                    arc_motion, in_start_x, in_start_y, in_end_x, in_end_y, center_x, center_y, feed=feed_rate_xy
                )
                if wall_to_end:
                    lines.append(wall_to_end)
            cap_end = _format_arc_ij(
                cap_start_dir, in_end_x, in_end_y, out_end_x, out_end_y, ex, ey, feed=feed_rate_xy
            )
            if cap_end:
                lines.append(cap_end)
            lines.append(f"G1 X{_r4(ex):.4f} Y{_r4(ey):.4f} F{feed_rate_xy:.1f}")
        else:
            lines.append(f"G0 X{_r4(sx):.4f} Y{_r4(sy):.4f}")
            lines.append(f"G0 Z{_r4(current_z + 1.0):.4f}")
            lines.append(f"G1 Z{_r4(target_pass_z):.4f} F{plunge_feed:.1f}")
            center_arc = _format_arc_ij(arc_motion, sx, sy, ex, ey, center_x, center_y, feed=feed_rate_xy)
            if center_arc:
                lines.append(center_arc)
            if slot_width - tool_diameter > 0.05:
                r_out = radius + r_loop
                r_in = max(0.001, radius - r_loop)
                ox1, oy1 = center_x + r_out * math.cos(a1), center_y + r_out * math.sin(a1)
                ox0, oy0 = center_x + r_out * math.cos(a0), center_y + r_out * math.sin(a0)
                ix0, iy0 = center_x + r_in * math.cos(a0), center_y + r_in * math.sin(a0)
                ix1, iy1 = center_x + r_in * math.cos(a1), center_y + r_in * math.sin(a1)
                lines.append(f"G1 X{_r4(ox1):.4f} Y{_r4(oy1):.4f} F{feed_rate_xy:.1f}")
                out_arc = _format_arc_ij(rev_arc_motion, ox1, oy1, ox0, oy0, center_x, center_y, feed=feed_rate_xy)
                if out_arc:
                    lines.append(out_arc)
                lines.append(f"G1 X{_r4(ix0):.4f} Y{_r4(iy0):.4f} F{feed_rate_xy:.1f}")
                if r_in > 0.002:
                    in_arc = _format_arc_ij(arc_motion, ix0, iy0, ix1, iy1, center_x, center_y, feed=feed_rate_xy)
                    if in_arc:
                        lines.append(in_arc)

        lines.append(f"G0 Z{retract_z:.3f}")
        current_z = target_pass_z

    lines.extend(
        postprocessor.format_footer(
            park_x=park_x,
            park_y=park_y,
            park_z=park_z if park_z is not None else retract_z,
        )
    )
    gcode_text = "\n".join(lines)

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=round(num_passes * (14.0 if cutting_strategy == "trochoidal" else 6.0), 1),
        warnings=warnings,
    )
