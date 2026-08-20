"""
2.5D Arbitrary Profile & Contour Milling Generator Engine.
Supports:
- Line and Arc segment chains (open contours and closed loops)
- Tool radius compensation (Left/Climb, Right/Conventional, Centerline)
- Smooth 90°/180° tangential circular and 45° linear lead-in/lead-out moves
- Multi-depth stepdowns with roughing passes, wall finish allowance, and spring passes
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from ..postprocessors import get_postprocessor


def _normalize_vec(dx: float, dy: float) -> Tuple[float, float, float]:
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0, 0.0
    return dx / length, dy / length, length


def _offset_line_segment(
    x0: float, y0: float, x1: float, y1: float, offset_dist: float
) -> Tuple[float, float, float, float]:
    """
    Offsets a line segment to the left by offset_dist (positive = left).
    """
    ux, uy, length = _normalize_vec(x1 - x0, y1 - y0)
    if length == 0:
        return x0, y0, x1, y1
    # Left normal is (-uy, ux)
    nx = -uy * offset_dist
    ny = ux * offset_dist
    return x0 + nx, y0 + ny, x1 + nx, y1 + ny


def _compute_lead_in(
    start_x: float,
    start_y: float,
    dir_x: float,
    dir_y: float,
    lead_in_type: str = "tangential_arc",
    lead_in_radius: float = 5.0,
) -> Tuple[List[str], float, float]:
    """
    Generates lead-in moves and returns (gcode_lines, approach_x, approach_y).
    """
    ux, uy, _ = _normalize_vec(dir_x, dir_y)
    lines = []

    if lead_in_type == "tangential_arc" and lead_in_radius > 0:
        # Arc center is to the left of direction: center = start + (-uy*R, ux*R)
        # Approach start point is start - ux*R + (-uy*R, ux*R)
        cx = start_x - uy * lead_in_radius
        cy = start_y + ux * lead_in_radius
        # Start of 90 deg tangent arc is start_x - ux*R, start_y - uy*R
        app_x = start_x - ux * lead_in_radius
        app_y = start_y - uy * lead_in_radius
        # Vector from approach point to arc center
        i_vec = cx - app_x
        j_vec = cy - app_y
        lines.append(f"G3 X{start_x:.3f} Y{start_y:.3f} I{i_vec:.3f} J{j_vec:.3f} (Tangential Arc Lead-In)")
        return lines, app_x, app_y
    elif lead_in_type == "linear_45" and lead_in_radius > 0:
        # 45-degree angle entry
        dist = lead_in_radius
        app_x = start_x - (ux + uy) * dist * 0.7071
        app_y = start_y - (uy - ux) * dist * 0.7071
        lines.append(f"G1 X{start_x:.3f} Y{start_y:.3f} (Linear 45 Lead-In)")
        return lines, app_x, app_y
    else:
        return [], start_x, start_y


def _compute_lead_out(
    end_x: float,
    end_y: float,
    dir_x: float,
    dir_y: float,
    lead_out_type: str = "tangential_arc",
    lead_out_radius: float = 5.0,
) -> List[str]:
    """
    Generates smooth departure moves tangent to the exit vector.
    """
    ux, uy, _ = _normalize_vec(dir_x, dir_y)
    lines = []

    if lead_out_type == "tangential_arc" and lead_out_radius > 0:
        # 90-degree tangent exit arc
        dep_x = end_x + ux * lead_out_radius
        dep_y = end_y + uy * lead_out_radius
        cx = end_x - uy * lead_out_radius
        cy = end_y + ux * lead_out_radius
        i_vec = cx - end_x
        j_vec = cy - end_y
        lines.append(f"G3 X{dep_x:.3f} Y{dep_y:.3f} I{i_vec:.3f} J{j_vec:.3f} (Tangential Arc Lead-Out)")
    elif lead_out_type == "linear_45" and lead_out_radius > 0:
        dist = lead_out_radius
        dep_x = end_x + (ux - uy) * dist * 0.7071
        dep_y = end_y + (uy + ux) * dist * 0.7071
        lines.append(f"G1 X{dep_x:.3f} Y{dep_y:.3f} (Linear 45 Lead-Out)")

    return lines


def generate_contour_profile(
    segments: Optional[List[Dict[str, Any]]] = None,
    start_point: Optional[Tuple[float, float]] = None,
    is_closed: bool = True,
    side: str = "left",  # 'left' (climb), 'right' (conventional), 'center'
    lead_in_type: str = "tangential_arc",
    lead_in_radius: float = 5.0,
    target_depth_z: float = -5.0,
    start_z: float = 0.0,
    stepdown_z: float = 1.5,
    retract_z: float = 5.0,
    finish_allowance: float = 0.2,
    spring_pass: bool = True,
    tool_diameter: float = 3.175,
    tool_number: int = 1,
    tool_name: str = "Endmill",
    spindle_speed: int = 16000,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
    units: str = "mm",
    dialect: str = "grbl",
    **kwargs,
) -> Dict[str, Any]:
    """
    Generates full G-code for 2.5D profile contouring with cutter compensation and multi-depth passes.
    """
    if not segments:
        # Default 40x30 rectangular profile with corner radius
        segments = [
            {"type": "line", "x": 40.0, "y": 0.0},
            {"type": "line", "x": 40.0, "y": 30.0},
            {"type": "line", "x": 0.0, "y": 30.0},
            {"type": "line", "x": 0.0, "y": 0.0},
        ]
        start_point = (0.0, 0.0)

    if start_point is None:
        start_point = (0.0, 0.0)

    post = get_postprocessor(dialect)
    lines = []

    # 1. Header
    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=f"2.5D Profile Contour: Side={side.upper()} | Tool={tool_name} (D={tool_diameter:.3f}{units})",
    )
    lines.extend(header)
    lines.append("")

    # 2. Spindle Start
    lines.extend(post.format_tool_comment(tool_number, tool_name))
    lines.extend(post.format_spindle_start(rpm=spindle_speed, dwell_seconds=1.5))
    lines.append("")

    # Tool offset calculation
    r_tool = tool_diameter / 2.0
    if side.lower() == "left":
        base_offset = r_tool
    elif side.lower() == "right":
        base_offset = -r_tool
    else:
        base_offset = 0.0

    # Depth level passes calculation
    total_depth = abs(target_depth_z - start_z)
    stepdown = max(0.1, abs(stepdown_z))
    num_passes = max(1, math.ceil(total_depth / stepdown))
    depth_levels = [start_z - (i + 1) * (total_depth / num_passes) for i in range(num_passes)]

    # Build offset segment chains
    def build_path_points(active_offset: float) -> Tuple[List[Dict[str, Any]], float, float]:
        path_segs = []
        curr_x, curr_y = start_point

        for seg in segments:
            seg_type = seg.get("type", "line").lower()
            nx = float(seg.get("x", curr_x))
            ny = float(seg.get("y", curr_y))

            if seg_type == "line":
                ox0, oy0, ox1, oy1 = _offset_line_segment(curr_x, curr_y, nx, ny, active_offset)
                path_segs.append({"type": "line", "x": ox1, "y": oy1, "orig_x": nx, "orig_y": ny})
            elif seg_type == "arc":
                # Arc offset
                cw = seg.get("cw", False)
                i_val = float(seg.get("i", 0.0))
                j_val = float(seg.get("j", 0.0))
                cx = curr_x + i_val
                cy = curr_y + j_val
                r_orig = math.hypot(i_val, j_val)
                # Offset arc radius
                r_offset = r_orig + (active_offset if cw else -active_offset)
                path_segs.append({
                    "type": "arc",
                    "x": nx,
                    "y": ny,
                    "cw": cw,
                    "i": i_val,
                    "j": j_val,
                    "radius": r_offset,
                })
            curr_x, curr_y = nx, ny

        # Initial direction vector for lead-in
        if segments:
            first_dx = segments[0].get("x", start_point[0]) - start_point[0]
            first_dy = segments[0].get("y", start_point[1]) - start_point[1]
        else:
            first_dx, first_dy = 1.0, 0.0

        return path_segs, first_dx, first_dy

    # Passes execution: Roughing passes + Finish pass
    passes_to_run = []
    if finish_allowance > 0:
        # Roughing pass offset (leave finish allowance)
        rough_offset = base_offset + (math.copysign(finish_allowance, base_offset) if base_offset != 0 else 0)
        passes_to_run.append({"type": "rough", "offset": rough_offset, "depths": depth_levels})
        # Finish pass offset
        passes_to_run.append({"type": "finish", "offset": base_offset, "depths": [target_depth_z]})
    else:
        passes_to_run.append({"type": "standard", "offset": base_offset, "depths": depth_levels})

    if spring_pass:
        passes_to_run.append({"type": "spring", "offset": base_offset, "depths": [target_depth_z]})

    lines.append(f"G0 Z{retract_z:.3f} (Move to safe clearance)")

    for pass_info in passes_to_run:
        p_type = pass_info["type"].upper()
        p_offset = pass_info["offset"]
        p_depths = pass_info["depths"]

        path_segs, init_dx, init_dy = build_path_points(p_offset)
        if not path_segs:
            continue

        # Compute lead-in start
        first_seg = path_segs[0]
        lead_in_lines, app_x, app_y = _compute_lead_in(
            start_point[0], start_point[1], init_dx, init_dy, lead_in_type, lead_in_radius
        )

        lines.append(f"( --- {p_type} PASS (Offset: {p_offset:+.3f}{units}) --- )")

        for current_z in p_depths:
            lines.append(f"( Depth Level Z: {current_z:.3f}{units} )")
            # Rapid to approach position
            lines.append(f"G0 X{app_x:.3f} Y{app_y:.3f}")
            lines.append(f"G0 Z{start_z + 1.0:.3f} (Approach Clearance)")
            lines.append(f"G1 Z{current_z:.3f} F{plunge_feed:.1f} (Plunge to Depth)")

            # Execute Lead-In
            if lead_in_lines:
                lines.extend(lead_in_lines)

            # Traverse Contour Path
            for seg in path_segs:
                if seg["type"] == "line":
                    lines.append(f"G1 X{seg['x']:.3f} Y{seg['y']:.3f} F{feed_rate_xy:.1f}")
                elif seg["type"] == "arc":
                    cmd = "G2" if seg.get("cw") else "G3"
                    lines.append(f"{cmd} X{seg['x']:.3f} Y{seg['y']:.3f} I{seg['i']:.3f} J{seg['j']:.3f} F{feed_rate_xy:.1f}")

            # Lead-Out
            if segments:
                last_dx = segments[-1].get("x", 0) - (segments[-2].get("x", 0) if len(segments) > 1 else start_point[0])
                last_dy = segments[-1].get("y", 0) - (segments[-2].get("y", 0) if len(segments) > 1 else start_point[1])
            else:
                last_dx, last_dy = 1.0, 0.0

            lead_out_lines = _compute_lead_out(
                path_segs[-1]["x"], path_segs[-1]["y"], last_dx, last_dy, lead_in_type, lead_in_radius
            )
            if lead_out_lines:
                lines.extend(lead_out_lines)

            # Retract between depth levels
            lines.append(f"G0 Z{retract_z:.3f} (Retract)")
            lines.append("")

    # 4. Footer
    footer = post.format_footer(park_z=retract_z, park_x=0.0, park_y=0.0)
    lines.extend(footer)

    full_gcode = "\n".join(lines)

    return {
        "gcode": full_gcode,
        "segment_count": len(segments),
        "total_depth": total_depth,
        "passes": len(depth_levels),
        "side": side,
        "tool_diameter": tool_diameter,
        "estimated_time_seconds": (total_depth / max(plunge_feed, 1)) * 60 + (len(segments) * 2),
    }
