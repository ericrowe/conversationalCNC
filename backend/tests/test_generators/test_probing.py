import pytest
from app.generators.probing import (
    generate_z_probe_macro,
    generate_corner_xyz_probe_macro,
    generate_in_program_probe_block,
    generate_homing_macro,
)


def test_generate_z_probe_macro():
    macro = generate_z_probe_macro(
        plate_thickness=14.85,
        search_dist=30.0,
        fast_feed=150.0,
        slow_feed=25.0,
        retract_height=20.0,
    )
    gcode = macro["gcode"]
    assert "G38.2 Z-30.000 F150.0" in gcode
    assert "G38.2 Z-3.000 F25.0" in gcode
    assert "G10 L20 P1 Z14.850" in gcode
    assert "G0 Z20.000" in gcode
    assert "G54" in gcode


def test_generate_corner_xyz_probe_macro():
    macro = generate_corner_xyz_probe_macro(
        tool_diameter=6.35,
        plate_thickness=14.85,
        block_x_lip=10.0,
        block_y_lip=10.0,
    )
    gcode = macro["gcode"]
    assert "G10 L20 P1 Z14.850" in gcode
    # Tool radius = 3.175, Lip = 10 -> X offset = -(3.175 + 10) = -13.175
    assert "G10 L20 P1 X-13.175" in gcode
    assert "G10 L20 P1 Y-13.175" in gcode
    assert "G0 X0.000 Y0.000" in gcode


def test_generate_in_program_probe_block():
    lines = generate_in_program_probe_block(plate_thickness=14.85, retract_z=20.0)
    joined = "\n".join(lines)
    assert "M0" in joined
    assert "ATTACH Z-PROBE" in joined
    assert "REMOVE PROBE CLIP" in joined
    assert "G38.2" in joined
    assert "G10 L20 P1 Z14.850" in joined


def test_generate_homing_macro():
    macro = generate_homing_macro()
    gcode = macro["gcode"]
    assert "$H" in gcode
    assert "G54" in gcode
