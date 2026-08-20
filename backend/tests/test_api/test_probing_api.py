def test_api_z_touch_plate(client):
    payload = {
        "plate_thickness": 14.85,
        "search_dist": 30.0,
        "fast_feed": 150.0,
        "slow_feed": 25.0,
        "retract_height": 20.0,
    }
    res = client.post("/api/probing/z-touch-plate", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "G10 L20 P1 Z14.850" in data["data"]["gcode"]


def test_api_corner_xyz(client):
    payload = {
        "tool_diameter": 6.35,
        "plate_thickness": 14.85,
        "block_x_lip": 10.0,
        "block_y_lip": 10.0,
    }
    res = client.post("/api/probing/corner-xyz", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "G10 L20 P1 X-13.175" in data["data"]["gcode"]


def test_api_homing(client):
    res = client.get("/api/probing/homing")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "$H" in data["data"]["gcode"]
