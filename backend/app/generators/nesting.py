"""
Step-and-Repeat Array Nesting & Soft Jaw Fixturing Generator Engine.
Supports:
- 2D Matrix Grid & Staggered / Honeycomb multi-part nesting
- Optimized serpentine / zig-zag rapid traversal order
- Vise Soft Jaw Clamping Pocket Wizard (Rectangular & Cylindrical) with dogbone corner relief
"""
import re
import math
from typing import Dict, Any, List, Optional, Tuple
from ..postprocessors import get_postprocessor
from .transformations import transform_shift_gcode
from .base import strip_header_and_footer as _strip_header_and_footer
from .rectangular_pocket import generate_rectangular_pocket
from .circular_pocket import generate_circular_pocket



def generate_step_and_repeat_grid(
    gcode_snippet: str,
    cols_x: int = 2,
    rows_y: int = 2,
    spacing_x: float = 60.0,
    spacing_y: float = 50.0,
    layout_pattern: str = "grid",  # 'grid' or 'staggered'
    order_strategy: str = "zigzag",  # 'zigzag' or 'oneway'
    safe_z_retract: float = 5.0,
    units: str = "mm",
    dialect: str = "grbl",
    **kwargs,
) -> Dict[str, Any]:
    """
    Arrays a single-part G-code snippet across an Nx * Ny grid or staggered honeycomb layout.
    """
    post = get_postprocessor(dialect)
    cleaned_lines = _strip_header_and_footer(gcode_snippet)
    snippet_body = "\n".join(cleaned_lines)

    cols = max(1, int(cols_x))
    rows = max(1, int(rows_y))
    total_instances = cols * rows

    lines = []
    # 1. Header
    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=f"Step-and-Repeat Array: {cols}x{rows} ({total_instances} parts) | Pattern={layout_pattern.upper()}",
    )
    lines.extend(header)
    lines.append("")
    lines.append(f"G0 Z{safe_z_retract:.3f} (Move to safe array clearance)")
    lines.append("")

    instance_index = 0

    for r in range(rows):
        # Determine column order for this row
        if order_strategy == "zigzag" and r % 2 == 1:
            col_range = list(range(cols - 1, -1, -1))
        else:
            col_range = list(range(cols))

        for c in col_range:
            instance_index += 1
            # Calculate instance offset
            if layout_pattern == "staggered" and r % 2 == 1:
                dx = c * spacing_x + (spacing_x / 2.0)
            else:
                dx = c * spacing_x

            dy = r * spacing_y

            lines.append(f"( ====================================================== )")
            lines.append(f"( >>> PART {instance_index}/{total_instances} [Col {c+1}, Row {r+1}] Offset: X{dx:+.3f} Y{dy:+.3f} <<< )")
            lines.append(f"( ====================================================== )")
            lines.append(f"G0 Z{safe_z_retract:.3f} (Ensure safe clearance before shift)")

            # Shift the base snippet coordinates by (dx, dy)
            shifted_gcode = transform_shift_gcode(snippet_body, delta_x=dx, delta_y=dy, delta_z=0.0)
            lines.append(shifted_gcode)
            lines.append(f"G0 Z{safe_z_retract:.3f} (Retract after instance)")
            lines.append("")


    # 4. Footer
    footer = post.format_footer(park_z=safe_z_retract, park_x=0.0, park_y=0.0)
    lines.extend(footer)

    full_gcode = "\n".join(lines)

    return {
        "gcode": full_gcode,
        "total_instances": total_instances,
        "cols_x": cols,
        "rows_y": rows,
        "layout_pattern": layout_pattern,
        "spacing_x": spacing_x,
        "spacing_y": spacing_y,
    }


