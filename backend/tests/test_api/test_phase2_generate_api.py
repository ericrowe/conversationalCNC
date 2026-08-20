import pytest

def test_thread_standards_api(client):
    res = client.get("/api/generate/thread-standards")
    assert res.status_code == 200
    data = res.get_json()
    assert "standards" in data
    assert "M6x1.0" in data["standards"]
    assert "1/4-20 UNC" in data["standards"]

def test_thread_milling_api(client):
    payload = {
        "holes": [[25.0, 25.0]],
        "thread_standard": "M6x1.0",
        "thread_length": 10.0,
        "tool_diameter": 4.5,
        "radial_passes": 2,
    }
    res = client.post("/api/generate/thread-milling", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "M6x1.0" in data["data"]["gcode"] or "6.0" in data["data"]["gcode"]
    assert "G3" in data["data"]["gcode"]

def test_peck_drilling_api(client):
    payload = {
        "holes": [[10.0, 10.0]],
        "target_depth_z": -12.0,
        "peck_depth": 4.0,
    }
    res = client.post("/api/generate/drilling/peck", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "Peck 1/3" in data["data"]["gcode"]

def test_circular_pocket_api(client):
    payload = {
        "pockets": [[30.0, 30.0]],
        "pocket_diameter": 20.0,
        "target_depth_z": -4.0,
        "tool_diameter": 3.175,
        "stepdown_z": 2.0,
    }
    res = client.post("/api/generate/pocket/circular", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "Finish Wall Pass" in data["data"]["gcode"]

def test_surfacing_api(client):
    payload = {
        "length_x": 120.0,
        "width_y": 80.0,
        "total_depth_z": 0.5,
        "stepdown_z": 0.5,
        "tool_diameter": 25.4,
    }
    res = client.post("/api/generate/surfacing", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "Surfacing / Facing" in data["data"]["gcode"]

def test_text_engraving_api(client):
    payload = {
        "text": "SERIAL #1042",
        "layout_mode": "linear",
        "start_x": 15.0,
        "start_y": 25.0,
        "font_size": 8.0,
        "font_name": "duplex_sans",
        "target_depth_z": -0.3,
        "stepdown_z": 0.3,
    }
    res = client.post("/api/generate/engraving/text", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "Text Engraving" in data["data"]["gcode"]

def test_engraving_fonts_api(client):
    res = client.get("/api/generate/engraving/fonts")
    assert res.status_code == 200
    data = res.get_json()
    assert "fonts" in data
    assert "simplex_sans" in data["fonts"]
    assert "roman_serif" in data["fonts"]
    assert "cursive_script" in data["fonts"]


