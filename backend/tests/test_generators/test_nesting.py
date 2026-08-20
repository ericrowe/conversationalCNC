import pytest
from app.generators.nesting import (
    generate_step_and_repeat_grid,
    generate_soft_jaw_fixture,
)


def test_step_and_repeat_grid_2x2():
    sample_snippet = """G0 X0 Y0
G1 Z-2.0 F200.0
G1 X10.0 Y0 F500.0
G1 X10.0 Y10.0
G1 X0 Y10.0
G1 X0 Y0
G0 Z5.0"""

    res = generate_step_and_repeat_grid(
        gcode_snippet=sample_snippet,
        cols_x=2,
        rows_y=2,
        spacing_x=30.0,
        spacing_y=25.0,
        layout_pattern="grid",
        order_strategy="zigzag",
        safe_z_retract=5.0,
        dialect="grbl",
    )

    assert res["total_instances"] == 4
    assert res["cols_x"] == 2
    assert res["rows_y"] == 2
    gcode = res["gcode"]

    # Check headers and offsets
    assert "G21 G90 G94 G17 G54" in gcode
    assert "PART 1/4" in gcode
    assert "PART 4/4" in gcode
    assert "X30.000" in gcode
    assert "Y25.000" in gcode
    assert "M2" in gcode


def test_step_and_repeat_staggered():
    sample = "G1 X0 Y0\nG1 X5 Y5"
    res = generate_step_and_repeat_grid(
        gcode_snippet=sample,
        cols_x=2,
        rows_y=2,
        spacing_x=40.0,
        spacing_y=30.0,
        layout_pattern="staggered",
        order_strategy="oneway",
        safe_z_retract=5.0,
    )

    assert res["total_instances"] == 4
    gcode = res["gcode"]
    # Row 1 (r=1) should have staggered offset by spacing_x/2 = 20.0
    assert "X20.000" in gcode or "X60.000" in gcode


def test_soft_jaw_fixture_rectangular_with_dogbones():
    res = generate_soft_jaw_fixture(
        jaw_type="rectangular",
        part_length_x=50.0,
        part_width_y=30.0,
        step_depth_z=3.0,
        jaw_gap=10.0,
        dogbone_relief=True,
        tool_diameter=6.35,
        tool_number=1,
        tool_name="1/4 Endmill",
        stepdown_z=1.5,
        feed_rate_xy=1000.0,
        plunge_feed=250.0,
        spindle_speed=18000,
        safe_z_retract=5.0,
        dialect="grbl",
    )

    assert res["jaw_type"] == "rectangular"
    assert res["step_depth_z"] == 3.0
    gcode = res["gcode"]

    assert "G21 G90 G94 G17 G54" in gcode
    assert "Vise Soft Jaw Fixture Wizard" in gcode
    assert "CORNER DOGBONE RELIEFS" in gcode
    assert "Z-3.000" in gcode
    assert "M5" in gcode
    assert "M2" in gcode


def test_soft_jaw_fixture_round_bore():
    res = generate_soft_jaw_fixture(
        jaw_type="round_bore",
        part_diameter=40.0,
        step_depth_z=4.0,
        tool_diameter=6.35,
        tool_number=2,
        tool_name="1/4 Endmill",
        stepdown_z=2.0,
        feed_rate_xy=800.0,
        plunge_feed=200.0,
        spindle_speed=16000,
        safe_z_retract=5.0,
        dialect="grbl",
    )

    assert res["jaw_type"] == "round_bore"
    assert res["step_depth_z"] == 4.0
    gcode = res["gcode"]

    assert "G21 G90 G94 G17 G54" in gcode
    assert "Z-4.000" in gcode
    assert "G2" in gcode or "G3" in gcode
