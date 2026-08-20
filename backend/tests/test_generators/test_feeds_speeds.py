import pytest
from app.generators.feeds_speeds import calculate_feeds_and_speeds, MATERIAL_PHYSICS_CATALOG


def test_softwood_feeds_speeds():
    # 1/4" (6.35mm) 2-flute endmill in pine
    res = calculate_feeds_and_speeds(
        material_key="softwood_pine",
        tool_diameter_mm=6.35,
        num_flutes=2,
        stepover_mm=3.175,
        stepdown_mm=3.175,
    )
    assert res["recommended_rpm"] >= 15000
    assert res["recommended_feed_xy"] > 1000
    assert res["mrr_cm3_min"] > 0
    assert res["estimated_power_kw"] > 0


def test_radial_chip_thinning():
    # Full slotting (stepover = tool diameter)
    slot_res = calculate_feeds_and_speeds(
        material_key="aluminum_6061",
        tool_diameter_mm=6.35,
        num_flutes=2,
        stepover_mm=6.35,
    )
    assert slot_res["rctf_multiplier"] == 1.0

    # 10% radial stepover (0.635mm) -> chip thinning factor > 1.5x
    light_res = calculate_feeds_and_speeds(
        material_key="aluminum_6061",
        tool_diameter_mm=6.35,
        num_flutes=2,
        stepover_mm=0.635,
    )
    assert light_res["rctf_multiplier"] > 1.5
    assert light_res["compensated_chipload_mm"] > slot_res["nominal_chipload_mm"]


def test_tool_deflection_warning():
    # 3.175mm tool with 20mm stickout (>6x diameter)
    res = calculate_feeds_and_speeds(
        material_key="hardwood_oak",
        tool_diameter_mm=3.175,
        num_flutes=2,
        tool_stickout_mm=20.0,
    )
    assert any("deflection" in w.lower() for w in res["warnings"])


def test_belt_driven_conservative_feeds_speeds():
    # 1/8" (3.175mm) 2-flute in Softwood
    res_1_8 = calculate_feeds_and_speeds(
        material_key="softwood_pine",
        tool_diameter_mm=3.175,
        num_flutes=2,
    )
    # Feeds should be in the conservative 800 - 1050 mm/min range (matching Easel ~35-40 in/min)
    assert 700 <= res_1_8["recommended_feed_xy"] <= 1100
    # Plunge should be capped conservatively (< 250 mm/min) to prevent missed Z steps on belt/leadscrew
    assert res_1_8["recommended_plunge_feed"] <= 250.0
    assert res_1_8["recommended_stepdown_mm"] <= 1.2

    # 1/4" (6.35mm) 2-flute in Aluminum 6061
    res_alu = calculate_feeds_and_speeds(
        material_key="aluminum_6061",
        tool_diameter_mm=6.35,
        num_flutes=2,
    )
    # Conservative aluminum feed for belt CNC: 250-450 mm/min
    assert 200 <= res_alu["recommended_feed_xy"] <= 500
    assert res_alu["recommended_plunge_feed"] <= 100.0
    # Very shallow depth per pass for aluminum rigidity safety
    assert res_alu["recommended_stepdown_mm"] <= 0.40


def test_invalid_parameters():
    with pytest.raises(ValueError):
        calculate_feeds_and_speeds(material_key="softwood_pine", tool_diameter_mm=-5.0)
    with pytest.raises(ValueError):
        calculate_feeds_and_speeds(material_key="softwood_pine", tool_diameter_mm=6.35, num_flutes=0)

