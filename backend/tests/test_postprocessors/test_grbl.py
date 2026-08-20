import pytest
from app.postprocessors import GrblPostProcessor, get_postprocessor
from app.postprocessors.registry import StandardPostProcessor

def test_grbl_postprocessor_properties():
    grbl = GrblPostProcessor()
    assert grbl.dialect_name == "grbl"
    assert grbl.supports_canned_cycles is False

def test_grbl_header_and_footer():
    grbl = GrblPostProcessor()
    header = grbl.format_header(units="mm", absolute_mode=True)
    assert any("G21 G90 G94 G17" in line for line in header)

    footer = grbl.format_footer(park_z=5.0, park_x=0.0, park_y=0.0)
    assert any("M5" in line for line in footer)
    assert any("G0 Z5.000" in line for line in footer)
    assert any("G0 X0.000 Y0.000" in line for line in footer)
    assert any("M2" in line for line in footer)

def test_grbl_dwell_format():
    grbl = GrblPostProcessor()
    dwell_line = grbl.format_dwell(2.5)
    assert dwell_line == "G4 P2.50"

def test_grbl_straight_drill_expansion():
    grbl = GrblPostProcessor()
    lines = grbl.format_straight_drill(
        x=25.0,
        y=50.0,
        start_z=0.0,
        target_depth_z=-6.0,
        retract_z=5.0,
        plunge_feed=300.0,
        dwell_seconds=1.0,
        approach_clearance=1.0,
    )
    combined = "\n".join(lines)
    # Ensure NO canned cycle codes exist
    assert "G81" not in combined
    assert "G83" not in combined
    assert "G82" not in combined
    
    # Ensure linear motions exist
    assert "G0 Z5.000" in combined
    assert "G0 X25.000 Y50.000" in combined
    assert "G0 Z1.000" in combined
    assert "G1 Z-6.000 F300.0" in combined
    assert "G4 P1.00" in combined

def test_dialect_registry():
    grbl = get_postprocessor("grbl")
    assert isinstance(grbl, GrblPostProcessor)

    grblhal = get_postprocessor("grblhal")
    assert isinstance(grblhal, GrblPostProcessor)

    standard = get_postprocessor("standard")
    assert isinstance(standard, StandardPostProcessor)
    assert standard.supports_canned_cycles is True
