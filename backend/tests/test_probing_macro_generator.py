import pytest
from app.generators.probing import (
    generate_z_probe_macro,
    generate_corner_xyz_probe_macro,
    generate_bore_center_probe_macro,
    generate_boss_center_probe_macro,
    generate_in_program_probe_block,
    generate_homing_macro,
)


def test_z_probe_offset_calculation():
    """
    Plan 05 Spec:
    Asserts probe macro with 10.0mm plate thickness sets G10 L20 P1 Z10.0 upon contact.
    """
    macro = generate_z_probe_macro(
        plate_thickness=10.0,
        search_dist=25.0,
        fast_feed=120.0,
        slow_feed=20.0,
        retract_height=15.0,
        wcs_slot=1,
    )
    gcode = macro["gcode"]
    assert "G38.2 Z-25.000 F120.0" in gcode
    assert "G38.2 Z-3.000 F20.0" in gcode
    assert "G10 L20 P1 Z10.000" in gcode
    assert "G0 Z15.000" in gcode


def test_xyz_corner_tool_radius_compensation():
    """
    Plan 05 Spec:
    Asserts front-left corner probing with 6.35mm (1/4") endmill and 10.0mm block lip
    sets X zero offset to -(10.0 + 3.175) = -13.175mm.
    """
    macro = generate_corner_xyz_probe_macro(
        tool_diameter=6.35,
        plate_thickness=14.85,
        block_x_lip=10.0,
        block_y_lip=10.0,
        corner="front_left",
    )
    gcode = macro["gcode"]
    assert "G10 L20 P1 Z14.850" in gcode
    assert "G10 L20 P1 X-13.175" in gcode
    assert "G10 L20 P1 Y-13.175" in gcode
    assert "G38.2 X25.000" in gcode  # Probing X+ into block
    assert "G38.2 Y25.000" in gcode  # Probing Y+ into block


def test_xyz_corner_all_four_orientations():
    """
    Verifies sign logic and tool offsets for all 4 workpiece corner orientations:
    1. Front-Left:  X=-(Lip+R), Y=-(Lip+R), probes X+, Y+
    2. Front-Right: X=+(Lip+R), Y=-(Lip+R), probes X-, Y+
    3. Back-Left:   X=-(Lip+R), Y=+(Lip+R), probes X+, Y-
    4. Back-Right:  X=+(Lip+R), Y=+(Lip+R), probes X-, Y-
    """
    tool_dia = 4.0  # radius = 2.0
    lip = 8.0  # offset magnitude = 10.0
    thick = 12.0

    # 1. Front-Left
    fl = generate_corner_xyz_probe_macro(
        tool_diameter=tool_dia, plate_thickness=thick, block_x_lip=lip, block_y_lip=lip, corner="front_left"
    )
    assert "G10 L20 P1 X-10.000" in fl["gcode"]
    assert "G10 L20 P1 Y-10.000" in fl["gcode"]
    assert "G38.2 X25.000" in fl["gcode"]
    assert "G38.2 Y25.000" in fl["gcode"]

    # 2. Front-Right
    fr = generate_corner_xyz_probe_macro(
        tool_diameter=tool_dia, plate_thickness=thick, block_x_lip=lip, block_y_lip=lip, corner="front_right"
    )
    assert "G10 L20 P1 X10.000" in fr["gcode"]
    assert "G10 L20 P1 Y-10.000" in fr["gcode"]
    assert "G38.2 X-25.000" in fr["gcode"]
    assert "G38.2 Y25.000" in fr["gcode"]

    # 3. Back-Left
    bl = generate_corner_xyz_probe_macro(
        tool_diameter=tool_dia, plate_thickness=thick, block_x_lip=lip, block_y_lip=lip, corner="back_left"
    )
    assert "G10 L20 P1 X-10.000" in bl["gcode"]
    assert "G10 L20 P1 Y10.000" in bl["gcode"]
    assert "G38.2 X25.000" in bl["gcode"]
    assert "G38.2 Y-25.000" in bl["gcode"]

    # 4. Back-Right
    br = generate_corner_xyz_probe_macro(
        tool_diameter=tool_dia, plate_thickness=thick, block_x_lip=lip, block_y_lip=lip, corner="back_right"
    )
    assert "G10 L20 P1 X10.000" in br["gcode"]
    assert "G10 L20 P1 Y10.000" in br["gcode"]
    assert "G38.2 X-25.000" in br["gcode"]
    assert "G38.2 Y-25.000" in br["gcode"]


def test_bore_center_probing_macro():
    """
    Tests circular inside hole center probe macro.
    """
    bore = generate_bore_center_probe_macro(
        approx_diameter=50.0,
        tool_diameter=6.35,
        search_dist=30.0,
        fast_feed=150.0,
        slow_feed=25.0,
        retract_z=10.0,
    )
    gcode = bore["gcode"]
    assert "IN-BORE 4-POINT CENTER PROBE" in gcode
    assert "G38.2 X-30.000" in gcode
    assert "G38.2 X30.000" in gcode
    assert "G38.2 Y-30.000" in gcode
    assert "G38.2 Y30.000" in gcode
    assert "G10 L20 P1 X0.000 Y0.000" in gcode


def test_boss_center_probing_macro():
    """
    Tests cylindrical outside boss center probe macro.
    """
    boss = generate_boss_center_probe_macro(
        approx_diameter=40.0,
        tool_diameter=6.35,
        search_dist=15.0,
        retract_z=15.0,
    )
    gcode = boss["gcode"]
    assert "OUTSIDE BOSS 4-POINT CENTER PROBE" in gcode
    assert "G10 L20 P1 X0.000 Y0.000" in gcode


def test_probing_validation_errors():
    with pytest.raises(ValueError, match="Touch plate thickness cannot be negative"):
        generate_z_probe_macro(plate_thickness=-5.0)

    with pytest.raises(ValueError, match="Tool diameter must be positive"):
        generate_corner_xyz_probe_macro(tool_diameter=-2.0)
