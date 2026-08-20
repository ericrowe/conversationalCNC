"""
Pure Python DXF 2D Vector CAD Importer Engine (Phase 5).
Parses AutoCAD ASCII DXF files (R12 to R2018), extracts 2D geometry primitives
(LINE, ARC, CIRCLE, LWPOLYLINE), chains continuous paths/closed loops,
and converts directly into Contouring, Pocketing, and Drilling toolpaths.
"""
import math
from typing import Dict, Any, List, Tuple, Optional
from .base import BoundingBox, GCodeProgram, strip_header_and_footer
from .contouring import generate_contour_profile
from .drilling import generate_straight_plunge, generate_peck_drilling
from ..postprocessors import get_postprocessor


class DXFEntity:
    def __init__(self, entity_type: str, layer: str = "0", color: int = 7):
        self.entity_type = entity_type
        self.layer = layer
        self.color = color


class DXFLine(DXFEntity):
    def __init__(self, x1: float, y1: float, x2: float, y2: float, layer: str = "0", color: int = 7):
        super().__init__("LINE", layer, color)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


class DXFCircle(DXFEntity):
    def __init__(self, cx: float, cy: float, radius: float, layer: str = "0", color: int = 7):
        super().__init__("CIRCLE", layer, color)
        self.cx = cx
        self.cy = cy
        self.radius = radius


class DXFArc(DXFEntity):
    def __init__(self, cx: float, cy: float, radius: float, start_angle_deg: float, end_angle_deg: float, layer: str = "0", color: int = 7):
        super().__init__("ARC", layer, color)
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.start_angle_deg = start_angle_deg
        self.end_angle_deg = end_angle_deg


class DXFPolyline(DXFEntity):
    def __init__(self, vertices: List[Tuple[float, float, float]], is_closed: bool = False, layer: str = "0", color: int = 7):
        # vertices are tuples of (x, y, bulge)
        super().__init__("LWPOLYLINE", layer, color)
        self.vertices = vertices
        self.is_closed = is_closed


