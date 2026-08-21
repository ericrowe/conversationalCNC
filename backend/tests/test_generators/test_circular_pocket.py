import pytest
from app.generators.circular_pocket import generate_circular_pocket, generate_circular_boss
from app.generators.sequencer import generate_job_sequence
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


def test_circular_boss_generation_round_stock():
    """Test machining an M10 bolt shaft (Ø10mm) from Ø25mm round bar stock."""
    prog = generate_circular_boss(
        boss_center_x=0.0,
        boss_center_y=0.0,
        boss_diameter=10.0,
        stock_shape="circle",
        stock_diameter=25.0,
        target_depth_z=-15.0,
        stepdown_z=5.0,
        stepover_percent=50.0,
        finish_allowance=0.2,
        tool_diameter=6.35,
        feed_rate_xy=800.0,
        plunge_feed=250.0,
        spindle_speed=16000,
    )
    assert prog.gcode is not None
    assert "Depth Pass 1/3" in prog.gcode
    assert "Depth Pass 2/3" in prog.gcode
    assert "Depth Pass 3/3" in prog.gcode
    assert "Plunge in Open Air" in prog.gcode
    assert "Climb Cut Ring" in prog.gcode
    assert "Wall Finishing Pass" in prog.gcode
    assert "G2" in prog.gcode
    assert prog.bounds.min_z == -15.0
    assert prog.bounds.max_z == 5.0


def test_circular_boss_generation_rect_stock():
    """Test machining a raised cylindrical boss from square billet stock."""
    prog = generate_circular_boss(
        boss_center_x=20.0,
        boss_center_y=20.0,
        boss_diameter=12.0,
        stock_shape="rectangle",
        stock_length_x=30.0,
        stock_width_y=30.0,
        target_depth_z=-8.0,
        stepdown_z=2.0,
        finish_allowance=0.3,
        tool_diameter=6.35,
    )
    assert prog.gcode is not None
    assert "Depth Pass 1/4" in prog.gcode
    assert "Wall Finishing Pass" in prog.gcode
    assert prog.bounds.min_z == -8.0


def test_circular_boss_validation():
    # Stock smaller than boss
    with pytest.raises(ValueError, match="must be strictly larger than boss diameter"):
        generate_circular_boss(
            boss_diameter=20.0,
            stock_diameter=15.0,
            stock_shape="circle",
        )

    # Rectangular stock smaller than boss
    with pytest.raises(ValueError, match="must be strictly larger than boss diameter"):
        generate_circular_boss(
            boss_diameter=25.0,
            stock_length_x=20.0,
            stock_width_y=20.0,
            stock_shape="rectangle",
        )

    # Zero or negative boss diameter
    with pytest.raises(ValueError, match="Boss diameter must be greater than zero"):
        generate_circular_boss(boss_diameter=0.0)


def test_bolt_machining_sequencer_integration():
    """Test full multi-op bolt machining sequence in Job Builder (Boss -> External Thread)."""
    ops = [
        {
            "op_name": "Step 1: M10 Shaft Boss Turning",
            "op_type": "circular_boss",
            "tool_number": 1,
            "tool_name": "1/4in Flat Endmill",
            "tool_diameter": 6.35,
            "spindle_speed": 16000,
            "params": {
                "boss_center_x": 0.0,
                "boss_center_y": 0.0,
                "boss_diameter": 10.0,
                "stock_shape": "circle",
                "stock_diameter": 25.0,
                "target_depth_z": -20.0,
                "stepdown_z": 2.0,
                "tool_diameter": 6.35,
            },
        },
        {
            "op_name": "Step 2: M10x1.5 External Thread Milling",
            "op_type": "thread_milling",
            "tool_number": 2,
            "tool_name": "Single-Point Thread Mill",
            "tool_diameter": 4.0,
            "spindle_speed": 18000,
            "params": {
                "holes": [(0.0, 0.0)],
                "nominal_diameter": 10.0,
                "pitch": 1.5,
                "thread_length": 18.0,
                "tool_diameter": 4.0,
                "thread_type": "external",
            },
        },
    ]

    result = generate_job_sequence(
        operations=ops,
        safe_z_retract=5.0,
        optimize_tool_order=False,
    )

    assert result["gcode"] is not None
    assert "STEP 1: M10 SHAFT BOSS TURNING" in result["gcode"].upper()
    assert "STEP 2: M10X1.5 EXTERNAL THREAD MILLING" in result["gcode"].upper()
    assert "M6 T1" in result["gcode"] or "T1" in result["gcode"]
    assert "M6 T2" in result["gcode"] or "T2" in result["gcode"]
