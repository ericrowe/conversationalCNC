"""
2D Chamfering & Edge Breaking G-Code Generator.
Supports:
- Outer and Inner Rectangular perimeter chamfering (with corner fillets)
- Circular perimeter chamfering (boss or bore, emitted as two 180° G2/G3 semicircles)
- Tool geometry calculation for 45°, 60°, 90°, 120° V-bits and chamfer mills
- Safe tip-offset to avoid cutting at the dead center of the tool
- Smooth tangential arc lead-in and lead-out
- Grbl and Standard controller dialects
"""
import math
from typing import List, Tuple, Optional
from ..postprocessors.base import BasePostProcessor
from ..postprocessors.grbl import GrblPostProcessor
from ..postprocessors import get_postprocessor
from .base import BoundingBox, GCodeProgram, WorkEnvelope, normalize_units
from .rectangular_pocket import _get_corner_path

ROUTER_DIAL_MAPS = {
    "dewalt_611": {1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000},
    "makita_rt0701": {1: 10000, 2: 12000, 3: 17000, 4: 22000, 5: 27000, 6: 30000},
}


def calculate_chamfer_depth_and_offset(
    chamfer_width: float,
    vbit_angle_deg: float = 90.0,
    tip_diameter: float = 0.2,
    tip_offset: float = 0.5,
) -> Tuple[float, float]:
    """
    Calculates the required Z cutting depth and radial toolpath offset
    to machine a chamfer of specified width using a conical chamfer mill / V-bit.
    """
    if chamfer_width <= 0:
        raise ValueError("Chamfer width must be greater than zero.")
    if vbit_angle_deg <= 0 or vbit_angle_deg >= 180.0:
        raise ValueError("V-bit included angle must be between 0 and 180 degrees.")
    if tip_diameter < 0:
        raise ValueError("Tip diameter cannot be negative.")
    if tip_offset < 0:
        raise ValueError("Tip offset cannot be negative.")

    half_angle_rad = math.radians(vbit_angle_deg / 2.0)
    tan_half = math.tan(half_angle_rad)

    cutting_depth_z = -abs(chamfer_width / tan_half + tip_offset)
    radial_offset = (tip_diameter / 2.0) + (tip_offset * tan_half)

    return (round(cutting_depth_z, 4), round(radial_offset, 4))


