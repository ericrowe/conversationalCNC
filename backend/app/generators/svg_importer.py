"""
Pure Python SVG 2D Vector CAD Importer Engine with Grayscale Shading to Depth Mapping.
Parses standard SVG XML files without external binary C-dependencies, extracting
vector paths (<path>, <rect>, <circle>, <ellipse>, <line>, <polyline>, <polygon>),
evaluates fill/stroke grayscale shading (% luminance) into proportional Z cut depths,
and synthesizes 2.5D stepped contouring and drilling CNC G-code programs.
"""
import re
import math
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Optional
from .base import BoundingBox, GCodeProgram, strip_header_and_footer
from .contouring import generate_contour_profile
from .drilling import generate_straight_plunge, generate_peck_drilling
from ..postprocessors import get_postprocessor


# Standard CSS Color Map
NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211),
    "darkgray": (169, 169, 169),
    "darkgrey": (169, 169, 169),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
}


def parse_color_to_luminance(color_str: Optional[str], opacity: float = 1.0) -> Tuple[float, str]:
    """
    Parses a color string (hex, rgb, named) and opacity into a normalized ITU-R BT.601
    luminance float in [0.0, 1.0] (0.0 = pure black, 1.0 = pure white).
    Returns (luminance, canonical_color_string).
    """
    if not color_str or color_str.strip().lower() in ("none", "transparent", ""):
        return 1.0, "none"

    c = color_str.strip().lower()
    r, g, b = 0, 0, 0

    if c.startswith("#"):
        hex_digits = c[1:]
        if len(hex_digits) == 3:
            r = int(hex_digits[0] * 2, 16)
            g = int(hex_digits[1] * 2, 16)
            b = int(hex_digits[2] * 2, 16)
        elif len(hex_digits) == 6 or len(hex_digits) == 8:
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
        else:
            r, g, b = 0, 0, 0
    elif c.startswith("rgb"):
        nums = re.findall(r"[-+]?\d*\.?\d+", c)
        if len(nums) >= 3:
            if "%" in c:
                r = int(float(nums[0]) * 2.55)
                g = int(float(nums[1]) * 2.55)
                b = int(float(nums[2]) * 2.55)
            else:
                r = int(float(nums[0]))
                g = int(float(nums[1]))
                b = int(float(nums[2]))
    elif c.startswith("hsl"):
        nums = re.findall(r"[-+]?\d*\.?\d+", c)
        if len(nums) >= 3:
            h = float(nums[0]) % 360
            s = float(nums[1]) / 100.0
            l = float(nums[2]) / 100.0
            c_val = (1.0 - abs(2.0 * l - 1.0)) * s
            x_val = c_val * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
            m_val = l - c_val / 2.0
            if 0 <= h < 60:
                r1, g1, b1 = c_val, x_val, 0
            elif 60 <= h < 120:
                r1, g1, b1 = x_val, c_val, 0
            elif 120 <= h < 180:
                r1, g1, b1 = 0, c_val, x_val
            elif 180 <= h < 240:
                r1, g1, b1 = 0, x_val, c_val
            elif 240 <= h < 300:
                r1, g1, b1 = x_val, 0, c_val
            else:
                r1, g1, b1 = c_val, 0, x_val
            r = int((r1 + m_val) * 255)
            g = int((g1 + m_val) * 255)
            b = int((b1 + m_val) * 255)
    elif c in NAMED_COLORS:
        r, g, b = NAMED_COLORS[c]
    else:
        r, g, b = 0, 0, 0

    # BT.601 standard perceptual luminance formula
    raw_lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    # Factor in opacity: lower opacity blends with white background (increases luminance towards 1.0)
    effective_lum = raw_lum * opacity + (1.0 - opacity) * 1.0
    effective_lum = max(0.0, min(1.0, effective_lum))

    hex_canonical = f"#{r:02x}{g:02x}{b:02x}"
    return effective_lum, hex_canonical


