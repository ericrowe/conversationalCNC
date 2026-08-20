import pytest
from app.generators.surfacing import generate_surfacing

def test_surfacing_zigzag():
    prog = generate_surfacing(
        length_x=100.0,
        width_y=80.0,
        origin_x=0.0,
        origin_y=0.0,
        origin_mode="corner",
        total_depth_z=1.0,
        stepdown_z=0.5,
        tool_diameter=25.4,
        stepover_percent=70.0,
        cut_direction="zigzag",
        feed_rate_xy=2000.0,
        plunge_feed=300.0,
    )
    assert prog.gcode is not None
    assert "Z Layer 1/2" in prog.gcode
    assert "Z Layer 2/2" in prog.gcode
    assert "Pass 1" in prog.gcode
    assert prog.bounds.min_z == -1.0

def test_surfacing_climb_oneway():
    prog = generate_surfacing(
        length_x=100.0,
        width_y=50.0,
        origin_x=50.0,
        origin_y=50.0,
        origin_mode="center",
        total_depth_z=0.5,
        stepdown_z=0.5,
        tool_diameter=25.4,
        cut_direction="climb_oneway",
    )
    assert prog.gcode is not None
    assert "Z Layer 1/1" in prog.gcode
    assert "Safe Z clearance" in prog.gcode
