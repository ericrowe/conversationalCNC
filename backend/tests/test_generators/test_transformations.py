import pytest
from app.generators.transformations import (
    transform_shift_gcode,
    transform_rotate_gcode,
    transform_mirror_gcode,
    transform_override_feeds_speeds,
    split_multitool_gcode,
)


def test_shift_gcode():
    input_gcode = "G0 X10.000 Y20.000 Z5.000 (Safe move)\nG1 X30.000 Y40.000 Z-2.000 F800"
    shifted = transform_shift_gcode(input_gcode, delta_x=10.0, delta_y=-5.0, delta_z=2.0)
    assert "X20.000" in shifted
    assert "Y15.000" in shifted
    assert "Z7.000" in shifted
    assert "X40.000" in shifted
    assert "Y35.000" in shifted
    assert "Z0.000" in shifted
    assert "(Safe move)" in shifted


def test_rotate_gcode():
    # Rotate 90 degrees CCW: (10, 0) -> (0, 10)
    input_gcode = "G1 X10.000 Y0.000 F500"
    rotated = transform_rotate_gcode(input_gcode, angle_deg=90.0, center_x=0.0, center_y=0.0)
    assert "X0.000" in rotated
    assert "Y10.000" in rotated


def test_mirror_gcode():
    # Mirror across X axis (Y -> -Y, G2 -> G3)
    input_gcode = "G2 X10.000 Y20.000 I5.000 J0.000"
    mirrored = transform_mirror_gcode(input_gcode, mirror_axis="x")
    assert "Y-20.000" in mirrored
    assert "G3" in mirrored
    assert "J-0.000" in mirrored or "J0.000" in mirrored


def test_override_feeds_speeds():
    input_gcode = "G1 X10.000 Y20.000 F1000.0\nS10000 M3"
    overridden = transform_override_feeds_speeds(input_gcode, feed_multiplier=0.8, speed_multiplier=1.2)
    assert "F800.0" in overridden
    assert "S12000" in overridden


def test_split_multitool_gcode():
    input_gcode = """(Header)
G21 G90
T1 M6 (1/4 Endmill)
G0 X0 Y0
G1 Z-5 F500
T2 M6 (1/8 Ballmill)
G0 X10 Y10
G1 Z-2 F300
"""
    sections = split_multitool_gcode(input_gcode)
    assert len(sections) == 2
    assert sections[0]["tool_number"] == 1
    assert sections[0]["filename"] == "program_T1.nc"
    assert "M30" in sections[0]["gcode"]
    assert sections[1]["tool_number"] == 2
    assert sections[1]["filename"] == "program_T2.nc"
