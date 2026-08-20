import pytest
from app.generators.drilling import generate_straight_plunge
from app.generators.base import WorkEnvelope
from app.postprocessors.grbl import GrblPostProcessor
from app.postprocessors.registry import StandardPostProcessor

def test_generate_straight_plunge_single_hole():
    program = generate_straight_plunge(
        holes=[(10.0, 20.0)],
        target_depth_z=-5.0,
        start_z=0.0,
        retract_z=5.0,
        plunge_feed=250.0,
        rapid_feed=5000.0,
        spindle_speed=18000,
        dwell_seconds=0.5,
        spindle_dwell_seconds=2.0,
    )

    gcode = program.gcode
    # Safety header checks
    assert "G21 G90 G94 G17" in gcode
    # Spindle and dwell
    assert "M3 S18000" in gcode
    assert "G4 P2.00" in gcode
    # Safe clearance approach
    assert "G0 Z5.000" in gcode
    # Hole location approach
    assert "G0 X10.000 Y20.000" in gcode
    # Controlled plunge
    assert "G1 Z-5.000 F250.0" in gcode
    # Dwell at bottom
    assert "G4 P0.50" in gcode
    # Retract
    assert "G0 Z5.000" in gcode
    # Program end
    assert "M5" in gcode
    assert "M2" in gcode
    # No canned cycles
    assert "G81" not in gcode
    assert "G83" not in gcode

    # Verify bounding box
    assert program.bounds.min_x == 0.0  # because park_x is 0.0
    assert program.bounds.max_x == 10.0
    assert program.bounds.min_y == 0.0  # park_y is 0.0
    assert program.bounds.max_y == 20.0
    assert program.bounds.min_z == -5.0
    assert program.bounds.max_z == 5.0
    assert program.estimated_time_seconds > 0

def test_positive_depth_conversion():
    # If user provides positive depth 5.0 with start_z=0.0, it should drill to -5.0
    program = generate_straight_plunge(
        holes=[(0.0, 0.0)],
        target_depth_z=5.0,
        start_z=0.0,
    )
    assert "G1 Z-5.000" in program.gcode

def test_generate_straight_plunge_multi_hole():
    holes = [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)]
    program = generate_straight_plunge(
        holes=holes,
        target_depth_z=-4.0,
        start_z=0.0,
        plunge_feed=300.0,
    )

    assert "Hole 1/4 at X10.000, Y10.000" in program.gcode
    assert "Hole 2/4 at X30.000, Y10.000" in program.gcode
    assert "Hole 3/4 at X30.000, Y30.000" in program.gcode
    assert "Hole 4/4 at X10.000, Y30.000" in program.gcode
    assert program.line_count > 20

def test_work_envelope_validation():
    envelope = WorkEnvelope(work_area_x=750.0, work_area_y=750.0, work_area_z=65.0)

    # Within bounds -> No warnings
    prog_ok = generate_straight_plunge(
        holes=[(100.0, 100.0)],
        target_depth_z=-5.0,
        work_envelope=envelope,
    )
    assert len(prog_ok.warnings) == 0

    # Outside bounds (X=800 exceeds 750) -> Warning present
    prog_oob = generate_straight_plunge(
        holes=[(800.0, 100.0)],
        target_depth_z=-5.0,
        work_envelope=envelope,
    )
    assert len(prog_oob.warnings) > 0
    assert any("exceeds work envelope max 750.00" in w for w in prog_oob.warnings)

def test_invalid_parameters():
    with pytest.raises(ValueError, match="At least one hole coordinate"):
        generate_straight_plunge(holes=[], target_depth_z=-5.0)

    with pytest.raises(ValueError, match="Plunge feed rate must be greater than zero"):
        generate_straight_plunge(holes=[(0, 0)], target_depth_z=-5.0, plunge_feed=-10)

    with pytest.raises(ValueError, match="Spindle speed must be greater than zero"):
        generate_straight_plunge(holes=[(0, 0)], target_depth_z=-5.0, spindle_speed=0)

def test_standard_dialect_canned_cycle():
    standard_post = StandardPostProcessor()
    program = generate_straight_plunge(
        holes=[(15.0, 25.0)],
        target_depth_z=-8.0,
        postprocessor=standard_post,
        dwell_seconds=1.0,
    )
    assert "G82" in program.gcode
    assert "G80" in program.gcode

def test_dewalt_router_dial_mapping_and_comment():
    program = generate_straight_plunge(
        holes=[(10.0, 20.0)],
        target_depth_z=-5.0,
        spindle_speed=20400,
        spindle_type="router",
        router_model="dewalt_611",
    )
    assert "DeWalt DWP611 - Set Speed Dial to #3 [~20400 RPM]" in program.gcode
    assert "M3 S20400" in program.gcode
    assert len(program.warnings) == 0

def test_router_min_rpm_clamping():
    program = generate_straight_plunge(
        holes=[(10.0, 20.0)],
        target_depth_z=-5.0,
        spindle_speed=10000,
        spindle_type="router",
        router_model="dewalt_611",
        min_spindle_rpm=16000,
    )
    assert "M3 S16000" in program.gcode
    assert "Set Speed Dial to #1" in program.gcode
    assert any("below Dewalt 611 minimum speed" in w for w in program.warnings)

def test_vfd_spindle_comment():
    program = generate_straight_plunge(
        holes=[(10.0, 20.0)],
        target_depth_z=-5.0,
        spindle_speed=12000,
        spindle_type="vfd_spindle",
    )
    assert "Spindle: VFD / PWM Control at 12000 RPM" in program.gcode
    assert "M3 S12000" in program.gcode
