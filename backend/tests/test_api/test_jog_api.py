def test_api_jog_step(client):
    payload = {
        "axis": "X",
        "distance": 10.0,
        "feed_rate": 1200.0,
        "units": "mm",
        "dialect": "grbl",
    }
    res = client.post("/api/jog/step", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "$J=G91 G21 X+10.000 F1200.0" in data["data"]["gcode"]


def test_api_jog_zero(client):
    payload = {
        "axes": ["X", "Y"],
        "wcs_slot": 1,
    }
    res = client.post("/api/jog/zero", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "G10 L20 P1 X0.000 Y0.000" in data["data"]["gcode"]


def test_api_jog_goto_origin(client):
    payload = {
        "safe_z_retract": 10.0,
        "units": "mm",
    }
    res = client.post("/api/jog/goto-origin", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "G0 Z10.000" in data["data"]["gcode"]
    assert "G0 X0.000 Y0.000" in data["data"]["gcode"]


def test_api_jog_spindle(client):
    payload = {
        "rpm": 15000,
        "state": True,
        "clockwise": True,
    }
    res = client.post("/api/jog/spindle", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "M3 S15000" in data["data"]["gcode"]
