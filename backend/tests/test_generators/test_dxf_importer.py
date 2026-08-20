import pytest
from app.generators.dxf_importer import parse_dxf_ascii, generate_dxf_toolpath


SAMPLE_DXF = """0
SECTION
2
ENTITIES
0
LINE
8
OUTLINE
10
0.0
20
0.0
11
50.0
21
0.0
0
LINE
8
OUTLINE
10
50.0
20
0.0
11
50.0
21
30.0
0
LINE
8
OUTLINE
10
50.0
20
30.0
11
0.0
21
30.0
0
LINE
8
OUTLINE
10
0.0
20
30.0
11
0.0
21
0.0
0
CIRCLE
8
HOLES
10
15.0
20
15.0
40
3.0
0
CIRCLE
8
HOLES
10
35.0
20
15.0
40
3.0
0
ENDSEC
0
EOF"""


def test_parse_dxf_ascii_lines_and_circles():
    res = parse_dxf_ascii(SAMPLE_DXF)
    assert res["entity_count"] == 6
    assert set(res["layers"]) == {"OUTLINE", "HOLES"}
    assert len(res["circles"]) == 2
    assert res["circles"][0]["x"] == 15.0
    assert res["circles"][0]["y"] == 15.0
    assert res["circles"][0]["diameter"] == 6.0
    assert len(res["chains"]) == 1
    assert res["chains"][0]["is_closed"] is True
    assert res["bounding_box"]["width"] == 50.0
    assert res["bounding_box"]["height"] == 30.0


def test_generate_dxf_contour_toolpath():
    parsed = parse_dxf_ascii(SAMPLE_DXF)
    res = generate_dxf_toolpath(
        chains=parsed["chains"],
        operation_type="contour",
        side="left",
        target_depth_z=-4.0,
        stepdown_z=2.0,
        tool_diameter=3.175,
        feed_rate_xy=800.0,
        plunge_feed=250.0,
        spindle_speed=16000,
        safe_z_retract=5.0,
        dialect="grbl",
    )
    assert "gcode" in res
    gcode = res["gcode"]
    assert "G21 G90 G94" in gcode
    assert "DXF CAD Importer Toolpath" in gcode
    assert "M5" in gcode
    assert "M2" in gcode


def test_generate_dxf_drill_toolpath():
    parsed = parse_dxf_ascii(SAMPLE_DXF)
    res = generate_dxf_toolpath(
        chains=[],
        circles=parsed["circles"],
        operation_type="drill",
        target_depth_z=-5.0,
        tool_diameter=3.0,
        tool_number=1,
        feed_rate_xy=800.0,
        plunge_feed=200.0,
        spindle_speed=16000,
        safe_z_retract=5.0,
        dialect="grbl",
    )
    assert "gcode" in res
    gcode = res["gcode"]
    assert "X15.000 Y15.000" in gcode
    assert "X35.000 Y15.000" in gcode
