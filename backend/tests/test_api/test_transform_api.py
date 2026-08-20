def test_api_shift(client):
    payload = {
        "gcode": "G0 X10 Y20 Z5\nG1 X50 Y50 Z-2 F800",
        "delta_x": 5.0,
        "delta_y": -10.0,
        "delta_z": 1.0,
    }
    res = client.post("/api/transform/shift", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "X15.000" in data["gcode"]
    assert "Y10.000" in data["gcode"]


def test_api_rotate(client):
    payload = {
        "gcode": "G1 X10 Y0 F500",
        "angle_deg": 180.0,
    }
    res = client.post("/api/transform/rotate", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "X-10.000" in data["gcode"]


def test_api_mirror(client):
    payload = {
        "gcode": "G2 X10 Y20 I5 J0",
        "mirror_axis": "y",
    }
    res = client.post("/api/transform/mirror", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "G3" in data["gcode"]
    assert "X-10.000" in data["gcode"]


def test_api_feed_speed_override(client):
    payload = {
        "gcode": "G1 X10 Y20 F1000\nS10000 M3",
        "feed_percent": 120.0,
        "speed_percent": 80.0,
    }
    res = client.post("/api/transform/feed-speed-override", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "F1200.0" in data["gcode"]
    assert "S8000" in data["gcode"]


def test_api_split_tools(client):
    payload = {
        "gcode": "T1 M6\nG1 X0 Y0 Z-5\nT2 M6\nG1 X10 Y10 Z-2",
        "safe_retract_z": 10.0,
    }
    res = client.post("/api/transform/split-tools", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] == 2
    assert len(data["sub_programs"]) == 2