def parse_svg_length(val: Optional[str], default_dpi: float = 96.0) -> Optional[float]:
    """
    Converts an SVG length attribute string ('100', '50mm', '2in', '10pt') into millimeters.
    """
    if not val:
        return None
    val_clean = val.strip().lower()
    if val_clean.endswith("mm"):
        return float(val_clean[:-2])
    elif val_clean.endswith("in"):
        return float(val_clean[:-2]) * 25.4
    elif val_clean.endswith("cm"):
        return float(val_clean[:-2]) * 10.0
    elif val_clean.endswith("pt"):
        return float(val_clean[:-2]) * (25.4 / 72.0)
    elif val_clean.endswith("px"):
        return float(val_clean[:-2]) * (25.4 / default_dpi)
    else:
        try:
            return float(val_clean) * (25.4 / default_dpi)
        except ValueError:
            return None


def tokenize_svg_path(d: str) -> List[Tuple[str, List[float]]]:
    """
    Tokenizes an SVG path 'd' string into commands and argument lists.
    Handles condensed notation (e.g. M10-20L.5.5, scientific notation).
    """
    cmd_regex = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])")
    num_regex = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")

    tokens: List[Tuple[str, List[float]]] = []
    chunks = cmd_regex.split(d)

    current_cmd = None
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if cmd_regex.match(chunk):
            current_cmd = chunk
            if current_cmd in ("Z", "z"):
                tokens.append((current_cmd, []))
        elif current_cmd:
            nums = [float(n) for n in num_regex.findall(chunk)]
            tokens.append((current_cmd, nums))

    return tokens


def subdivide_cubic_bezier(p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], steps: int = 12) -> List[Tuple[float, float]]:
    """Subdivides a cubic Bezier curve into points."""
    pts = []
    for step in range(1, steps + 1):
        t = step / float(steps)
        t_inv = 1.0 - t
        x = (t_inv ** 3) * p0[0] + 3 * (t_inv ** 2) * t * p1[0] + 3 * t_inv * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        y = (t_inv ** 3) * p0[1] + 3 * (t_inv ** 2) * t * p1[1] + 3 * t_inv * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        pts.append((x, y))
    return pts


def subdivide_quadratic_bezier(p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float], steps: int = 8) -> List[Tuple[float, float]]:
    """Subdivides a quadratic Bezier curve into points."""
    pts = []
    for step in range(1, steps + 1):
        t = step / float(steps)
        t_inv = 1.0 - t
        x = (t_inv ** 2) * p0[0] + 2 * t_inv * t * p1[0] + (t ** 2) * p2[0]
        y = (t_inv ** 2) * p0[1] + 2 * t_inv * t * p1[1] + (t ** 2) * p2[1]
        pts.append((x, y))
    return pts


def parse_style_attribute(elem: ET.Element) -> Dict[str, str]:
    """Extracts style attributes and direct element attributes."""
    styles: Dict[str, str] = {}
    style_attr = elem.attrib.get("style", "")
    if style_attr:
        pairs = style_attr.split(";")
        for pair in pairs:
            if ":" in pair:
                k, v = pair.split(":", 1)
                styles[k.strip().lower()] = v.strip()

    for key in ("fill", "stroke", "opacity", "fill-opacity", "stroke-opacity"):
        if key in elem.attrib and key not in styles:
            styles[key] = elem.attrib[key].strip()

    return styles