def generate_rectangular_chamfer(
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    length_x: float = 50.0,
    width_y: float = 50.0,
    chamfer_width: float = 0.5,
    corner_radius: float = 0.0,
    origin_mode: str = "center",  # "center" or "corner"
    feature_type: str = "outside",  # "outside" (boss/perimeter) or "inside" (pocket/hole)
    vbit_angle_deg: float = 90.0,
    tip_diameter: float = 0.2,
    tip_offset: float = 0.5,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 1000.0,
    plunge_feed: float = 300.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    units: str = "mm",
    tool_number: int = 1,
    tool_name: str = "",
    spindle_type: str = "router",
    router_model: Optional[str] = "dewalt_611",
    router_dial: Optional[int] = None,
    postprocessor: Optional[BasePostProcessor] = None,
    work_envelope: Optional[WorkEnvelope] = None,
    park_x: Optional[float] = 0.0,
    park_y: Optional[float] = 0.0,
    park_z: Optional[float] = None,
) -> GCodeProgram:
    """
    Generates G-code for chamfering a rectangular perimeter or pocket rim.
    """
    if chamfer_width <= 0:
        raise ValueError("Chamfer width must be greater than zero.")
    if length_x <= 0 or width_y <= 0:
        raise ValueError("Length and width must be greater than zero.")

    depth_rel_z, radial_offset = calculate_chamfer_depth_and_offset(
        chamfer_width=chamfer_width,
        vbit_angle_deg=vbit_angle_deg,
        tip_diameter=tip_diameter,
        tip_offset=tip_offset,
    )
    depth_z = start_z + depth_rel_z

    if origin_mode == "center":
        min_x = origin_x - length_x / 2.0
        max_x = origin_x + length_x / 2.0
        min_y = origin_y - width_y / 2.0
        max_y = origin_y + width_y / 2.0
    else:
        min_x = origin_x
        max_x = origin_x + length_x
        min_y = origin_y
        max_y = origin_y + width_y

    eff_r = max(0.0, min(corner_radius, min(length_x, width_y) / 2.0))

    if feature_type == "outside":
        path_min_x = min_x - radial_offset
        path_max_x = max_x + radial_offset
        path_min_y = min_y - radial_offset
        path_max_y = max_y + radial_offset
        path_r = eff_r + radial_offset
    else:
        path_min_x = min_x + radial_offset
        path_max_x = max_x - radial_offset
        path_min_y = min_y + radial_offset
        path_max_y = max_y - radial_offset
        if path_min_x >= path_max_x or path_min_y >= path_max_y:
            raise ValueError("Inside pocket dimensions are too small for the requested chamfer offset.")
        path_r = max(0.0, eff_r - radial_offset)

    pts = _get_corner_path(path_min_x, path_max_x, path_min_y, path_max_y, path_r)

    if postprocessor is None:
        postprocessor = GrblPostProcessor()

    bounds = BoundingBox(
        min_x=path_min_x,
        max_x=path_max_x,
        min_y=path_min_y,
        max_y=path_max_y,
        min_z=depth_z,
        max_z=retract_z,
    )

    warnings: List[str] = []
    if work_envelope:
        warnings.extend(work_envelope.validate_bounds(bounds))

    resolved_dial = router_dial
    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if resolved_dial is None:
            resolved_dial = 1
            for d, rpm in dial_map.items():
                if spindle_speed >= rpm:
                    resolved_dial = d

    lines: List[str] = []
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=f"Operation: 2D Chamfering ({chamfer_width:.2f}mm width, {vbit_angle_deg}° V-Bit, Depth={depth_z:.3f}mm)",
        )
    )
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"{vbit_angle_deg}deg Chamfer Mill",
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

    lines.append(f"G0 X{pts[0][0]:.3f} Y{pts[0][1]:.3f}")
    lines.append(f"G0 Z{(start_z + 1.0):.3f}")
    lines.append(f"G1 Z{depth_z:.3f} F{plunge_feed:.1f}")

    for pt in pts[1:]:
        lines.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f} F{feed_rate_xy:.1f}")

    lines.append(f"G0 Z{retract_z:.3f}")
    lines.extend(postprocessor.format_footer(park_x=park_x, park_y=park_y, park_z=park_z or retract_z))
    gcode_text = "\n".join(lines)

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=8.0,
        warnings=warnings,
    )


