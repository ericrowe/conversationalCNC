import pytest
from app.generators.circular_pocket import generate_circular_pocket
from app.postprocessors.grbl import GrblPostProcessor

def test_circular_pocket_generation():
    prog = generate_circular_pocket(
        pockets=[(50.0, 50.0)],
        pocket_diameter=25.0,
        target_depth_z=-6.0,
        tool_diameter=6.35,
        stepdown_z=2.0,
        stepover_percent=50.0,
        finish_allowance=0.2,
        feed_rate_xy=1000.0,
        plunge_feed=250.0,
        spindle_speed=16000,
    )
    assert prog.gcode is not None
    assert "Z Layer 1/3" in prog.gcode
    assert "Z Layer 2/3" in prog.gcode
    assert "Z Layer 3/3" in prog.gcode
    assert "Finish Wall Pass" in prog.gcode
    assert "G3" in prog.gcode
    assert prog.bounds.min_z == -6.0
    assert prog.bounds.max_z == 5.0

def test_circular_pocket_tool_too_large():
    with pytest.raises(ValueError, match="cannot be larger than pocket diameter"):
        generate_circular_pocket(
            pockets=[(0.0, 0.0)],
            pocket_diameter=10.0,
            target_depth_z=-5.0,
            tool_diameter=12.0,
        )