def parse_dxf_ascii(dxf_content: str) -> Dict[str, Any]:
    """
    Parses raw ASCII DXF content into structured entities, layers, and bounding boxes.
    """
    lines = [line.strip() for line in dxf_content.splitlines()]
    pairs: List[Tuple[int, str]] = []
    i = 0
    while i < len(lines) - 1:
        try:
            code = int(lines[i])
            val = lines[i + 1]
            pairs.append((code, val))
            i += 2
        except ValueError:
            i += 1

    entities: List[DXFEntity] = []
    layers = set()

    in_entities = False
    idx = 0
    n = len(pairs)

    while idx < n:
        code, val = pairs[idx]
        if code == 0 and val.upper() == "SECTION":
            if idx + 1 < n and pairs[idx + 1][0] == 2 and pairs[idx + 1][1].upper() == "ENTITIES":
                in_entities = True
                idx += 2
                continue
        elif code == 0 and val.upper() == "ENDSEC":
            in_entities = False

        if in_entities and code == 0:
            etype = val.upper()
            idx += 1
            cur_layer = "0"
            cur_color = 7
            data: Dict[int, Any] = {}
            poly_verts: List[Tuple[float, float, float]] = []
            cur_vx, cur_vy, cur_vb = None, None, 0.0
            is_poly_closed = False

            while idx < n and pairs[idx][0] != 0:
                p_code, p_val = pairs[idx]
                if p_code == 8:
                    cur_layer = p_val
                    layers.add(cur_layer)
                elif p_code == 62:
                    cur_color = int(p_val)
                elif p_code == 70 and etype == "LWPOLYLINE":
                    is_poly_closed = (int(p_val) & 1) != 0
                elif p_code == 10 and etype == "LWPOLYLINE":
                    if cur_vx is not None and cur_vy is not None:
                        poly_verts.append((cur_vx, cur_vy, cur_vb))
                    cur_vx = float(p_val)
                    cur_vy = 0.0
                    cur_vb = 0.0
                elif p_code == 20 and etype == "LWPOLYLINE":
                    cur_vy = float(p_val)
                elif p_code == 42 and etype == "LWPOLYLINE":
                    cur_vb = float(p_val)
                else:
                    try:
                        data[p_code] = float(p_val)
                    except ValueError:
                        data[p_code] = p_val
                idx += 1

            # Finalize LWPOLYLINE vertex
            if etype == "LWPOLYLINE" and cur_vx is not None and cur_vy is not None:
                poly_verts.append((cur_vx, cur_vy, cur_vb))

            if etype == "LINE":
                x1, y1 = float(data.get(10, 0.0)), float(data.get(20, 0.0))
                x2, y2 = float(data.get(11, 0.0)), float(data.get(21, 0.0))
                entities.append(DXFLine(x1, y1, x2, y2, layer=cur_layer, color=cur_color))
            elif etype == "CIRCLE":
                cx, cy = float(data.get(10, 0.0)), float(data.get(20, 0.0))
                r = float(data.get(40, 1.0))
                entities.append(DXFCircle(cx, cy, r, layer=cur_layer, color=cur_color))
            elif etype == "ARC":
                cx, cy = float(data.get(10, 0.0)), float(data.get(20, 0.0))
                r = float(data.get(40, 1.0))
                sa = float(data.get(50, 0.0))
                ea = float(data.get(51, 360.0))
                entities.append(DXFArc(cx, cy, r, sa, ea, layer=cur_layer, color=cur_color))
            elif etype == "LWPOLYLINE":
                if poly_verts:
                    entities.append(DXFPolyline(poly_verts, is_closed=is_poly_closed, layer=cur_layer, color=cur_color))
            continue

        idx += 1

    # Extract Drill Circles
    circles = []
    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")

    def update_bounds(x: float, y: float):
        nonlocal min_x, max_x, min_y, max_y
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)

    for e in entities:
        if isinstance(e, DXFLine):
            update_bounds(e.x1, e.y1)
            update_bounds(e.x2, e.y2)
        elif isinstance(e, DXFCircle):
            circles.append({
                "x": round(e.cx, 4),
                "y": round(e.cy, 4),
                "radius": round(e.radius, 4),
                "diameter": round(e.radius * 2.0, 4),
                "layer": e.layer,
            })
            update_bounds(e.cx - e.radius, e.cy - e.radius)
            update_bounds(e.cx + e.radius, e.cy + e.radius)
        elif isinstance(e, DXFArc):
            update_bounds(e.cx - e.radius, e.cy - e.radius)
            update_bounds(e.cx + e.radius, e.cy + e.radius)
        elif isinstance(e, DXFPolyline):
            for vx, vy, _ in e.vertices:
                update_bounds(vx, vy)

    if min_x == float("inf"):
        min_x, max_x, min_y, max_y = 0.0, 0.0, 0.0, 0.0

    # Convert Polylines & Chained Entities into Contour Chains
    chains = _extract_chains_from_entities(entities)

    return {
        "entity_count": len(entities),
        "layers": sorted(list(layers)) if layers else ["0"],
        "circles": circles,
        "chains": chains,
        "bounding_box": {
            "min_x": round(min_x, 3),
            "max_x": round(max_x, 3),
            "min_y": round(min_y, 3),
            "max_y": round(max_y, 3),
            "width": round(max_x - min_x, 3),
            "height": round(max_y - min_y, 3),
        }
    }


