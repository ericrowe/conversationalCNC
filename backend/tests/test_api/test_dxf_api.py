import pytest

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



def test_api_parse_dxf(client):
    res = client.post("/api/generate/dxf/parse", json={"dxf_text": SAMPLE_DXF})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["entity_count"] == 6
    assert len(data["data"]["circles"]) == 2
    assert len(data["data"]["chains"]) == 1


def test_api_generate_dxf_toolpath(client):
    parse_res = client.post("/api/generate/dxf/parse", json={"dxf_text": SAMPLE_DXF})
    parsed = parse_res.get_json()["data"]

    payload = {
        "chains": parsed["chains"],
        "circles": parsed["circles"],
        "operation_type": "contour",
        "side": "left",
        "target_depth_z": -3.0,
        "stepdown_z": 1.5,
        "tool_diameter": 3.175,
        "feed_rate_xy": 800.0,
        "plunge_feed": 250.0,
        "spindle_speed": 16000,
        "safe_z_retract": 5.0,
    }
    res = client.post("/api/generate/dxf/toolpath", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "gcode" in data["data"]
    assert "G21 G90" in data["data"]["gcode"]


def test_api_parse_dxf_validation_error(client):
    res = client.post("/api/generate/dxf/parse", json={"dxf_text": "short"})
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