def parse_svg(
    svg_text: str,
    default_dpi: float = 96.0,
    flip_y: bool = True,
    max_cut_depth: float = -6.0,
    invert_shading: bool = False,
    shading_mode: str = "fill",
) -> Dict[str, Any]:
    """
    Parses SVG XML vector data into chains, circles, bounding boxes, and calculates
    depths based on grayscale shading percentage.
    """
    clean_text = re.sub(r'xmlns="[^"]+"', "", svg_text)
    root = ET.fromstring(clean_text)

    # Determine Canvas dimensions & viewBox
    viewbox_str = root.attrib.get("viewBox", "")
    vb_min_x, vb_min_y, vb_w, vb_h = 0.0, 0.0, None, None
    if viewbox_str:
        vb_parts = [float(p) for p in re.findall(r"[-+]?\d*\.?\d+", viewbox_str)]
        if len(vb_parts) == 4:
            vb_min_x, vb_min_y, vb_w, vb_h = vb_parts

    width_mm = parse_svg_length(root.attrib.get("width"), default_dpi)
    height_mm = parse_svg_length(root.attrib.get("height"), default_dpi)

    scale_x = 25.4 / default_dpi
    scale_y = 25.4 / default_dpi

    if width_mm and vb_w and vb_w > 0:
        scale_x = width_mm / vb_w
    if height_mm and vb_h and vb_h > 0:
        scale_y = height_mm / vb_h

    chains: List[Dict[str, Any]] = []
    circles: List[Dict[str, Any]] = []

    all_x: List[float] = []
    all_y: List[float] = []

    chain_id_counter = 1

    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower()
        if tag not in ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon"):
            continue

        styles = parse_style_attribute(elem)
        fill = styles.get("fill", "black")
        stroke = styles.get("stroke", "none")
        opacity = float(styles.get("opacity", 1.0))
        fill_opacity = float(styles.get("fill-opacity", 1.0)) * opacity
        stroke_opacity = float(styles.get("stroke-opacity", 1.0)) * opacity

        if shading_mode == "stroke" and stroke != "none":
            lum, hex_color = parse_color_to_luminance(stroke, stroke_opacity)
        else:
            lum, hex_color = parse_color_to_luminance(fill if fill != "none" else stroke, fill_opacity)

        if invert_shading:
            shading_pct = lum * 100.0
        else:
            shading_pct = (1.0 - lum) * 100.0

        depth_ratio = shading_pct / 100.0
        calc_depth_z = -abs(max_cut_depth) * depth_ratio

        if tag == "circle":
            cx = (float(elem.attrib.get("cx", 0.0)) - vb_min_x) * scale_x
            cy = (float(elem.attrib.get("cy", 0.0)) - vb_min_y) * scale_y
            r = float(elem.attrib.get("r", 1.0)) * ((scale_x + scale_y) / 2.0)
            circles.append({
                "x": round(cx, 4),
                "y": round(cy, 4),
                "radius": round(r, 4),
                "diameter": round(r * 2.0, 4),
                "fill": hex_color,
                "luminance": round(lum, 3),
                "shading_percent": round(shading_pct, 1),
                "target_depth_z": round(calc_depth_z, 3),
            })
            all_x.extend([cx - r, cx + r])
            all_y.extend([cy - r, cy + r])
            continue

        elif tag == "rect":
            rx_pos = (float(elem.attrib.get("x", 0.0)) - vb_min_x) * scale_x
            ry_pos = (float(elem.attrib.get("y", 0.0)) - vb_min_y) * scale_y
            rw = float(elem.attrib.get("width", 0.0)) * scale_x
            rh = float(elem.attrib.get("height", 0.0)) * scale_y

            p1 = (rx_pos, ry_pos)
            p2 = (rx_pos + rw, ry_pos)
            p3 = (rx_pos + rw, ry_pos + rh)
            p4 = (rx_pos, ry_pos + rh)

            segments = [
                {"type": "line", "x": p2[0], "y": p2[1], "i": 0.0, "j": 0.0, "cw": False},
                {"type": "line", "x": p3[0], "y": p3[1], "i": 0.0, "j": 0.0, "cw": False},
                {"type": "line", "x": p4[0], "y": p4[1], "i": 0.0, "j": 0.0, "cw": False},
                {"type": "line", "x": p1[0], "y": p1[1], "i": 0.0, "j": 0.0, "cw": False},
            ]

            chains.append({
                "id": chain_id_counter,
                "tag": "rect",
                "fill": hex_color,
                "luminance": round(lum, 3),
                "shading_percent": round(shading_pct, 1),
                "target_depth_z": round(calc_depth_z, 3),
                "is_closed": True,
                "start_point": [round(p1[0], 4), round(p1[1], 4)],
                "segments": segments,
                "segment_count": len(segments),
            })
            chain_id_counter += 1
            all_x.extend([rx_pos, rx_pos + rw])
            all_y.extend([ry_pos, ry_pos + rh])
            continue

        elif tag == "line":
            x1 = (float(elem.attrib.get("x1", 0.0)) - vb_min_x) * scale_x
            y1 = (float(elem.attrib.get("y1", 0.0)) - vb_min_y) * scale_y
            x2 = (float(elem.attrib.get("x2", 0.0)) - vb_min_x) * scale_x
            y2 = (float(elem.attrib.get("y2", 0.0)) - vb_min_y) * scale_y

            segments = [{"type": "line", "x": x2, "y": y2, "i": 0.0, "j": 0.0, "cw": False}]
            chains.append({
                "id": chain_id_counter,
                "tag": "line",
                "fill": hex_color,
                "luminance": round(lum, 3),
                "shading_percent": round(shading_pct, 1),
                "target_depth_z": round(calc_depth_z, 3),
                "is_closed": False,
                "start_point": [round(x1, 4), round(y1, 4)],
                "segments": segments,
                "segment_count": 1,
            })
            chain_id_counter += 1
            all_x.extend([x1, x2])
            all_y.extend([y1, y2])
            continue

        elif tag in ("polyline", "polygon"):
            points_str = elem.attrib.get("points", "")
            coords = [float(c) for c in re.findall(r"[-+]?\d*\.?\d+", points_str)]
            if len(coords) >= 4:
                pts = []
                for k in range(0, len(coords) - 1, 2):
                    px = (coords[k] - vb_min_x) * scale_x
                    py = (coords[k + 1] - vb_min_y) * scale_y
                    pts.append((px, py))
                    all_x.append(px)
                    all_y.append(py)

                segments = []
                for pt in pts[1:]:
                    segments.append({"type": "line", "x": pt[0], "y": pt[1], "i": 0.0, "j": 0.0, "cw": False})

                is_poly = tag == "polygon"
                if is_poly:
                    segments.append({"type": "line", "x": pts[0][0], "y": pts[0][1], "i": 0.0, "j": 0.0, "cw": False})

                chains.append({
                    "id": chain_id_counter,
                    "tag": tag,
                    "fill": hex_color,
                    "luminance": round(lum, 3),
                    "shading_percent": round(shading_pct, 1),
                    "target_depth_z": round(calc_depth_z, 3),
                    "is_closed": is_poly,
                    "start_point": [round(pts[0][0], 4), round(pts[0][1], 4)],
                    "segments": segments,
                    "segment_count": len(segments),
                })
                chain_id_counter += 1
            continue

        elif tag == "path":
            d = elem.attrib.get("d", "")
            if not d:
                continue

            tokens = tokenize_svg_path(d)
            cur_x, cur_y = 0.0, 0.0
            start_x, start_y = 0.0, 0.0
            path_segments = []
            chain_start = None
            is_closed = False

            for cmd, nums in tokens:
                if cmd in ("M", "m"):
                    if path_segments and chain_start is not None:
                        chains.append({
                            "id": chain_id_counter,
                            "tag": "path",
                            "fill": hex_color,
                            "luminance": round(lum, 3),
                            "shading_percent": round(shading_pct, 1),
                            "target_depth_z": round(calc_depth_z, 3),
                            "is_closed": is_closed,
                            "start_point": [round(chain_start[0], 4), round(chain_start[1], 4)],
                            "segments": path_segments,
                            "segment_count": len(path_segments),
                        })
                        chain_id_counter += 1
                        path_segments = []
                        is_closed = False

                    is_rel = cmd == "m"
                    if len(nums) >= 2:
                        target_x = cur_x + nums[0] if is_rel else nums[0]
                        target_y = cur_y + nums[1] if is_rel else nums[1]
                        cur_x = (target_x - vb_min_x) * scale_x
                        cur_y = (target_y - vb_min_y) * scale_y
                        start_x, start_y = cur_x, cur_y
                        chain_start = (cur_x, cur_y)
                        all_x.append(cur_x)
                        all_y.append(cur_y)

                        for idx in range(2, len(nums) - 1, 2):
                            tx = cur_x + nums[idx] * scale_x if is_rel else (nums[idx] - vb_min_x) * scale_x
                            ty = cur_y + nums[idx + 1] * scale_y if is_rel else (nums[idx + 1] - vb_min_y) * scale_y
                            path_segments.append({"type": "line", "x": tx, "y": ty, "i": 0.0, "j": 0.0, "cw": False})
                            cur_x, cur_y = tx, ty
                            all_x.append(cur_x)
                            all_y.append(cur_y)

                elif cmd in ("L", "l"):
                    is_rel = cmd == "l"
                    for idx in range(0, len(nums) - 1, 2):
                        tx = cur_x + nums[idx] * scale_x if is_rel else (nums[idx] - vb_min_x) * scale_x
                        ty = cur_y + nums[idx + 1] * scale_y if is_rel else (nums[idx + 1] - vb_min_y) * scale_y
                        path_segments.append({"type": "line", "x": tx, "y": ty, "i": 0.0, "j": 0.0, "cw": False})
                        cur_x, cur_y = tx, ty
                        all_x.append(cur_x)
                        all_y.append(cur_y)

                elif cmd in ("H", "h"):
                    is_rel = cmd == "h"
                    for val in nums:
                        tx = cur_x + val * scale_x if is_rel else (val - vb_min_x) * scale_x
                        path_segments.append({"type": "line", "x": tx, "y": cur_y, "i": 0.0, "j": 0.0, "cw": False})
                        cur_x = tx
                        all_x.append(cur_x)

                elif cmd in ("V", "v"):
                    is_rel = cmd == "v"
                    for val in nums:
                        ty = cur_y + val * scale_y if is_rel else (val - vb_min_y) * scale_y
                        path_segments.append({"type": "line", "x": cur_x, "y": ty, "i": 0.0, "j": 0.0, "cw": False})
                        cur_y = ty
                        all_y.append(cur_y)

                elif cmd in ("C", "c"):
                    is_rel = cmd == "c"
                    for idx in range(0, len(nums) - 5, 6):
                        x1 = cur_x + nums[idx] * scale_x if is_rel else (nums[idx] - vb_min_x) * scale_x
                        y1 = cur_y + nums[idx + 1] * scale_y if is_rel else (nums[idx + 1] - vb_min_y) * scale_y
                        x2 = cur_x + nums[idx + 2] * scale_x if is_rel else (nums[idx + 2] - vb_min_x) * scale_x
                        y2 = cur_y + nums[idx + 3] * scale_y if is_rel else (nums[idx + 3] - vb_min_y) * scale_y
                        x3 = cur_x + nums[idx + 4] * scale_x if is_rel else (nums[idx + 4] - vb_min_x) * scale_x
                        y3 = cur_y + nums[idx + 5] * scale_y if is_rel else (nums[idx + 5] - vb_min_y) * scale_y

                        sub_pts = subdivide_cubic_bezier((cur_x, cur_y), (x1, y1), (x2, y2), (x3, y3), steps=10)
                        for sp in sub_pts:
                            path_segments.append({"type": "line", "x": sp[0], "y": sp[1], "i": 0.0, "j": 0.0, "cw": False})
                            all_x.append(sp[0])
                            all_y.append(sp[1])
                        cur_x, cur_y = x3, y3

                elif cmd in ("Q", "q"):
                    is_rel = cmd == "q"
                    for idx in range(0, len(nums) - 3, 4):
                        x1 = cur_x + nums[idx] * scale_x if is_rel else (nums[idx] - vb_min_x) * scale_x
                        y1 = cur_y + nums[idx + 1] * scale_y if is_rel else (nums[idx + 1] - vb_min_y) * scale_y
                        x2 = cur_x + nums[idx + 2] * scale_x if is_rel else (nums[idx + 2] - vb_min_x) * scale_x
                        y2 = cur_y + nums[idx + 3] * scale_y if is_rel else (nums[idx + 3] - vb_min_y) * scale_y

                        sub_pts = subdivide_quadratic_bezier((cur_x, cur_y), (x1, y1), (x2, y2), steps=8)
                        for sp in sub_pts:
                            path_segments.append({"type": "line", "x": sp[0], "y": sp[1], "i": 0.0, "j": 0.0, "cw": False})
                            all_x.append(sp[0])
                            all_y.append(sp[1])
                        cur_x, cur_y = x2, y2

                elif cmd in ("Z", "z"):
                    is_closed = True
                    if abs(cur_x - start_x) > 0.01 or abs(cur_y - start_y) > 0.01:
                        path_segments.append({"type": "line", "x": start_x, "y": start_y, "i": 0.0, "j": 0.0, "cw": False})
                        cur_x, cur_y = start_x, start_y

            if path_segments and chain_start is not None:
                chains.append({
                    "id": chain_id_counter,
                    "tag": "path",
                    "fill": hex_color,
                    "luminance": round(lum, 3),
                    "shading_percent": round(shading_pct, 1),
                    "target_depth_z": round(calc_depth_z, 3),
                    "is_closed": is_closed,
                    "start_point": [round(chain_start[0], 4), round(chain_start[1], 4)],
                    "segments": path_segments,
                    "segment_count": len(path_segments),
                })
                chain_id_counter += 1

    # Apply Flip-Y if enabled (SVG screen Y down -> CNC Cartesian Y up)
    if flip_y and all_y:
        max_y_val = max(all_y)
        min_y_val = min(all_y)

        for ch in chains:
            ch["start_point"][1] = round(max_y_val - (ch["start_point"][1] - min_y_val), 4)
            for seg in ch["segments"]:
                seg["y"] = round(max_y_val - (seg["y"] - min_y_val), 4)
                if seg.get("j"):
                    seg["j"] = -seg["j"]

        for circ in circles:
            circ["y"] = round(max_y_val - (circ["y"] - min_y_val), 4)

        all_y = [max_y_val - (y - min_y_val) for y in all_y]

    if all_x and all_y:
        bbox = {
            "min_x": round(min(all_x), 3),
            "max_x": round(max(all_x), 3),
            "min_y": round(min(all_y), 3),
            "max_y": round(max(all_y), 3),
            "width": round(max(all_x) - min(all_x), 3),
            "height": round(max(all_y) - min(all_y), 3),
        }
    else:
        bbox = {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0, "width": 0.0, "height": 0.0}

    return {
        "chains": chains,
        "circles": circles,
        "bounding_box": bbox,
        "entity_count": len(chains) + len(circles),
        "units": "mm",
    }