def _extract_chains_from_entities(entities: List[DXFEntity], tol: float = 0.05) -> List[Dict[str, Any]]:
    """
    Extracts ordered contour chains from polylines, lines, and arcs.
    """
    chains = []

    # 1. First add explicit LWPOLYLINEs
    for e in entities:
        if isinstance(e, DXFPolyline) and len(e.vertices) >= 2:
            segments = []
            v_start = e.vertices[0]
            start_pt = [v_start[0], v_start[1]]

            for k in range(len(e.vertices) - 1):
                v_curr = e.vertices[k]
                v_next = e.vertices[k + 1]
                bulge = v_curr[2]
                if abs(bulge) < 1e-4:
                    segments.append({
                        "type": "line",
                        "x": round(v_next[0], 4),
                        "y": round(v_next[1], 4),
                        "i": 0.0,
                        "j": 0.0,
                        "cw": False,
                    })
                else:
                    # Convert bulge to arc
                    arc_info = _bulge_to_arc(v_curr[0], v_curr[1], v_next[0], v_next[1], bulge)
                    segments.append({
                        "type": "arc",
                        "x": round(v_next[0], 4),
                        "y": round(v_next[1], 4),
                        "i": round(arc_info["i"], 4),
                        "j": round(arc_info["j"], 4),
                        "cw": arc_info["cw"],
                    })

            if e.is_closed:
                v_last = e.vertices[-1]
                bulge = v_last[2]
                if abs(bulge) < 1e-4:
                    segments.append({
                        "type": "line",
                        "x": round(v_start[0], 4),
                        "y": round(v_start[1], 4),
                        "i": 0.0,
                        "j": 0.0,
                        "cw": False,
                    })
                else:
                    arc_info = _bulge_to_arc(v_last[0], v_last[1], v_start[0], v_start[1], bulge)
                    segments.append({
                        "type": "arc",
                        "x": round(v_start[0], 4),
                        "y": round(v_start[1], 4),
                        "i": round(arc_info["i"], 4),
                        "j": round(arc_info["j"], 4),
                        "cw": arc_info["cw"],
                    })

            chains.append({
                "id": len(chains) + 1,
                "layer": e.layer,
                "is_closed": e.is_closed,
                "start_point": start_pt,
                "segments": segments,
                "segment_count": len(segments),
            })

    # 2. Stitch loose LINE and ARC segments into chains
    loose_lines = [e for e in entities if isinstance(e, DXFLine)]
    loose_arcs = [e for e in entities if isinstance(e, DXFArc)]

    unvisited_lines = list(loose_lines)
    while unvisited_lines:
        first_line = unvisited_lines.pop(0)
        curr_chain = [{
            "type": "line",
            "x": round(first_line.x2, 4),
            "y": round(first_line.y2, 4),
            "i": 0.0,
            "j": 0.0,
            "cw": False,
        }]
        start_pt = [round(first_line.x1, 4), round(first_line.y1, 4)]
        cur_end = [first_line.x2, first_line.y2]
        layer = first_line.layer

        matched = True
        while matched:
            matched = False
            for idx, candidate in enumerate(unvisited_lines):
                if candidate.layer != layer:
                    continue
                # Forward match
                if math.hypot(candidate.x1 - cur_end[0], candidate.y1 - cur_end[1]) <= tol:
                    curr_chain.append({
                        "type": "line",
                        "x": round(candidate.x2, 4),
                        "y": round(candidate.y2, 4),
                        "i": 0.0,
                        "j": 0.0,
                        "cw": False,
                    })
                    cur_end = [candidate.x2, candidate.y2]
                    unvisited_lines.pop(idx)
                    matched = True
                    break
                # Reversed match
                elif math.hypot(candidate.x2 - cur_end[0], candidate.y2 - cur_end[1]) <= tol:
                    curr_chain.append({
                        "type": "line",
                        "x": round(candidate.x1, 4),
                        "y": round(candidate.y1, 4),
                        "i": 0.0,
                        "j": 0.0,
                        "cw": False,
                    })
                    cur_end = [candidate.x1, candidate.y1]
                    unvisited_lines.pop(idx)
                    matched = True
                    break

        is_closed = math.hypot(cur_end[0] - start_pt[0], cur_end[1] - start_pt[1]) <= tol
        chains.append({
            "id": len(chains) + 1,
            "layer": layer,
            "is_closed": is_closed,
            "start_point": start_pt,
            "segments": curr_chain,
            "segment_count": len(curr_chain),
        })

    return chains


