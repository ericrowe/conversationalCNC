import math
from typing import List, Tuple, Optional, Dict, Any
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope
from .drilling import ROUTER_DIAL_MAPS
from .engraving_font import get_glyph

def generate_text_engraving(
    text: str,
    layout_mode: str = "linear",  # "linear" or "arc"
    start_x: float = 0.0,
    start_y: float = 0.0,
    rotation_deg: float = 0.0,
    align: str = "left",  # "left", "center", "right"
    line_spacing_mult: float = 1.4,
    center_x: float = 0.0,
    center_y: float = 0.0,
    arc_radius: float = 30.0,
    start_angle_deg: float = 90.0,
    arc_direction: str = "clockwise",  # "clockwise" or "counter_clockwise"
    font_size: float = 10.0,  # Cap height in mm
    letter_spacing: float = 1.0,  # Extra spacing between characters (mm)
    font_name: str = "simplex_sans",  # Font style key
    curve_subdivisions: int = 4,  # Curve interpolation sampling steps (1=coarse, 4=smooth, 8=ultra-fine)
    target_depth_z: float = -0.5,




    stepdown_z: float = 0.5,
    start_z: float = 0.0,
    retract_z: float = 2.0,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 300.0,
    rapid_feed: float = 5000.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    units: str = "mm",
    tool_number: int = 1,
    tool_name: str = "",
    tool_diameter: float = 3.175,
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
    Pure Python G-Code Generator for Text Engraving.
    
    Converts text into stroke vector polylines using embedded single-line vector font glyphs,
    supporting both linear and circular arc layouts with multi-pass Z stepdowns.
    """
    if not text:
        raise ValueError("Engraving text cannot be empty.")

    if font_size <= 0:
        raise ValueError("Font size must be greater than zero.")

    if feed_rate_xy <= 0:
        raise ValueError("Cutting feed rate must be greater than zero.")

    if plunge_feed <= 0:
        raise ValueError("Plunge feed rate must be greater than zero.")

    if stepdown_z <= 0:
        raise ValueError("Stepdown (Z) must be greater than zero.")

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

    final_target_z = start_z - abs(target_depth_z)
    effective_retract_z = max(retract_z, start_z + 0.5)
    total_depth = abs(start_z - final_target_z)

    num_z_passes = max(1, int(math.ceil(total_depth / stepdown_z)))
    actual_stepdown = total_depth / num_z_passes

    # Normalized font grid scale (nominal cap height = 10.0 units)
    scale = font_size / 10.0

    # 1. Compute Polylines for Text
    polylines: List[List[Tuple[float, float]]] = []

    if layout_mode == "arc":
        # Arc / Circular Text Layout
        if arc_radius <= 0:
            raise ValueError("Arc radius must be greater than zero.")

        # Strip line breaks for arc text (single line wrapped around arc)
        arc_text = text.replace("\n", " ").strip()
        glyphs = [get_glyph(c, font_name=font_name, curve_subdivisions=curve_subdivisions) for c in arc_text]

        # Calculate character advance positions along the arc
        char_widths = [g["w"] * scale + letter_spacing for g in glyphs]
        total_arc_len = sum(char_widths)
        total_angle_rad = total_arc_len / arc_radius

        start_angle_rad = math.radians(start_angle_deg)
        is_cw = (arc_direction == "clockwise")

        # Alignment along the arc
        if align == "center":
            base_angle_rad = start_angle_rad + (total_angle_rad / 2.0 if is_cw else -total_angle_rad / 2.0)
        elif align == "right":
            base_angle_rad = start_angle_rad + (total_angle_rad if is_cw else -total_angle_rad)
        else:  # left
            base_angle_rad = start_angle_rad

        curr_dist = 0.0
        for i, char in enumerate(arc_text):
            g = glyphs[i]
            char_w = g["w"] * scale
            char_center_dist = curr_dist + (char_w / 2.0)
            char_angle = base_angle_rad - (char_center_dist / arc_radius) if is_cw else base_angle_rad + (char_center_dist / arc_radius)

            # Transform each stroke of the character
            for stroke in g["strokes"]:
                poly: List[Tuple[float, float]] = []
                for (gx, gy) in stroke:
                    # Tangent offset from character center
                    t_offset = (gx - g["w"] / 2.0) * scale
                    t_angle_delta = (t_offset / arc_radius) if not is_cw else (-t_offset / arc_radius)
                    pt_angle = char_angle + t_angle_delta

                    # Radial offset (baseline is at arc_radius)
                    pt_radius = arc_radius + (gy * scale)

                    px = center_x + pt_radius * math.cos(pt_angle)
                    py = center_y + pt_radius * math.sin(pt_angle)
                    poly.append((round(px, 3), round(py, 3)))
                if poly:
                    polylines.append(poly)

            curr_dist += char_w + letter_spacing

    else:
        # Linear Text Layout (supports multi-line and rotation)
        rad_rot = math.radians(rotation_deg)
        cos_rot = math.cos(rad_rot)
        sin_rot = math.sin(rad_rot)

        lines_text = text.split("\n")
        for line_idx, line_str in enumerate(lines_text):
            glyphs = [get_glyph(c, font_name=font_name, curve_subdivisions=curve_subdivisions) for c in line_str]
            char_widths = [g["w"] * scale + letter_spacing for g in glyphs]
            line_width = sum(char_widths) - (letter_spacing if char_widths else 0.0)



            # Alignment offset along line
            if align == "center":
                align_x_offset = -line_width / 2.0
            elif align == "right":
                align_x_offset = -line_width
            else:  # left
                align_x_offset = 0.0

            line_y_offset = -line_idx * (font_size * line_spacing_mult)

            curr_char_x = 0.0
            for i, char in enumerate(line_str):
                g = glyphs[i]
                for stroke in g["strokes"]:
                    poly = []
                    for (gx, gy) in stroke:
                        # Local unrotated coordinate relative to text origin
                        lx = align_x_offset + curr_char_x + (gx * scale)
                        ly = line_y_offset + (gy * scale)

                        # Apply rotation and translation
                        rx = start_x + (lx * cos_rot - ly * sin_rot)
                        ry = start_y + (lx * sin_rot + ly * cos_rot)
                        poly.append((round(rx, 3), round(ry, 3)))
                    if poly:
                        polylines.append(poly)

                curr_char_x += (g["w"] * scale) + letter_spacing

    if not polylines:
        raise ValueError("No printable strokes generated for the specified text.")

    # 2. Header & Safe Setup
    lines: List[str] = []
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: Text Engraving ('{text[:20]}...', Size={font_size:.1f}mm, Depth={total_depth:.2f}mm)",
        )
    )

    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"V-Bit / Engraving Bit D{tool_diameter:.2f}mm",
        )
    )

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
    lines.append(postprocessor.format_rapid(z=effective_retract_z, comment="Safe Z clearance"))

    # Track bounds
    all_pts_x = [pt[0] for poly in polylines for pt in poly]
    all_pts_y = [pt[1] for poly in polylines for pt in poly]
    min_cut_x = min(all_pts_x)
    max_cut_x = max(all_pts_x)
    min_cut_y = min(all_pts_y)
    max_cut_y = max(all_pts_y)

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

    # 3. Generate Toolpath (Z passes)
    for z_step in range(1, num_z_passes + 1):
        curr_layer_z = start_z - (z_step * actual_stepdown)
        if z_step == num_z_passes:
            curr_layer_z = final_target_z

        lines.append(f"(--- Z Layer {z_step}/{num_z_passes} at Z{curr_layer_z:.3f} ---)")

        for s_idx, poly in enumerate(polylines, start=1):
            start_pt = poly[0]

            # Rapid to stroke start at clearance
            lines.append(postprocessor.format_rapid(x=start_pt[0], y=start_pt[1]))
            lines.append(postprocessor.format_rapid(z=start_z + 0.5))
            lines.append(postprocessor.format_linear(z=curr_layer_z, feed_rate=plunge_feed))

            total_rapid_dist += math.hypot(start_pt[0] - current_x, start_pt[1] - current_y)
            total_feed_dist += abs(start_z + 0.5 - curr_layer_z)

            current_x, current_y = start_pt
            current_z = curr_layer_z

            # Feed along stroke points
            for pt in poly[1:]:
                lines.append(postprocessor.format_linear(x=pt[0], y=pt[1], feed_rate=feed_rate_xy))
                total_feed_dist += math.hypot(pt[0] - current_x, pt[1] - current_y)
                current_x, current_y = pt

            # Rapid lift at end of stroke
            lines.append(postprocessor.format_rapid(z=effective_retract_z))
            total_rapid_dist += abs(effective_retract_z - curr_layer_z)
            current_z = effective_retract_z

        lines.append("")

    # 4. Program Footer / Park
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
