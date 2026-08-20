import pytest
from app.generators.contouring import generate_contour_profile, _offset_line_segment


def test_offset_line_segment():
    # Horizontal line from (0,0) to (10,0), offset left by 2.0 (left of +X is +Y)
    x0, y0, x1, y1 = _offset_line_segment(0.0, 0.0, 10.0, 0.0, 2.0)
    assert pytest.approx(x0) == 0.0
    assert pytest.approx(y0) == 2.0
    assert pytest.approx(x1) == 10.0
    assert pytest.approx(y1) == 2.0


def test_contouring_basic_closed_profile():
    segments = [
        {"type": "line", "x": 40.0, "y": 0.0},
        {"type": "line", "x": 40.0, "y": 30.0},
        {"type": "line", "x": 0.0, "y": 30.0},
        {"type": "line", "x": 0.0, "y": 0.0},
    ]

    result = generate_contour_profile(
        segments=segments,
        start_point=(0.0, 0.0),
        side="left",
        target_depth_z=-4.0,
        stepdown_z=2.0,
        tool_diameter=4.0,
        lead_in_type="tangential_arc",
        lead_in_radius=5.0,
        spring_pass=True,
    )

    gcode = result["gcode"]
    assert "2.5D Profile Contour: Side=LEFT" in gcode
    assert "G21 G90 G94 G17 G54" in gcode
    assert "M3 S16000" in gcode
    assert "Tangential Arc Lead-In" in gcode
    assert "Tangential Arc Lead-Out" in gcode
    assert "M5" in gcode
    assert "M2" in gcode
    assert result["passes"] == 2


def test_contouring_cutter_comp_left_right():
    segments = [
        {"type": "line", "x": 50.0, "y": 0.0},
    ]
    # Tool diameter 6mm (radius 3mm)
    res_left = generate_contour_profile(
        segments=segments,
        start_point=(0.0, 0.0),
        side="left",
        tool_diameter=6.0,
        finish_allowance=0.0,
        spring_pass=False,
    )
    # Left offset should move Y in positive direction
    assert "Y3.000" in res_left["gcode"]

    res_right = generate_contour_profile(
        segments=segments,
        start_point=(0.0, 0.0),
        side="right",
        tool_diameter=6.0,
        finish_allowance=0.0,
        spring_pass=False,
    )
    # Right offset should move Y in negative direction
    assert "Y-3.000" in res_right["gcode"]


def test_contouring_arc_segments():
    segments = [
        {"type": "line", "x": 30.0, "y": 0.0},
        {"type": "arc", "x": 30.0, "y": 20.0, "i": 0.0, "j": 10.0, "cw": False},
        {"type": "line", "x": 0.0, "y": 20.0},
    ]

    result = generate_contour_profile(
        segments=segments,
        start_point=(0.0, 0.0),
        side="left",
        tool_diameter=3.175,
    )

    gcode = result["gcode"]
    assert "G3 X30.000 Y20.000" in gcode
    assert result["segment_count"] == 3


def test_contouring_finish_allowance_and_spring_pass():
    segments = [
        {"type": "line", "x": 20.0, "y": 0.0},
        {"type": "line", "x": 0.0, "y": 0.0},
    ]

    result = generate_contour_profile(
        segments=segments,
        start_point=(0.0, 0.0),
        side="left",
        target_depth_z=-2.0,
        stepdown_z=2.0,
        finish_allowance=0.3,
        spring_pass=True,
    )

    gcode = result["gcode"]
    assert "--- ROUGH PASS" in gcode
    assert "--- FINISH PASS" in gcode
    assert "--- SPRING PASS" in gcode
