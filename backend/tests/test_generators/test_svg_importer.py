import pytest
from app.generators.svg_importer import (
    parse_color_to_luminance,
    parse_svg,
    generate_svg_toolpath,
)


def test_parse_color_to_luminance():
    # Hex colors
    lum_black, hex_b = parse_color_to_luminance("#000000")
    assert lum_black == pytest.approx(0.0, abs=0.01)
    assert hex_b == "#000000"

    lum_white, hex_w = parse_color_to_luminance("#ffffff")
    assert lum_white == pytest.approx(1.0, abs=0.01)
    assert hex_w == "#ffffff"

    lum_gray, hex_g = parse_color_to_luminance("#808080")
    assert lum_gray == pytest.approx(0.5, abs=0.05)

    # Named colors
    lum_named_black, _ = parse_color_to_luminance("black")
    assert lum_named_black == pytest.approx(0.0, abs=0.01)

    lum_named_white, _ = parse_color_to_luminance("white")
    assert lum_named_white == pytest.approx(1.0, abs=0.01)


def test_parse_svg_shapes_and_shading():
    svg_sample = """<svg width="100mm" height="50mm" viewBox="0 0 100 50">
      <rect x="5" y="5" width="90" height="40" fill="#000000" />
      <circle cx="50" cy="25" r="10" fill="#808080" />
      <line x1="10" y1="10" x2="40" y2="10" stroke="#000000" />
    </svg>"""

    parsed = parse_svg(svg_sample, max_cut_depth=-6.0)

    assert parsed["entity_count"] == 3
    assert len(parsed["chains"]) == 2  # rect + line
    assert len(parsed["circles"]) == 1

    # Check 100% black rect
    rect_chain = next(c for c in parsed["chains"] if c["tag"] == "rect")
    assert rect_chain["shading_percent"] == pytest.approx(100.0, abs=1.0)
    assert rect_chain["target_depth_z"] == pytest.approx(-6.0, abs=0.1)
    assert rect_chain["is_closed"] is True

    # Check 50% gray circle
    circle_entity = parsed["circles"][0]
    assert circle_entity["shading_percent"] == pytest.approx(50.0, abs=2.0)
    assert circle_entity["target_depth_z"] == pytest.approx(-3.0, abs=0.2)
    assert circle_entity["radius"] == pytest.approx(10.0, abs=0.1)


def test_parse_svg_path_bezier():
    svg_path_sample = """<svg width="60mm" height="40mm" viewBox="0 0 60 40">
      <path d="M 10 10 C 20 20, 40 20, 50 10 Z" fill="#000000" />
    </svg>"""

    parsed = parse_svg(svg_path_sample, max_cut_depth=-4.0)
    assert len(parsed["chains"]) == 1
    chain = parsed["chains"][0]
    assert chain["is_closed"] is True
    assert chain["target_depth_z"] == pytest.approx(-4.0, abs=0.1)
    assert len(chain["segments"]) > 5  # Subdivided Bezier points


def test_generate_svg_multi_depth_toolpath():
    svg_sample = """<svg width="100mm" height="50mm" viewBox="0 0 100 50">
      <rect x="5" y="5" width="90" height="40" fill="#000000" />
      <circle cx="20" cy="25" r="2.5" fill="#000000" />
      <circle cx="80" cy="25" r="2.5" fill="#808080" />
    </svg>"""

    parsed = parse_svg(svg_sample, max_cut_depth=-6.0)
    result = generate_svg_toolpath(
        chains=parsed["chains"],
        circles=parsed["circles"],
        operation_type="auto",
        stepdown_z=1.5,
        tool_diameter=3.175,
        dialect="grbl",
    )

    assert result["chain_count"] == 1
    assert result["hole_count"] == 2
    assert "G21 G90" in result["gcode"]
    assert "Z-6.000" in result["gcode"]  # Full depth pass
    assert "Z-2.988" in result["gcode"] or "Z-3.000" in result["gcode"]  # 50% depth hole


def test_parse_svg_manual_scaling():
    svg_sample = """<svg width="100mm" height="50mm" viewBox="0 0 100 50">
      <rect x="0" y="0" width="100" height="50" fill="#000000" />
    </svg>"""

    # 1. Scaling Width with aspect ratio preserved
    scaled_w = parse_svg(svg_sample, target_width=200.0)
    assert scaled_w["bounding_box"]["width"] == pytest.approx(200.0, abs=0.1)
    assert scaled_w["bounding_box"]["height"] == pytest.approx(100.0, abs=0.1)
    assert scaled_w["original_dimensions"]["width"] == pytest.approx(100.0, abs=0.1)
    assert scaled_w["original_dimensions"]["height"] == pytest.approx(50.0, abs=0.1)

    # 2. Scaling Height with aspect ratio preserved
    scaled_h = parse_svg(svg_sample, target_height=25.0)
    assert scaled_h["bounding_box"]["width"] == pytest.approx(50.0, abs=0.1)
    assert scaled_h["bounding_box"]["height"] == pytest.approx(25.0, abs=0.1)

    # 3. Independent Non-Uniform Scaling (Unlinked width and height)
    scaled_both = parse_svg(svg_sample, target_width=150.0, target_height=80.0)
    assert scaled_both["bounding_box"]["width"] == pytest.approx(150.0, abs=0.1)
    assert scaled_both["bounding_box"]["height"] == pytest.approx(80.0, abs=0.1)
