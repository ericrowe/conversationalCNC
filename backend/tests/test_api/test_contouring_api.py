import pytest


def test_api_generate_contouring(client):
    payload = {
        "segments": [
            {"type": "line", "x": 50.0, "y": 0.0},
            {"type": "line", "x": 50.0, "y": 40.0},
            {"type": "line", "x": 0.0, "y": 40.0},
            {"type": "line", "x": 0.0, "y": 0.0},
        ],
        "start_point": [0.0, 0.0],
        "side": "left",
        "lead_in_type": "tangential_arc",
        "lead_in_radius": 5.0,
        "target_depth_z": -3.0,
        "stepdown_z": 1.5,
        "finish_allowance": 0.2,
        "spring_pass": True,
        "feed_rate_xy": 900.0,
        "plunge_feed": 200.0,
        "spindle_speed": 18000,
    }

    res = client.post("/api/generate/milling/contour", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "data" in data
    assert "G21 G90 G94 G17 G54" in data["data"]["gcode"]
    assert data["data"]["segment_count"] == 4
    assert data["dialect_used"] == "grbl"


def test_api_contouring_invalid_payload(client):
    # Invalid stepdown <= 0
    payload = {
        "stepdown_z": -1.0,
    }
    res = client.post("/api/generate/milling/contour", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert "Validation error" in data["error"]
