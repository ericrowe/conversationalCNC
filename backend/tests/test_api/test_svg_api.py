import pytest


def test_api_parse_svg(client):
    svg_data = """<svg width="80mm" height="40mm" viewBox="0 0 80 40">
      <rect x="0" y="0" width="80" height="40" fill="#000000" />
      <circle cx="40" cy="20" r="5" fill="#808080" />
    </svg>"""

    res = client.post("/api/generate/svg/parse", json={
        "svg_text": svg_data,
        "max_cut_depth": -5.0,
    })

    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["entity_count"] == 2
    assert len(data["data"]["chains"]) == 1
    assert len(data["data"]["circles"]) == 1


def test_api_parse_svg_with_target_dimensions(client):
    svg_data = """<svg width="80mm" height="40mm" viewBox="0 0 80 40">
      <rect x="0" y="0" width="80" height="40" fill="#000000" />
    </svg>"""

    res = client.post("/api/generate/svg/parse", json={
        "svg_text": svg_data,
        "target_width": 160.0,
        "target_height": 80.0,
    })

    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["bounding_box"]["width"] == pytest.approx(160.0, abs=0.1)
    assert data["data"]["bounding_box"]["height"] == pytest.approx(80.0, abs=0.1)
    assert data["data"]["original_dimensions"]["width"] == pytest.approx(80.0, abs=0.1)
    assert data["data"]["original_dimensions"]["height"] == pytest.approx(40.0, abs=0.1)


def test_api_generate_svg_toolpath(client):
    svg_data = """<svg width="80mm" height="40mm" viewBox="0 0 80 40">
      <rect x="0" y="0" width="80" height="40" fill="#000000" />
    </svg>"""

    parse_res = client.post("/api/generate/svg/parse", json={
        "svg_text": svg_data,
        "max_cut_depth": -4.5,
    })
    parsed = parse_res.get_json()["data"]

    toolpath_res = client.post("/api/generate/svg/toolpath", json={
        "chains": parsed["chains"],
        "circles": parsed["circles"],
        "operation_type": "contour",
        "side": "left",
        "stepdown_z": 1.5,
        "tool_diameter": 3.175,
        "feed_rate_xy": 800.0,
        "plunge_feed": 250.0,
        "spindle_speed": 16000,
    })

    assert toolpath_res.status_code == 200
    tp_data = toolpath_res.get_json()
    assert tp_data["success"] is True
    assert "gcode" in tp_data["data"]
    assert "Z-4.500" in tp_data["data"]["gcode"]


def test_api_parse_svg_validation_error(client):
    res = client.post("/api/generate/svg/parse", json={
        "svg_text": "short",
    })
    assert res.status_code == 400