def generate_soft_jaw_fixture(
    jaw_type: str = "rectangular",  # 'rectangular' or 'round_bore'
    part_length_x: float = 60.0,
    part_width_y: float = 40.0,
    part_diameter: float = 50.0,
    step_depth_z: float = 3.0,  # Clamping ledge depth (positive magnitude)
    jaw_gap: float = 10.0,  # Gap between jaws when clamped on spacer
    dogbone_relief: bool = True,
    tool_diameter: float = 6.35,
    tool_number: int = 1,
    tool_name: str = "Endmill",
    stepdown_z: float = 1.5,
    stepover_percent: float = 50.0,
    feed_rate_xy: float = 1000.0,
    plunge_feed: float = 250.0,
    spindle_speed: int = 16000,
    safe_z_retract: float = 5.0,
    units: str = "mm",
    dialect: str = "grbl",
    **kwargs,
) -> Dict[str, Any]:
    """
    Generates G-code to machine custom vise soft jaw clamping pockets.
    Machines negative cavity into Fixed & Movable jaws centered around (X0, Y0).
    """
    post = get_postprocessor(dialect)
    depth_z = -abs(step_depth_z)

    lines = []
    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=f"Vise Soft Jaw Fixture Wizard: Type={jaw_type.upper()} | Depth={abs(step_depth_z):.3f}{units}",
    )
    lines.extend(header)
    lines.append("")

    lines.extend(post.format_tool_comment(tool_number, tool_name))
    lines.extend(post.format_spindle_start(rpm=spindle_speed, dwell_seconds=1.5))
    lines.append("")
    lines.append(f"( Origin (X0, Y0) is centered on the Vise Jaw Gap centerline )")
    lines.append(f"G0 Z{safe_z_retract:.3f}")
    lines.append("")

    r_tool = tool_diameter / 2.0

    if jaw_type == "round_bore":
        # Circular bore pocket centered at (0, 0)
        pocket_res = generate_circular_pocket(
            pockets=[(0.0, 0.0)],
            pocket_diameter=part_diameter,
            target_depth_z=depth_z,
            tool_diameter=tool_diameter,
            stepdown_z=stepdown_z,
            stepover_percent=stepover_percent,
            feed_rate_xy=feed_rate_xy,
            plunge_feed=plunge_feed,
            retract_z=safe_z_retract,
            spindle_speed=spindle_speed,
            units=units,
            postprocessor=post,
        )
        pocket_gcode = pocket_res.gcode if hasattr(pocket_res, "gcode") else pocket_res.get("gcode", "")
        cleaned = _strip_header_and_footer(pocket_gcode)
        lines.extend(cleaned)
    else:
        # Rectangular cavity pocket centered at (0, 0)
        pocket_res = generate_rectangular_pocket(
            origin_x=0.0,
            origin_y=0.0,
            length_x=part_length_x,
            width_y=part_width_y,
            target_depth_z=depth_z,
            origin_mode="center",
            corner_radius=0.0,
            tool_diameter=tool_diameter,
            stepdown_z=stepdown_z,
            stepover_percent=stepover_percent,
            feed_rate_xy=feed_rate_xy,
            plunge_feed=plunge_feed,
            retract_z=safe_z_retract,
            spindle_speed=spindle_speed,
            units=units,
            postprocessor=post,
        )
        pocket_gcode = pocket_res.gcode if hasattr(pocket_res, "gcode") else pocket_res.get("gcode", "")
        cleaned = _strip_header_and_footer(pocket_gcode)
        lines.extend(cleaned)


        # Dogbone corner relief drill moves to clear sharp corners
        if dogbone_relief:
            lines.append("")
            lines.append("( --- CORNER DOGBONE RELIEFS (45-deg corner overcuts) --- )")
            half_x = part_length_x / 2.0
            half_y = part_width_y / 2.0
            # Relief offset distance into each corner
            db_ext = r_tool * 0.7071

            corners = [
                (-half_x - db_ext, -half_y - db_ext),  # Bottom-Left
                (half_x + db_ext, -half_y - db_ext),   # Bottom-Right
                (half_x + db_ext, half_y + db_ext),    # Top-Right
                (-half_x - db_ext, half_y + db_ext),   # Top-Left
            ]

            for cx, cy in corners:
                lines.append(f"G0 Z{safe_z_retract:.3f}")
                lines.append(f"G0 X{cx:.3f} Y{cy:.3f}")
                lines.append(f"G1 Z{depth_z:.3f} F{plunge_feed:.1f}")
                lines.append(f"G0 Z{safe_z_retract:.3f}")

    lines.append("")
    footer = post.format_footer(park_z=safe_z_retract, park_x=0.0, park_y=0.0)
    lines.extend(footer)

    full_gcode = "\n".join(lines)

    return {
        "gcode": full_gcode,
        "jaw_type": jaw_type,
        "step_depth_z": abs(step_depth_z),
        "dogbone_relief": dogbone_relief,
        "tool_diameter": tool_diameter,
    }
