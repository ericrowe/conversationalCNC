import pytest
from app.generators.thread_milling import generate_helical_thread_milling, THREAD_STANDARDS
from app.generators.base import WorkEnvelope
from app.postprocessors.grbl import GrblPostProcessor
from app.postprocessors.registry import StandardPostProcessor

def test_thread_standards_catalog():
    assert "M6x1.0" in THREAD_STANDARDS
    assert THREAD_STANDARDS["M6x1.0"]["pitch"] == 1.0
    assert THREAD_STANDARDS["M6x1.0"]["nominal_dia"] == 6.0
    assert "1/4-20 UNC" in THREAD_STANDARDS
    assert abs(THREAD_STANDARDS["1/4-20 UNC"]["pitch"] - 1.27) < 0.01

def test_thread_milling_internal_climb_bottom_to_top():
    prog = generate_helical_thread_milling(
        holes=[(50.0, 50.0)],
        nominal_diameter=6.0,
        pitch=1.0,
        thread_length=10.0,
        tool_diameter=4.5,
        thread_type="internal",
        thread_hand="right_hand",
        milling_direction="bottom_to_top",
        radial_passes=2,
        spring_passes=1,
        start_z=0.0,
        retract_z=5.0,
        feed_rate_xy=300.0,
        plunge_feed=200.0,
        spindle_speed=16000,
    )
    assert prog.gcode is not None
    assert "G21 G90" in prog.gcode
    assert "M3 S16000" in prog.gcode
    assert "G3" in prog.gcode  # CCW arc for climb milling
    assert "Radial Pass 1/2" in prog.gcode
    assert "Radial Pass 2/2" in prog.gcode
    assert "Spring Pass 1" in prog.gcode
    assert "M5" in prog.gcode
    assert prog.bounds.min_z == -10.0
    assert prog.bounds.max_z == 5.0

def test_thread_milling_external_stud():
    prog = generate_helical_thread_milling(
        holes=[(20.0, 20.0)],
        nominal_diameter=8.0,
        pitch=1.25,
        thread_length=12.0,
        tool_diameter=4.5,
        thread_type="external",
        thread_hand="right_hand",
        milling_direction="top_to_bottom",
        radial_passes=1,
    )
    assert prog.gcode is not None
    assert "G3" in prog.gcode
    assert prog.bounds.min_z == -12.0

def test_thread_milling_validation_errors():
    with pytest.raises(ValueError, match="At least one thread hole coordinate"):
        generate_helical_thread_milling(
            holes=[],
            nominal_diameter=6.0,
            pitch=1.0,
            thread_length=10.0,
            tool_diameter=4.5,
        )

    with pytest.raises(ValueError, match="must be strictly less than"):
        generate_helical_thread_milling(
            holes=[(10.0, 10.0)],
            nominal_diameter=6.0,
            pitch=1.0,
            thread_length=10.0,
            tool_diameter=6.5,  # Tool larger than thread
            thread_type="internal",
        )

def test_thread_milling_work_envelope_warning():
    envelope = WorkEnvelope(work_area_x=100.0, work_area_y=100.0, work_area_z=50.0)
    prog = generate_helical_thread_milling(
        holes=[(150.0, 50.0)],
        nominal_diameter=6.0,
        pitch=1.0,
        thread_length=10.0,
        tool_diameter=4.5,
        work_envelope=envelope,
    )
    assert len(prog.warnings) > 0
    assert "exceeds work envelope max" in prog.warnings[0]
