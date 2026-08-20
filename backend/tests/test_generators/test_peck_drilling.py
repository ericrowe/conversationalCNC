import pytest
from app.generators.drilling import generate_peck_drilling
from app.postprocessors.grbl import GrblPostProcessor
from app.postprocessors.registry import StandardPostProcessor

def test_peck_drilling_grbl_expansion():
    prog = generate_peck_drilling(
        holes=[(10.0, 20.0), (30.0, 40.0)],
        target_depth_z=-15.0,
        peck_depth=5.0,
        start_z=0.0,
        retract_z=5.0,
        plunge_feed=200.0,
        dwell_seconds=0.5,
        postprocessor=GrblPostProcessor(),
    )
    assert prog.gcode is not None
    assert "Peck 1/3" in prog.gcode
    assert "Peck 2/3" in prog.gcode
    assert "Peck 3/3" in prog.gcode
    assert "G4 P0.50" in prog.gcode
    assert "G0 Z5.000" in prog.gcode
    assert prog.bounds.min_z == -15.0

def test_peck_drilling_chip_break():
    prog = generate_peck_drilling(
        holes=[(10.0, 20.0)],
        target_depth_z=-10.0,
        peck_depth=5.0,
        peck_retract_type="chip_break",
        postprocessor=GrblPostProcessor(),
    )
    assert prog.gcode is not None
    assert "Chip Breaking (G73)" in prog.gcode

def test_peck_drilling_standard_canned_cycle():
    prog = generate_peck_drilling(
        holes=[(15.0, 25.0)],
        target_depth_z=-12.0,
        peck_depth=4.0,
        postprocessor=StandardPostProcessor(),
    )
    assert "G98 G83" in prog.gcode
    assert "Q4.000" in prog.gcode
    assert "G80" in prog.gcode
