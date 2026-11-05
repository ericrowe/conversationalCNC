"""
2.5D Arbitrary Profile & Contour Milling Generator Engine.
Supports:
- Line and Arc segment chains (open contours and closed loops)
- Tool radius compensation (Left/Climb, Right/Conventional, Centerline)
- Smooth 90° tangential circular and 45° linear lead-in/lead-out moves
- Multi-depth stepdowns with roughing passes, wall finish allowance, and spring passes
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from ..postprocessors import get_postprocessor
from .base import BoundingBox, normalize_units


def _normalize_vec(dx: float, dy: float) -> Tuple[float, float, float]:
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0, 0.0
    return dx / length, dy / length, length


def _offset_line_segment(
    x0: float, y0: float, x1: float, y1: float, offset_dist: float
) -> Tuple[float, float, float, float]:
    """
    Offsets a line segment to the left by offset_dist (positive = left, negative = right).
    """
    ux, uy, length = _normalize_vec(x1 - x0, y1 - y0)
    if length == 0:
        return x0, y0, x1, y1
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
    side: str = "left",
    feed_rate_xy: Optional[float] = None,
) -> Tuple[List[str], float, float]:
    """
    Generates geometrically exact quarter-circle tangential or 45-degree linear lead-in moves
    on the scrap/offset side of the contour and returns (gcode_lines, approach_x, approach_y).
    """
    ux, uy, length = _normalize_vec(dir_x, dir_y)
    if length == 0:
        ux, uy = 1.0, 0.0

    # Normal pointing toward the offset / scrap side
    if side.lower() == "right":
        nx, ny = uy, -ux
        arc_cmd = "G2"
    else:
        nx, ny = -uy, ux
        arc_cmd = "G3"

    lines: List[str] = []
    f_str = f" F{feed_rate_xy:.1f}" if feed_rate_xy is not None else ""

    if lead_in_type in ("tangential_arc", "arc") and lead_in_radius > 0:
        # Center of 90-deg lead-in arc is at start + n * R
        cx = start_x + nx * lead_in_radius
        cy = start_y + ny * lead_in_radius
        # Approach point is 90 degrees back along -u from center: C - u * R
        app_x = cx - ux * lead_in_radius
        app_y = cy - uy * lead_in_radius
        # Incremental vector from approach start (app_x, app_y) to center (cx, cy)
        i_vec = cx - app_x
        j_vec = cy - app_y
        lines.append(
            f"{arc_cmd} X{start_x:.3f} Y{start_y:.3f} I{i_vec:.3f} J{j_vec:.3f}{f_str} (Tangential Arc Lead-In)"
        )
        return lines, app_x, app_y
    elif lead_in_type == "linear_45" and lead_in_radius > 0:
        dist = lead_in_radius
        inv_sqrt2 = math.sqrt(0.5)
        app_x = start_x + (-ux + nx) * dist * inv_sqrt2
        app_y = start_y + (-uy + ny) * dist * inv_sqrt2
        lines.append(f"G1 X{start_x:.3f} Y{start_y:.3f}{f_str} (Linear 45 Lead-In)")
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
    side: str = "left",
    feed_rate_xy: Optional[float] = None,
) -> List[str]:
    """
    Generates geometrically exact quarter-circle tangential or 45-degree linear lead-out moves
    departing toward the scrap/offset side of the contour.
    """
    ux, uy, length = _normalize_vec(dir_x, dir_y)
    if length == 0:
        ux, uy = 1.0, 0.0

    if side.lower() == "right":
        nx, ny = uy, -ux
        arc_cmd = "G2"
    else:
        nx, ny = -uy, ux
        arc_cmd = "G3"

    lines: List[str] = []
    f_str = f" F{feed_rate_xy:.1f}" if feed_rate_xy is not None else ""

    if lead_out_type in ("tangential_arc", "arc") and lead_out_radius > 0:
        # Center of 90-deg lead-out arc is at end + n * R
        cx = end_x + nx * lead_out_radius
        cy = end_y + ny * lead_out_radius
        # Departure point is 90 degrees forward along +u from center: C + u * R
        dep_x = cx + ux * lead_out_radius
        dep_y = cy + uy * lead_out_radius
        # Incremental vector from arc start (end_x, end_y) to center (cx, cy)
        i_vec = cx - end_x
        j_vec = cy - end_y
        lines.append(
            f"{arc_cmd} X{dep_x:.3f} Y{dep_y:.3f} I{i_vec:.3f} J{j_vec:.3f}{f_str} (Tangential Arc Lead-Out)"
        )
    elif lead_out_type == "linear_45" and lead_out_radius > 0:
        dist = lead_out_radius
        inv_sqrt2 = math.sqrt(0.5)
        dep_x = end_x + (ux + nx) * dist * inv_sqrt2
        dep_y = end_y + (uy + ny) * dist * inv_sqrt2
        lines.append(f"G1 X{dep_x:.3f} Y{dep_y:.3f}{f_str} (Linear 45 Lead-Out)")

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
    spindle_type: str = "router",
    router_model: Optional[str] = "dewalt_611",
    router_dial: Optional[float] = None,
    require_pause: bool = False,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
    units: str = "mm",
    dialect: str = "grbl",
    **kwargs,
) -> Dict[str, Any]:
    """
    Generates full G-code for 2.5D profile contouring with cutter compensation and multi-depth passes.
    """
    # CNC-009: Reject missing or empty geometry (never substitute a default rectangle)
    units = normalize_units(units)
    if not segments or not isinstance(segments, list) or len(segments) == 0:
        raise ValueError("Contour segments must be a non-empty list of geometry segments.")

    if tool_diameter <= 0:
        raise ValueError(f"tool_diameter ({tool_diameter}) must be greater than zero.")

    if stepdown_z <= 0:
        raise ValueError(f"stepdown_z ({stepdown_z}) must be greater than zero.")

    if finish_allowance < 0:
        raise ValueError(f"finish_allowance ({finish_allowance}) cannot be negative.")

    side_norm = (side or "left").lower().strip()
    if side_norm not in ("left", "right", "center"):
        raise ValueError(f"Invalid side '{side}'. Must be 'left', 'right', or 'center'.")

    # CNC-006: Validate depth direction and finish allowance with centerline
    if target_depth_z >= start_z:
        raise ValueError(
            f"target_depth_z ({target_depth_z}) must be strictly below start_z ({start_z})."
        )

    if retract_z <= start_z:
        raise ValueError(f"retract_z ({retract_z}) must be above start_z ({start_z}).")

    if finish_allowance > 0 and side_norm == "center":
        raise ValueError(
            "finish_allowance > 0 is not permitted when side='center' because material side is ambiguous."
        )

    if start_point is None:
        start_point = (0.0, 0.0)
    else:
        start_point = (float(start_point[0]), float(start_point[1]))

    post = get_postprocessor(dialect)
    lines: List[str] = []

    # 1. Header
    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=f"2.5D Profile Contour: Side={side_norm.upper()} | Tool={tool_name} (D={tool_diameter:.3f}{units})",
    )
    lines.extend(header)
    lines.append("")

    # 2. Spindle Start
    lines.extend(post.format_tool_comment(tool_number, tool_name))
    lines.extend(
        post.format_spindle_start(
            rpm=spindle_speed,
            clockwise=True,
            dwell_seconds=1.5,
            spindle_type=spindle_type,
            router_model=router_model,
            router_dial=router_dial,
            require_pause=require_pause,
        )
    )
    lines.append("")

    # Tool offset calculation
    r_tool = tool_diameter / 2.0
    if side_norm == "left":
        base_offset = r_tool
    elif side_norm == "right":
        base_offset = -r_tool
    else:
        base_offset = 0.0

    # Depth level passes calculation
    total_depth = start_z - target_depth_z
    stepdown = abs(stepdown_z)
    num_passes = max(1, math.ceil(total_depth / stepdown))
    depth_levels = [start_z - (i + 1) * (total_depth / num_passes) for i in range(num_passes)]
    depth_levels[-1] = target_depth_z

    # Build offset segment chains with exact line & arc cutter compensation
    def build_path_points(
        active_offset: float,
    ) -> Tuple[List[Dict[str, Any]], Tuple[float, float], Tuple[float, float], BoundingBox]:
        raw_offset_segs: List[Dict[str, Any]] = []
        curr_x, curr_y = start_point

        for seg_idx, seg in enumerate(segments):
            seg_type = (seg.get("type") or "line").lower().strip()
            if "x" not in seg or "y" not in seg:
                raise ValueError(f"Segment {seg_idx} missing required 'x' or 'y' coordinate.")
            nx = float(seg["x"])
            ny = float(seg["y"])

            if seg_type == "line":
                ux, uy, length = _normalize_vec(nx - curr_x, ny - curr_y)
                if length < 1e-6:
                    raise ValueError(f"Segment {seg_idx} has zero length.")
                ox0, oy0, ox1, oy1 = _offset_line_segment(curr_x, curr_y, nx, ny, active_offset)
                raw_offset_segs.append(
                    {
                        "type": "line",
                        "vx0": curr_x,
                        "vy0": curr_y,
                        "vx1": nx,
                        "vy1": ny,
                        "length": length,
                        "orig_ox0": ox0,
                        "orig_oy0": oy0,
                        "t_start": 0.0,
                        "t_end": length,
                        "ox0": ox0,
                        "oy0": oy0,
                        "x": ox1,
                        "y": oy1,
                        "t_in": (ux, uy),
                        "t_out": (ux, uy),
                    }
                )
            elif seg_type == "arc":
                cw = bool(seg.get("cw", False))
                i_val = float(seg.get("i", 0.0))
                j_val = float(seg.get("j", 0.0))
                cx = curr_x + i_val
                cy = curr_y + j_val
                r_start_orig = math.hypot(curr_x - cx, curr_y - cy)
                r_end_orig = math.hypot(nx - cx, ny - cy)
                if r_start_orig <= 1e-6 or abs(r_start_orig - r_end_orig) > 0.01:
                    raise ValueError(
                        f"Segment {seg_idx} invalid arc center: start radius {r_start_orig:.4f} != end radius {r_end_orig:.4f}."
                    )
                r_orig = r_start_orig
                # Left of CW is outward (+active_offset); left of CCW is inward (-active_offset)
                r_offset = r_orig + (active_offset if cw else -active_offset)
                if r_offset <= 1e-6:
                    raise ValueError(
                        f"Segment {seg_idx} compensated arc radius ({r_offset:.4f}) collapsed to <= 0."
                    )

                ur0_x = (curr_x - cx) / r_orig
                ur0_y = (curr_y - cy) / r_orig
                ur1_x = (nx - cx) / r_orig
                ur1_y = (ny - cy) / r_orig

                ox0 = cx + ur0_x * r_offset
                oy0 = cy + ur0_y * r_offset
                ox1 = cx + ur1_x * r_offset
                oy1 = cy + ur1_y * r_offset

                i_off = cx - ox0
                j_off = cy - oy0

                if cw:
                    t_in = (ur0_y, -ur0_x)
                    t_out = (ur1_y, -ur1_x)
                else:
                    t_in = (-ur0_y, ur0_x)
                    t_out = (-ur1_y, ur1_x)

                raw_offset_segs.append(
                    {
                        "type": "arc",
                        "vx0": curr_x,
                        "vy0": curr_y,
                        "vx1": nx,
                        "vy1": ny,
                        "ox0": ox0,
                        "oy0": oy0,
                        "x": ox1,
                        "y": oy1,
                        "cw": cw,
                        "cx": cx,
                        "cy": cy,
                        "i": i_off,
                        "j": j_off,
                        "radius": r_offset,
                        "t_in": t_in,
                        "t_out": t_out,
                    }
                )
            else:
                raise ValueError(f"Unsupported contour segment type: '{seg_type}'.")

            curr_x, curr_y = nx, ny

        if is_closed and math.hypot(curr_x - start_point[0], curr_y - start_point[1]) > 1e-3:
            effective_closed = False
        else:
            effective_closed = is_closed

        # Resolve line-line corner intersections or insert tangent corner-roll arcs so path is continuous and gouge-free
        n_segs = len(raw_offset_segs)
        for idx in range(n_segs):
            if not effective_closed and idx == n_segs - 1:
                break
            nxt_idx = (idx + 1) % n_segs
            s1 = raw_offset_segs[idx]
            s2 = raw_offset_segs[nxt_idx]
            gap = math.hypot(s2["ox0"] - s1["x"], s2["oy0"] - s1["y"])
            if gap > 1e-5 and s1["type"] == "line" and s2["type"] == "line":
                # Intersect offset lines s1 and s2 using their original un-trimmed origins
                u1x, u1y = s1["t_out"]
                u2x, u2y = s2["t_in"]
                cross = u1x * u2y - u1y * u2x
                det = u1x * (-u2y) - u1y * (-u2x)
                if abs(det) > 1e-5:
                    rhs_x = s2["orig_ox0"] - s1["orig_ox0"]
                    rhs_y = s2["orig_oy0"] - s1["orig_oy0"]
                    t1_param = (rhs_x * (-u2y) - rhs_y * (-u2x)) / det
                    t2_param = (u1x * rhs_y - u1y * rhs_x) / det
                    # Concave inside corner check (cutter is on the inside of the turn when active_offset * cross > 0)
                    if active_offset * cross > 1e-6:
                        if t1_param <= 1e-5 or t2_param >= s2["length"] - 1e-5:
                            raise ValueError(
                                f"Concave corner between segments {idx} and {nxt_idx} is smaller than cutter offset "
                                f"({abs(active_offset):.3f}{units}); tool would invert segment and gouge stock."
                            )
                    s1["t_end"] = t1_param
                    s2["t_start"] = t2_param
                    ix = s1["orig_ox0"] + t1_param * u1x
                    iy = s1["orig_oy0"] + t1_param * u1y
                    s1["x"], s1["y"] = ix, iy
                    s2["ox0"], s2["oy0"] = ix, iy

        # Re-verify that no line segment collapsed or inverted after trimming at both ends
        for idx, s in enumerate(raw_offset_segs):
            if s["type"] == "line":
                if s["t_end"] - s["t_start"] <= 1e-5:
                    raise ValueError(
                        f"Segment {idx} collapsed or inverted after concave cutter offset compensation "
                        f"(t_start={s['t_start']:.4f}, t_end={s['t_end']:.4f}); tool radius is too large for concave feature."
                    )

        # Assemble final continuous path_segs (rolling around convex non-tangent corners with a tangent arc)
        path_segs: List[Dict[str, Any]] = []
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        def _track_xy(px: float, py: float) -> None:
            nonlocal min_x, max_x, min_y, max_y
            min_x = min(min_x, px)
            max_x = max(max_x, px)
            min_y = min(min_y, py)
            max_y = max(max_y, py)

        def _make_corner_transition(
            prev_seg: Dict[str, Any], next_seg: Dict[str, Any]
        ) -> Dict[str, Any]:
            sx, sy = prev_seg["x"], prev_seg["y"]
            ex, ey = next_seg["ox0"], next_seg["oy0"]
            vx, vy = prev_seg["vx1"], prev_seg["vy1"]
            u1x, u1y = prev_seg["t_out"]
            u2x, u2y = next_seg["t_in"]
            cross = u1x * u2y - u1y * u2x

            # If cutter is on the outside of a non-tangent corner (convex corner) and offset > 0,
            # roll around vertex (vx, vy) with an arc of radius |active_offset| so distance to V is always |active_offset|
            r_start_v = math.hypot(sx - vx, sy - vy)
            r_end_v = math.hypot(ex - vx, ey - vy)
            if abs(active_offset) > 1e-5 and abs(r_start_v - abs(active_offset)) < 1e-3 and abs(r_end_v - abs(active_offset)) < 1e-3:
                if active_offset * cross > 1e-6:
                    # Concave non-tangent transition without valid trim -> would gouge vertex V
                    raise ValueError(
                        f"Concave non-tangent line/arc corner at ({vx:.3f}, {vy:.3f}) would be gouged by cutter radius {abs(active_offset):.3f}."
                    )
                cw_roll = active_offset > 0
                return {
                    "type": "arc",
                    "vx0": vx,
                    "vy0": vy,
                    "vx1": vx,
                    "vy1": vy,
                    "ox0": sx,
                    "oy0": sy,
                    "x": ex,
                    "y": ey,
                    "cw": cw_roll,
                    "cx": vx,
                    "cy": vy,
                    "i": vx - sx,
                    "j": vy - sy,
                    "radius": abs(active_offset),
                    "t_in": prev_seg["t_out"],
                    "t_out": next_seg["t_in"],
                }

            return {
                "type": "line",
                "vx0": vx,
                "vy0": vy,
                "vx1": vx,
                "vy1": vy,
                "ox0": sx,
                "oy0": sy,
                "x": ex,
                "y": ey,
                "t_in": next_seg["t_in"],
                "t_out": next_seg["t_in"],
            }

        for idx, s in enumerate(raw_offset_segs):
            if idx > 0:
                prev_end_x, prev_end_y = path_segs[-1]["x"], path_segs[-1]["y"]
                if math.hypot(s["ox0"] - prev_end_x, s["oy0"] - prev_end_y) > 1e-4:
                    bridge = _make_corner_transition(path_segs[-1], s)
                    path_segs.append(bridge)
                    _track_xy(bridge["x"], bridge["y"])
            path_segs.append(s)
            _track_xy(s["ox0"], s["oy0"])
            _track_xy(s["x"], s["y"])
            if s["type"] == "arc":
                cx, cy, r_off = s["cx"], s["cy"], s["radius"]
                a0 = math.atan2(s["oy0"] - cy, s["ox0"] - cx)
                a1 = math.atan2(s["y"] - cy, s["x"] - cx)
                sweep = (a0 - a1) % (2.0 * math.pi) if s["cw"] else (a1 - a0) % (2.0 * math.pi)
                if sweep < 1e-6:
                    sweep = 2.0 * math.pi
                for card in (0.0, math.pi / 2.0, math.pi, -math.pi / 2.0):
                    rel = (a0 - card) % (2.0 * math.pi) if s["cw"] else (card - a0) % (2.0 * math.pi)
                    if rel <= sweep + 1e-6:
                        _track_xy(cx + r_off * math.cos(card), cy + r_off * math.sin(card))

        if effective_closed and len(path_segs) > 1:
            first_ox0, first_oy0 = path_segs[0]["ox0"], path_segs[0]["ox0"]
            first_ox0, first_oy0 = path_segs[0]["ox0"], path_segs[0]["oy0"]
            last_x, last_y = path_segs[-1]["x"], path_segs[-1]["y"]
            if math.hypot(first_ox0 - last_x, first_oy0 - last_y) > 1e-4:
                closing_bridge = _make_corner_transition(path_segs[-1], path_segs[0])
                path_segs.append(closing_bridge)
                _track_xy(closing_bridge["x"], closing_bridge["y"])

        bbox = BoundingBox(
            min_x=min_x if min_x != float("inf") else 0.0,
            max_x=max_x if max_x != float("-inf") else 0.0,
            min_y=min_y if min_y != float("inf") else 0.0,
            max_y=max_y if max_y != float("-inf") else 0.0,
            min_z=target_depth_z,
            max_z=retract_z,
        )
        return path_segs, path_segs[0]["t_in"], path_segs[-1]["t_out"], bbox

    # Passes execution: Roughing passes + Finish pass
    passes_to_run = []
    if finish_allowance > 0:
        rough_offset = base_offset + math.copysign(finish_allowance, base_offset)
        passes_to_run.append({"type": "rough", "offset": rough_offset, "depths": depth_levels})
        passes_to_run.append({"type": "finish", "offset": base_offset, "depths": [target_depth_z]})
    else:
        passes_to_run.append({"type": "standard", "offset": base_offset, "depths": depth_levels})

    if spring_pass:
        passes_to_run.append({"type": "spring", "offset": base_offset, "depths": [target_depth_z]})

    lines.append(f"G0 Z{retract_z:.3f} (Move to safe clearance)")

    final_bbox = BoundingBox(min_z=target_depth_z, max_z=retract_z)

    for pass_info in passes_to_run:
        p_type = pass_info["type"].upper()
        p_offset = pass_info["offset"]
        p_depths = pass_info["depths"]

        path_segs, init_tangent, exit_tangent, pass_bbox = build_path_points(p_offset)
        if pass_info["type"] in ("finish", "standard"):
            final_bbox = pass_bbox

        comp_start_x = path_segs[0]["ox0"]
        comp_start_y = path_segs[0]["oy0"]
        comp_end_x = path_segs[-1]["x"]
        comp_end_y = path_segs[-1]["y"]

        lead_in_lines, app_x, app_y = _compute_lead_in(
            comp_start_x,
            comp_start_y,
            init_tangent[0],
            init_tangent[1],
            lead_in_type=lead_in_type,
            lead_in_radius=lead_in_radius,
            side=side_norm,
            feed_rate_xy=feed_rate_xy,
        )

        lead_out_lines = _compute_lead_out(
            comp_end_x,
            comp_end_y,
            exit_tangent[0],
            exit_tangent[1],
            lead_out_type=lead_in_type,
            lead_out_radius=lead_in_radius,
            side=side_norm,
            feed_rate_xy=feed_rate_xy,
        )

        lines.append(f"( --- {p_type} PASS (Offset: {p_offset:+.3f}{units}) --- )")

        for current_z in p_depths:
            lines.append(f"( Depth Level Z: {current_z:.3f}{units} )")
            lines.append(f"G0 X{app_x:.3f} Y{app_y:.3f}")
            lines.append(f"G0 Z{start_z + 1.0:.3f} (Approach Clearance)")
            lines.append(f"G1 Z{current_z:.3f} F{plunge_feed:.1f} (Plunge to Depth)")

            if lead_in_lines:
                lines.extend(lead_in_lines)

            for seg in path_segs:
                if seg["type"] == "line":
                    lines.append(f"G1 X{seg['x']:.3f} Y{seg['y']:.3f} F{feed_rate_xy:.1f}")
                elif seg["type"] == "arc":
                    cmd = "G2" if seg.get("cw") else "G3"
                    lines.append(
                        f"{cmd} X{seg['x']:.3f} Y{seg['y']:.3f} I{seg['i']:.3f} J{seg['j']:.3f} F{feed_rate_xy:.1f}"
                    )

            if lead_out_lines:
                lines.extend(lead_out_lines)

            lines.append(f"G0 Z{retract_z:.3f} (Retract)")
            lines.append("")

    # 3. Footer
    footer = post.format_footer(park_z=retract_z, park_x=0.0, park_y=0.0)
    lines.extend(footer)

    gcode_text = "\n".join(lines)

    return {
        "gcode": gcode_text,
        "line_count": len(lines),
        "passes": len(depth_levels),
        "depth_passes": len(depth_levels),
        "total_passes": len(passes_to_run),
        "segment_count": len(segments),
        "side": side_norm,
        "tool_offset": round(base_offset, 4),
        "finish_allowance": finish_allowance,
        "bounds": final_bbox.to_dict(),
    }