def generate_circular_chamfer(
    center_x: float = 0.0,
    center_y: float = 0.0,
    diameter: float = 20.0,
    chamfer_width: float = 0.5,
    feature_type: str = "outside",  # "outside" (boss/button) or "inside" (bore/hole)
    cut_direction: str = "cw",  # "cw", "ccw", "climb", "conventional"
    vbit_angle_deg: float = 90.0,
    tip_diameter: float = 0.2,
    tip_offset: float = 0.5,
    tool_diameter: Optional[float] = None,
    stepdown_z: Optional[float] = None,
    lead_in_radius: float = 0.0,
    start_z: float = 0.0,
    retract_z: float = 5.0,
    feed_rate_xy: float = 800.0,
    plunge_feed: float = 250.0,
    spindle_speed: int = 16000,
    spindle_dwell_seconds: float = 2.0,
    units: str = "mm",
    tool_number: int = 1,
    tool_name: str = "",
    spindle_type: str = "router",
    router_model: Optional[str] = "dewalt_611",
    router_dial: Optional[int] = None,
    require_pause: bool = False,
    dialect: str = "grbl",
    postprocessor: Optional[BasePostProcessor] = None,
    work_envelope: Optional[WorkEnvelope] = None,
    park_x: Optional[float] = 0.0,
    park_y: Optional[float] = 0.0,
    park_z: Optional[float] = None,
) -> GCodeProgram:
    """
    Generates G-code for circular perimeter chamfering (outer boss such as a 20 mm brass button,
    or inner bore/hole) using two 180-degree semicircle G2/G3 arcs for universal controller compatibility.
    """
    units = normalize_units(units)
    if diameter <= 0:
        raise ValueError("Circle diameter must be greater than zero.")
    if chamfer_width <= 0:
        raise ValueError("Chamfer width must be greater than zero.")
    if retract_z <= start_z:
        raise ValueError("retract_z must be strictly above start_z.")
    if lead_in_radius < 0:
        raise ValueError("lead_in_radius cannot be negative.")

    feat = (feature_type or "outside").lower().strip()
    if feat not in ("outside", "inside"):
        raise ValueError("feature_type must be 'outside' or 'inside'.")

    depth_rel_z, radial_offset = calculate_chamfer_depth_and_offset(
        chamfer_width=chamfer_width,
        vbit_angle_deg=vbit_angle_deg,
        tip_diameter=tip_diameter,
        tip_offset=tip_offset,
    )
    final_depth_z = start_z + depth_rel_z

    if tool_diameter is not None:
        if tool_diameter <= 0 or tip_diameter >= tool_diameter:
            raise ValueError("Invalid tool_diameter or tip_diameter >= tool_diameter.")
        required_radius = radial_offset + chamfer_width
        if required_radius > (tool_diameter / 2.0) + 1e-5:
            raise ValueError(
                f"Chamfer width ({chamfer_width}mm) + radial offset ({radial_offset}mm) "
                f"exceeds physical cutter radius ({tool_diameter / 2.0}mm)."
            )

    nom_r = diameter / 2.0
    if feat == "outside":
        path_r = nom_r + radial_offset
    else:
        if (chamfer_width + radial_offset) >= nom_r or radial_offset >= nom_r:
            raise ValueError(
                f"Inside bore radius ({nom_r:.3f}{units}) is too small for radial offset ({radial_offset:.3f}{units}) "
                f"and chamfer width ({chamfer_width:.3f}{units})."
            )
        path_r = nom_r - radial_offset
        if lead_in_radius > 0 and lead_in_radius >= path_r:
            raise ValueError(
                f"lead_in_radius ({lead_in_radius:.3f}{units}) must be smaller than inside path radius ({path_r:.3f}{units})."
            )

    dir_norm = (cut_direction or "cw").lower().strip()
    if dir_norm == "cw":
        clockwise = True
    elif dir_norm == "ccw":
        clockwise = False
    elif dir_norm == "climb":
        clockwise = True if feat == "outside" else False
    elif dir_norm == "conventional":
        clockwise = False if feat == "outside" else True
    else:
        raise ValueError("cut_direction must be 'cw', 'ccw', 'climb', or 'conventional'.")

    # Multi-pass Z levels if stepdown_z is supplied
    total_z_drop = abs(depth_rel_z)
    if stepdown_z is not None and stepdown_z > 0 and stepdown_z < total_z_drop:
        n_passes = max(1, math.ceil(total_z_drop / stepdown_z))
        z_levels = [start_z - (i + 1) * (total_z_drop / n_passes) for i in range(n_passes)]
        z_levels[-1] = final_depth_z
    else:
        z_levels = [final_depth_z]

    if postprocessor is None:
        postprocessor = get_postprocessor(dialect)

    max_extent = path_r + (lead_in_radius if feat == "outside" else 0.0)
    bounds = BoundingBox(
        min_x=center_x - max_extent,
        max_x=center_x + max_extent,
        min_y=center_y - max_extent,
        max_y=center_y + max_extent,
        min_z=final_depth_z,
        max_z=retract_z,
    )

    warnings: List[str] = []
    if work_envelope:
        warnings.extend(work_envelope.validate_bounds(bounds))

    resolved_dial = router_dial
    if spindle_type == "router" and router_model in ROUTER_DIAL_MAPS:
        dial_map = ROUTER_DIAL_MAPS[router_model]
        if resolved_dial is None:
            resolved_dial = 1
            for d, rpm in dial_map.items():
                if spindle_speed >= rpm:
                    resolved_dial = d

    lines: List[str] = []
    lines.extend(
        postprocessor.format_header(
            units=units,
            absolute_mode=True,
            feed_mode="G94",
            plane="G17",
            comment=(
                f"Operation: Circular Chamfer ({feat.upper()}, Dia={diameter:.2f}{units}, "
                f"Width={chamfer_width:.2f}{units}, {vbit_angle_deg}° V-Bit, PathR={path_r:.3f}{units})"
            ),
        )
    )
    lines.extend(
        postprocessor.format_tool_comment(
            tool_number=tool_number,
            tool_name=tool_name or f"{vbit_angle_deg}deg Chamfer Mill",
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
            require_pause=require_pause,
        )
    )
    lines.append("")
    lines.append(postprocessor.format_rapid(z=retract_z, comment="Safe Z clearance"))

    approach_clearance = min(retract_z - start_z, 1.0 if units == "mm" else 0.04)

    # East-most point (0 deg) and West-most point (180 deg) on circular path
    east_x, east_y = center_x + path_r, center_y
    west_x, west_y = center_x - path_r, center_y

    # Tangent vector at (east_x, east_y) is (0, -1) for CW or (0, +1) for CCW
    ty = -1.0 if clockwise else 1.0
    # Scrap normal at (east_x, east_y) is (+1, 0) for outside or (-1, 0) for inside
    nx = 1.0 if feat == "outside" else -1.0

    # Cross product u x n = (0, ty) x (nx, 0) = -ty * nx
    # If u x n > 0, scrap normal is to the LEFT of travel (G3); if < 0, to the RIGHT of travel (G2)
    lead_cw = (-ty * nx) < 0

    for z_lvl in z_levels:
        if lead_in_radius > 0:
            c_in_x = east_x + nx * lead_in_radius
            c_in_y = east_y
            app_x = c_in_x
            app_y = c_in_y - ty * lead_in_radius
            lines.append(postprocessor.format_rapid(x=app_x, y=app_y))
            lines.append(postprocessor.format_rapid(z=start_z + approach_clearance))
            lines.append(postprocessor.format_linear(z=z_lvl, feed_rate=plunge_feed))
            lines.append(
                postprocessor.format_arc(
                    clockwise=lead_cw,
                    x=east_x,
                    y=east_y,
                    i=c_in_x - app_x,
                    j=c_in_y - app_y,
                    feed_rate=feed_rate_xy,
                    comment="Lead-In Arc",
                )
            )
        else:
            lines.append(postprocessor.format_rapid(x=east_x, y=east_y))
            lines.append(postprocessor.format_rapid(z=start_z + approach_clearance))
            lines.append(postprocessor.format_linear(z=z_lvl, feed_rate=plunge_feed))

        # Two 180-degree semicircle arcs
        lines.append(
            postprocessor.format_arc(
                clockwise=clockwise,
                x=west_x,
                y=west_y,
                i=-path_r,
                j=0.0,
                feed_rate=feed_rate_xy,
                comment="Chamfer Arc 1/2",
            )
        )
        lines.append(
            postprocessor.format_arc(
                clockwise=clockwise,
                x=east_x,
                y=east_y,
                i=path_r,
                j=0.0,
                feed_rate=feed_rate_xy,
                comment="Chamfer Arc 2/2",
            )
        )

        if lead_in_radius > 0:
            c_out_x = east_x + nx * lead_in_radius
            c_out_y = east_y
            dep_x = c_out_x
            dep_y = c_out_y + ty * lead_in_radius
            lines.append(
                postprocessor.format_arc(
                    clockwise=lead_cw,
                    x=dep_x,
                    y=dep_y,
                    i=c_out_x - east_x,
                    j=c_out_y - east_y,
                    feed_rate=feed_rate_xy,
                    comment="Lead-Out Arc",
                )
            )

        lines.append(postprocessor.format_rapid(z=retract_z))

    lines.extend(postprocessor.format_footer(park_x=park_x, park_y=park_y, park_z=park_z or retract_z))
    gcode_text = "\n".join(lines)

    circumference = 2.0 * math.pi * path_r * len(z_levels)
    est_sec = max(2.0, (circumference / max(1.0, feed_rate_xy)) * 60.0 + spindle_dwell_seconds)

    return GCodeProgram(
        gcode=gcode_text,
        lines=lines,
        line_count=len(lines),
        bounds=bounds,
        estimated_time_seconds=est_sec,
        warnings=warnings,
    )