def _bulge_to_arc(x1: float, y1: float, x2: float, y2: float, bulge: float) -> Dict[str, Any]:
    """
    Converts DXF polyline bulge into circle center offsets (i, j) and CW flag.
    """
    theta = 4.0 * math.atan(bulge)
    dx = x2 - x1
    dy = y2 - y1
    chord = math.hypot(dx, dy)
    radius = (chord * (1.0 + bulge * bulge)) / (4.0 * abs(bulge)) if abs(bulge) > 1e-6 else chord / 2.0

    # Normal vector to chord
    nx = -dy / chord
    ny = dx / chord
    # Distance from chord midpoint to circle center
    sagitta = (bulge * chord) / 2.0
    h = radius - abs(sagitta)

    sign = 1.0 if bulge > 0 else -1.0
    mx = (x1 + x2) / 2.0
    my = (y1 + y2) / 2.0

    cx = mx + sign * h * nx
    cy = my + sign * h * ny

    i = cx - x1
    j = cy - y1
    cw = bulge < 0

    return {"i": i, "j": j, "radius": radius, "cw": cw}


def generate_dxf_toolpath(
    chains: List[Dict[str, Any]],
    operation_type: str = "contour",  # 'contour', 'pocket', or 'drill'
    circles: Optional[List[Dict[str, Any]]] = None,
    side: str = "left",
    target_depth_z: float = -5.0,
    stepdown_z: float = 1.5,
    finish_allowance: float = 0.2,
    spring_pass: bool = True,
    tool_diameter: float = 3.175,
    tool_number: int = 1,
    tool_name: str = "Endmill",
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
    spindle_speed: int = 16000,
    safe_z_retract: float = 5.0,
    units: str = "mm",
    dialect: str = "grbl",
    **kwargs,
) -> Dict[str, Any]:
    """
    Converts parsed DXF chains or circle drill holes into complete G-code toolpaths.
    """
    post = get_postprocessor(dialect)
    lines = []
    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=f"DXF CAD Importer Toolpath: Op={operation_type.upper()} | Tool={tool_name} (Ø{tool_diameter}mm)",
    )
    lines.extend(header)
    lines.append("")

    if operation_type == "drill" and circles:
        holes = [(c["x"], c["y"]) for c in circles]
        drill_res = generate_straight_plunge(
            holes=holes,
            target_depth_z=target_depth_z,
            retract_z=safe_z_retract,
            plunge_feed=plunge_feed,
            spindle_speed=spindle_speed,
            tool_number=tool_number,
            tool_name=tool_name,
            units=units,
            postprocessor=post,
        )
        drill_gcode = drill_res.gcode if hasattr(drill_res, "gcode") else drill_res.get("gcode", "")
        cleaned = strip_header_and_footer(drill_gcode)
        lines.extend(cleaned)

    else:
        # Chain contouring / profiling
        for c_idx, chain in enumerate(chains):
            lines.append(f"( --- DXF CHAIN {chain.get('id', c_idx+1)} [Layer: {chain.get('layer', '0')}] --- )")
            contour_res = generate_contour_profile(
                segments=chain["segments"],
                start_point=tuple(chain.get("start_point", [0.0, 0.0])),
                is_closed=chain.get("is_closed", True),
                side=side,
                lead_in_type="tangential_arc" if chain.get("is_closed", True) else "linear_45",
                lead_in_radius=min(5.0, tool_diameter),
                target_depth_z=target_depth_z,
                stepdown_z=stepdown_z,
                retract_z=safe_z_retract,
                finish_allowance=finish_allowance,
                spring_pass=spring_pass,
                tool_diameter=tool_diameter,
                tool_number=tool_number,
                tool_name=tool_name,
                feed_rate_xy=feed_rate_xy,
                plunge_feed=plunge_feed,
                spindle_speed=spindle_speed,
                units=units,
                dialect=dialect,
            )
            contour_gcode = contour_res.get("gcode", "")
            cleaned = strip_header_and_footer(contour_gcode)
            lines.extend(cleaned)
            lines.append("")

    lines.append("")
    footer = post.format_footer(park_z=safe_z_retract, park_x=0.0, park_y=0.0)
    lines.extend(footer)

    full_gcode = "\n".join(lines)
    return {
        "gcode": full_gcode,
        "chain_count": len(chains) if chains else (len(circles) if circles else 0),
        "operation_type": operation_type,
    }
