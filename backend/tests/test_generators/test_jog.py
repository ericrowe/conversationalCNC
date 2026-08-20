import pytest
from app.generators.jog import (
    generate_jog_command,
    generate_zero_wcs_command,
    generate_goto_origin_command,
    generate_spindle_manual_command,
)


def test_generate_jog_command_grbl():
    res = generate_jog_command(axis="X", distance=10.0, feed_rate=1500.0, units="mm", dialect="grbl")
    assert res["command_type"] == "jog_step"
    assert res["gcode"] == "$J=G91 G21 X+10.000 F1500.0"


def test_generate_jog_command_diagonal_grbl():
    res = generate_jog_command(axis="XY", distance=5.0, feed_rate=800.0, units="mm", dialect="grbl")
    assert res["gcode"] == "$J=G91 G21 X+5.000 Y+5.000 F800.0"

    res_neg = generate_jog_command(axis="-XY", distance=5.0, feed_rate=800.0, units="mm", dialect="grbl")
    assert res_neg["gcode"] == "$J=G91 G21 X-5.000 Y+5.000 F800.0"


def test_generate_jog_command_standard():
    res = generate_jog_command(axis="Z", distance=-1.0, feed_rate=300.0, units="mm", dialect="standard")
    assert "G91 G21 G1 Z-1.000 F300.0" in res["gcode"]
    assert "G90" in res["gcode"]


def test_generate_jog_invalid_parameters():
    with pytest.raises(ValueError):
        generate_jog_command(axis="X", distance=0.0)
    with pytest.raises(ValueError):
        generate_jog_command(axis="X", distance=10.0, feed_rate=0.0)


def test_generate_zero_wcs_command():
    res_all = generate_zero_wcs_command(axes=["X", "Y", "Z"], wcs_slot=1)
    assert res_all["gcode"] == "G10 L20 P1 X0.000 Y0.000 Z0.000"

    res_z = generate_zero_wcs_command(axes=["Z"], wcs_slot=1)
    assert res_z["gcode"] == "G10 L20 P1 Z0.000"


def test_generate_goto_origin_command():
    res = generate_goto_origin_command(safe_z_retract=15.0, units="mm")
    gcode = res["gcode"]
    assert "G0 Z15.000" in gcode
    assert "G0 X0.000 Y0.000" in gcode
    assert "G54" in gcode


def test_generate_spindle_manual_command():
    res_on = generate_spindle_manual_command(rpm=18000, state=True, clockwise=True)
    assert "M3 S18000" in res_on["gcode"]

    res_off = generate_spindle_manual_command(state=False)
    assert "M5" in res_off["gcode"]
