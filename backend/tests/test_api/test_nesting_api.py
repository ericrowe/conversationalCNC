import pytest


def test_api_generate_nesting_grid(client):
    payload = {
        "gcode": "G0 X0 Y0\nG1 Z-2.0 F200\nG1 X20 Y0\nG0 Z5",
        "cols_x": 2,
        "rows_y": 2,
        "spacing_x": 50.0,
        "spacing_y": 40.0,
        "layout_pattern": "grid",
        "order_strategy": "zigzag",
        "safe_z_retract": 5.0,
    }

    res = client.post("/api/generate/nesting/grid", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["total_instances"] == 4
    assert "G21 G90 G94 G17 G54" in data["data"]["gcode"]


def test_api_generate_soft_jaw(client):
    payload = {
        "jaw_type": "rectangular",
        "part_length_x": 60.0,
        "part_width_y": 30.0,
        "step_depth_z": 3.0,
        "jaw_gap": 10.0,
        "dogbone_relief": True,
        "tool_diameter": 6.35,
        "stepdown_z": 1.5,
        "feed_rate_xy": 900.0,
        "plunge_feed": 200.0,
        "spindle_speed": 16000,
    }

    res = client.post("/api/generate/nesting/soft-jaw", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "data" in data
    assert "CORNER DOGBONE RELIEFS" in data["data"]["gcode"]


def test_api_nesting_validation_error(client):
    # Invalid spacing <= 0
    payload = {
        "gcode": "G1 X0 Y0",
        "spacing_x": -10.0,
    }
    res = client.post("/api/generate/nesting/grid", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert "Validation error" in data["error"]
