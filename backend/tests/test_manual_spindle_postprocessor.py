import pytest
from app.models import MachineProfile, SpindleType, RouterModel
from app.postprocessors import GrblPostProcessor, get_postprocessor
from app.postprocessors.registry import StandardPostProcessor
from app.postprocessors.router_speed_tables import (
    interpolate_router_dial,
    format_manual_spindle_comment,
    ROUTER_SPECS,
)
from app.generators.surfacing import generate_surfacing
from app.generators.drilling import generate_straight_plunge


def test_manual_spindle_emits_dial_comment():
    """
    Test Plan 03 Section 4:
    Configures machine profile with spindle_type = MANUAL_ROUTER and router_model = MAKITA_RT0701C.
    Requests G-code generation for a 16,000 RPM facing operation.
    Asserts generated G-code contains '( *** MANUAL ROUTER: SET SPEED DIAL TO 2.8 (~16,000 RPM) *** )'
    and omits 'M3 S16000' / 'S16000 M3'.
    """
    grbl = GrblPostProcessor()
    lines = grbl.format_spindle_start(
        rpm=16000,
        clockwise=True,
        dwell_seconds=2.0,
        spindle_type="manual_router",
        router_model="makita_rt0701c",
    )
    gcode = "\n".join(lines)
    assert "( *** MANUAL ROUTER: SET SPEED DIAL TO 2.8 (~16,000 RPM) *** )" in gcode
    assert "M3" not in gcode
    assert "S16000" not in gcode


def test_vfd_spindle_emits_standard_m3():
    """
    Test Plan 03 Section 4:
    Asserts standard VFD machine profiles continue emitting S16000 M3 / M3 S16000 unchanged.
    """
    grbl = GrblPostProcessor()
    lines = grbl.format_spindle_start(
        rpm=16000,
        clockwise=True,
        dwell_seconds=2.0,
        spindle_type="vfd_auto",
    )
    gcode = "\n".join(lines)
    assert "M3 S16000" in gcode
    assert "G4 P2.00" in gcode
    assert "VFD / PWM Control" in gcode


def test_makita_rt0701c_dial_interpolation():
    # Dial 1 = 10k, Dial 2 = 12k, Dial 3 = 17k, Dial 4 = 22k, Dial 5 = 27k, Dial 6 = 30k
    info_10k = interpolate_router_dial("makita_rt0701c", 10000)
    assert info_10k.dial_setting == 1.0
    assert info_10k.dial_display == "1.0"

    info_16k = interpolate_router_dial("makita_rt0701c", 16000)
    assert info_16k.dial_setting == 2.8
    assert info_16k.dial_display == "2.8"

    info_30k = interpolate_router_dial("makita_rt0701c", 30000)
    assert info_30k.dial_setting == 6.0
    assert info_30k.dial_display == "6.0"


def test_dewalt_dwp611_dial_interpolation():
    # Dial 1 = 16k, Dial 2 = 18.2k, Dial 3 = 20.4k, Dial 4 = 22.6k, Dial 5 = 24.8k, Dial 6 = 27k
    info_16k = interpolate_router_dial("dewalt_611", 16000)
    assert info_16k.dial_setting == 1.0
    assert info_16k.dial_display == "1.0"

    info_27k = interpolate_router_dial("dewalt_611", 27000)
    assert info_27k.dial_setting == 6.0
    assert info_27k.dial_display == "6.0"

    info_20400 = interpolate_router_dial("dewalt_611", 20400)
    assert info_20400.dial_setting == 3.0


def test_bosch_colt_dial_interpolation():
    # Dial 1 = 16k, Dial 6 = 35k
    info_16k = interpolate_router_dial("bosch_colt", 16000)
    assert info_16k.dial_setting == 1.0
    assert info_16k.dial_display == "1.0"

    info_35k = interpolate_router_dial("bosch_colt", 35000)
    assert info_35k.dial_setting == 6.0


def test_generic_router_dial_interpolation():
    info_10k = interpolate_router_dial("generic", 10000)
    assert info_10k.dial_setting == 1.0

    info_30k = interpolate_router_dial("generic", 30000)
    assert info_30k.dial_setting == 6.0


def test_manual_router_pause_prompt_m0():
    grbl = GrblPostProcessor()
    lines = grbl.format_spindle_start(
        rpm=18000,
        clockwise=True,
        dwell_seconds=2.0,
        spindle_type="manual_router",
        router_model="dewalt_611",
        require_pause=True,
    )
    gcode = "\n".join(lines)
    assert any("M0" in line for line in lines)
    assert "( *** MANUAL ROUTER: SET SPEED DIAL TO" in gcode
    assert "M3" not in gcode


def test_standard_postprocessor_manual_and_vfd():
    standard = StandardPostProcessor()
    manual_lines = standard.format_spindle_start(
        rpm=16000,
        spindle_type="manual_router",
        router_model="makita_rt0701c",
    )
    manual_gcode = "\n".join(manual_lines)
    assert "( *** MANUAL ROUTER: SET SPEED DIAL TO 2.8 (~16,000 RPM) *** )" in manual_gcode
    assert "M3" not in manual_gcode

    vfd_lines = standard.format_spindle_start(
        rpm=16000,
        spindle_type="vfd_auto",
    )
    vfd_gcode = "\n".join(vfd_lines)
    assert "M3 S16000" in vfd_gcode


def test_surfacing_generator_with_manual_router():
    prog = generate_surfacing(
        length_x=100.0,
        width_y=80.0,
        origin_x=0.0,
        origin_y=0.0,
        total_depth_z=1.0,
        stepdown_z=0.5,
        tool_diameter=25.4,
        spindle_speed=16000,
        spindle_type="manual_router",
        router_model="makita_rt0701c",
    )
    assert "( *** MANUAL ROUTER: SET SPEED DIAL TO 2.8 (~16,000 RPM) *** )" in prog.gcode
    assert "M3" not in prog.gcode