def generate_svg_toolpath(
    chains: List[Dict[str, Any]],
    circles: Optional[List[Dict[str, Any]]] = None,
    operation_type: str = "contour",
    side: str = "left",
    target_depth_z: Optional[float] = None,
    stepdown_z: float = 1.5,
    finish_allowance: float = 0.0,
    spring_pass: bool = False,
    tool_diameter: float = 3.175,
    tool_number: int = 1,
    tool_name: str = "Endmill",
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
    spindle_speed: int = 16000,
    safe_z_retract: float = 5.0,
    lead_in_type: str = "tangential_arc",
    use_grayscale_depths: bool = True,
    units: str = "mm",
    dialect: str = "grbl",
    postprocessor=None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Synthesizes CNC G-code toolpaths from parsed SVG chains and circles.
    Respects individual grayscale shading depths when use_grayscale_depths is True.
    """
    post = postprocessor or get_postprocessor(dialect)

    circles = circles or []
    lines: List[str] = []

    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=f"SVG Vector Importer Toolpath: Op={operation_type.upper()} | Tool={tool_name} (Ø{tool_diameter}mm)",
    )
    lines.extend(header)
    lines.append("")

    executed_chains = 0
    executed_holes = 0

    # 1. Generate Contouring Toolpaths for Chains
    if operation_type in ("contour", "auto") and chains:
        for idx, chain in enumerate(chains):
            if use_grayscale_depths and "target_depth_z" in chain:
                chain_depth = chain["target_depth_z"]
            elif target_depth_z is not None:
                chain_depth = -abs(target_depth_z)
            else:
                chain_depth = -abs(stepdown_z)

            # Skip 0-depth passes
            if abs(chain_depth) < 0.001:
                continue

            shading_label = f"Shading={chain.get('shading_percent', 100.0)}% ({chain.get('fill', '#000')})"
            lines.append(f"\n( --- SVG CHAIN {idx + 1} [{chain.get('tag', 'path').upper()} | {shading_label} | Depth Z={chain_depth:.3f}mm] --- )")

            contour_segments = []
            for seg in chain["segments"]:
                contour_segments.append({
                    "type": seg.get("type", "line"),
                    "x": seg["x"],
                    "y": seg["y"],
                    "i": seg.get("i", 0.0),
                    "j": seg.get("j", 0.0),
                    "cw": seg.get("cw", False),
                })

            contour_res = generate_contour_profile(
                segments=chain["segments"],
                start_point=tuple(chain.get("start_point", [0.0, 0.0])),
                is_closed=chain.get("is_closed", False),
                side=side if chain.get("is_closed", False) else "center",
                lead_in_type=lead_in_type if chain.get("is_closed", False) else "direct",
                lead_in_radius=min(5.0, tool_diameter),
                target_depth_z=chain_depth,
                stepdown_z=stepdown_z,
                retract_z=safe_z_retract,
                finish_allowance=finish_allowance if chain.get("is_closed", False) else 0.0,
                spring_pass=spring_pass if chain.get("is_closed", False) else False,
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
            executed_chains += 1

    # 2. Generate Drill Toolpaths for Circles
    if operation_type in ("drill", "auto") and circles:
        holes_by_depth: Dict[float, List[Tuple[float, float]]] = {}
        for c in circles:
            if use_grayscale_depths and "target_depth_z" in c:
                hole_depth = c["target_depth_z"]
            elif target_depth_z is not None:
                hole_depth = -abs(target_depth_z)
            else:
                hole_depth = -abs(stepdown_z)

            if abs(hole_depth) < 0.001:
                continue

            rounded_depth = round(hole_depth, 3)
            if rounded_depth not in holes_by_depth:
                holes_by_depth[rounded_depth] = []
            holes_by_depth[rounded_depth].append((c["x"], c["y"]))

        for h_depth, hole_coords in holes_by_depth.items():
            lines.append(f"( --- SVG DRILL HOLES [Count={len(hole_coords)} | Target Depth Z={h_depth:.3f}mm] --- )")
            drill_res = generate_straight_plunge(
                holes=hole_coords,
                target_depth_z=h_depth,
                retract_z=safe_z_retract,
                plunge_feed=plunge_feed,
                spindle_speed=spindle_speed,
                tool_number=tool_number,
                tool_name=tool_name,
                units=units,
                postprocessor=post,
            )
            drill_gcode = drill_res.gcode if hasattr(drill_res, "gcode") else drill_res.get("gcode", "")
            cleaned_drill = strip_header_and_footer(drill_gcode)
            lines.extend(cleaned_drill)
            lines.append("")
            executed_holes += len(hole_coords)

    lines.append("")
    footer = post.format_footer(
        park_z=safe_z_retract,
        park_x=0.0,
        park_y=0.0,
    )


    lines.extend(footer)


    full_gcode = "\n".join(lines)
    return {
        "gcode": full_gcode,
        "chain_count": executed_chains,
        "hole_count": executed_holes,
        "operation_type": operation_type,
    }

