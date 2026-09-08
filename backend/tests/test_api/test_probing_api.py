def test_api_z_touch_plate(client):
    payload = {
        "plate_thickness": 14.85,
        "search_dist": 30.0,
        "fast_feed": 150.0,
        "slow_feed": 25.0,
        "retract_height": 20.0,
    }
    # Test primary and alias endpoints
    for endpoint in ("/api/probing/z-touch-plate", "/api/probing/z"):
        res = client.post(endpoint, json=payload)
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
        "corner": "front_left",
    }
    for endpoint in ("/api/probing/corner-xyz", "/api/probing/xyz"):
        res = client.post(endpoint, json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "G10 L20 P1 X-13.175" in data["data"]["gcode"]
        assert "G10 L20 P1 Y-13.175" in data["data"]["gcode"]


def test_api_corner_xyz_orientations(client):
    # Front-right corner test
    payload = {
        "tool_diameter": 4.0,
        "plate_thickness": 10.0,
        "block_x_lip": 8.0,
        "block_y_lip": 8.0,
        "corner": "front_right",
    }
    res = client.post("/api/probing/xyz", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "G10 L20 P1 X10.000" in data["data"]["gcode"]
    assert "G10 L20 P1 Y-10.000" in data["data"]["gcode"]


def test_api_bore_center(client):
    payload = {
        "approx_diameter": 50.0,
        "tool_diameter": 6.35,
        "search_dist": 30.0,
    }
    res = client.post("/api/probing/bore-center", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "IN-BORE 4-POINT CENTER PROBE" in data["data"]["gcode"]
    assert "G10 L20 P1 X0.000 Y0.000" in data["data"]["gcode"]


def test_api_boss_center(client):
    payload = {
        "approx_diameter": 40.0,
        "tool_diameter": 6.35,
    }
    res = client.post("/api/probing/boss-center", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "OUTSIDE BOSS 4-POINT CENTER PROBE" in data["data"]["gcode"]
    assert "G10 L20 P1 X0.000 Y0.000" in data["data"]["gcode"]


def test_api_homing(client):
    res = client.get("/api/probing/homing")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "$H" in data["data"]["gcode"]
