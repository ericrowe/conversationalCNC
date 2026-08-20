import pytest
from app.generators.rectangular_pocket import (
    generate_rectangular_pocket,
    generate_rectangular_boss,
)
from app.generators.drilling import compute_bolt_circle_holes, compute_grid_holes
from app.generators.base import WorkEnvelope
from app.postprocessors.grbl import GrblPostProcessor


def test_bolt_circle_calculation():
    # 4 holes at 90 deg intervals on 100mm dia circle centered at (50, 50)
    holes = compute_bolt_circle_holes(
        center_x=50.0,
        center_y=50.0,
        diameter=100.0,
        num_holes=4,
        start_angle_deg=0.0,
        arc_span_deg=360.0,
    )
    assert len(holes) == 4
    assert (100.0, 50.0) in holes
    assert (50.0, 100.0) in holes
    assert (0.0, 50.0) in holes
    assert (50.0, 0.0) in holes


def test_grid_holes_calculation():
    # 3x2 grid with 20mm spacing
    holes = compute_grid_holes(
        origin_x=10.0,
        origin_y=10.0,
        num_x=3,
        num_y=2,
        spacing_x=20.0,
        spacing_y=20.0,
    )
    assert len(holes) == 6
    assert (10.0, 10.0) in holes
    assert (30.0, 10.0) in holes
    assert (50.0, 10.0) in holes
    # Row 1 is serpentine reversed
    assert (50.0, 30.0) in holes
    assert (30.0, 30.0) in holes
    assert (10.0, 30.0) in holes


def test_rectangular_pocket_generation():
    program = generate_rectangular_pocket(
        origin_x=50.0,
        origin_y=50.0,
        length_x=60.0,
        width_y=40.0,
        corner_radius=5.0,
        origin_mode="center",
        target_depth_z=-4.5,
        stepdown_z=1.5,
        tool_diameter=6.35,
        stepover_percent=60.0,
        finish_pass_allowance=0.3,
        entry_strategy="helical_ramp",
    )
    assert program.gcode is not None
    assert "Operation: Rectangular Pocket" in program.gcode
    assert "G2" in program.gcode  # Helical ramp
    assert "Wall Finish Pass" in program.gcode
    assert program.bounds.min_z == -4.5
    assert program.bounds.min_x == 20.0
    assert program.bounds.max_x == 80.0


def test_rectangular_pocket_tool_too_large():
    with pytest.raises(ValueError, match="strictly greater than tool diameter"):
        generate_rectangular_pocket(
            origin_x=50.0,
            origin_y=50.0,
            length_x=5.0,
            width_y=5.0,
            tool_diameter=6.35,
        )


def test_rectangular_boss_generation():
    program = generate_rectangular_boss(
        boss_origin_x=50.0,
        boss_origin_y=50.0,
        boss_length_x=40.0,
        boss_width_y=30.0,
        stock_length_x=80.0,
        stock_width_y=60.0,
        boss_corner_radius=3.0,
        target_depth_z=-3.0,
        stepdown_z=1.5,
        tool_diameter=6.35,
    )
    assert program.gcode is not None
    assert "Operation: Rectangular Boss" in program.gcode
    assert program.bounds.min_x == 10.0  # 50 - 40
    assert program.bounds.max_x == 90.0  # 50 + 40
    assert program.bounds.min_z == -3.0
