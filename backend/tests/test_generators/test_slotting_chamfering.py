import pytest
from app.generators.slotting import generate_linear_slot
from app.generators.chamfering import (
    generate_rectangular_chamfer,
    calculate_chamfer_depth_and_offset,
)


def test_linear_slot_single_pass():
    program = generate_linear_slot(
        start_x=10.0,
        start_y=20.0,
        end_x=60.0,
        end_y=20.0,
        slot_width=3.175,
        target_depth_z=-3.0,
        stepdown_z=1.0,
        tool_diameter=3.175,
    )
    assert program.gcode is not None
    assert "Operation: Linear Slot" in program.gcode
    assert program.bounds.min_x == 10.0
    assert program.bounds.max_x == 60.0
    assert program.bounds.min_z == -3.0


def test_linear_slot_wide():
    program = generate_linear_slot(
        start_x=10.0,
        start_y=20.0,
        end_x=60.0,
        end_y=20.0,
        slot_width=6.0,
        target_depth_z=-2.0,
        stepdown_z=1.0,
        tool_diameter=3.175,
    )
    assert program.gcode is not None
    assert "Pass 1/2" in program.gcode
    # Should have multiple lines of cuts for side passes
    assert len(program.lines) > 15


def test_linear_slot_tool_larger_than_width():
    with pytest.raises(ValueError, match="cannot be smaller than tool diameter"):
        generate_linear_slot(
            start_x=10.0,
            start_y=20.0,
            end_x=60.0,
            end_y=20.0,
            slot_width=3.0,
            tool_diameter=6.35,
        )


def test_chamfer_depth_calculation():
    # 90 deg V-bit (half angle 45 deg, tan=1.0)
    # chamfer width = 1.0mm, tip offset = 0.5mm
    # depth = -(1.0/1.0 + 0.5) = -1.5mm
    depth_z, radial_offset = calculate_chamfer_depth_and_offset(
        chamfer_width=1.0,
        vbit_angle_deg=90.0,
        tip_diameter=0.2,
        tip_offset=0.5,
    )
    assert depth_z == -1.5
    # radial_offset = (0.2/2) + (0.5 * 1.0) = 0.6mm
    assert radial_offset == 0.6


def test_rectangular_chamfer_outside():
    program = generate_rectangular_chamfer(
        origin_x=50.0,
        origin_y=50.0,
        length_x=60.0,
        width_y=40.0,
        chamfer_width=0.5,
        corner_radius=4.0,
        vbit_angle_deg=90.0,
        feature_type="outside",
    )
    assert program.gcode is not None
    assert "Operation: 2D Chamfering" in program.gcode
    assert program.bounds.min_z < 0.0
