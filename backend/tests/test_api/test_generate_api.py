def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "online"

def test_get_dialects(client):
    response = client.get("/api/generate/dialects")
    assert response.status_code == 200
    data = response.get_json()
    assert "grbl" in data["available_dialects"]

def test_generate_straight_plunge_api(client):
    payload = {
        "x": 25.0,
        "y": 50.0,
        "target_depth_z": -6.0,
        "start_z": 0.0,
        "plunge_feed": 300.0,
        "spindle_speed": 16000,
        "dwell_seconds": 1.0,
    }
    response = client.post("/api/generate/drilling/straight-plunge", json=payload)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["success"] is True
    assert "G21 G90 G94 G17" in res_data["data"]["gcode"]
    assert "G1 Z-6.000 F300.0" in res_data["data"]["gcode"]
    assert "G4 P1.00" in res_data["data"]["gcode"]
    assert res_data["dialect_used"] == "grbl"
    assert res_data["machine_profile"]["name"] == "Test X-Carve"

def test_generate_with_tool_and_material_presets(client):
    payload = {
        "holes": [(10.0, 10.0), (20.0, 20.0)],
        "target_depth_z": -4.0,
        "tool_id": 1,
        "material_preset_id": 1,
    }
    response = client.post("/api/generate/drilling/straight-plunge", json=payload)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["success"] is True
    # DeWalt router clamps 12000 RPM preset to min speed 16000 RPM (Dial 1) with warning
    assert "M3 S16000" in res_data["data"]["gcode"]
    assert "DeWalt DWP611" in res_data["data"]["gcode"]
    assert "Set Speed Dial to #1" in res_data["data"]["gcode"]
    assert "F400.0" in res_data["data"]["gcode"]
    assert "Tool T1: 1/8in Drill Bit" in res_data["data"]["gcode"]
    assert any("below Dewalt 611 minimum speed" in w for w in res_data["data"]["warnings"])

def test_generate_validation_failure(client):
    # Missing coordinates
    payload = {
        "target_depth_z": -5.0,
    }
    response = client.post("/api/generate/drilling/straight-plunge", json=payload)
    assert response.status_code == 400
    assert "Validation error" in response.get_json()["error"]

def test_generate_with_machine_switching_and_bounds_warning(client):
    # Test X-Carve has work_area_x=750. Request with hole at X=800
    payload = {
        "x": 800.0,
        "y": 100.0,
        "target_depth_z": -5.0,
    }
    res = client.post("/api/generate/drilling/straight-plunge", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["data"]["warnings"]) > 0
    assert "exceeds work envelope max 750.00" in data["data"]["warnings"][0]

    # Switch to Shapeoko (id=2, work_area_x=838.0)
    client.post("/api/machines/2/activate")

    # Re-run same payload with Shapeoko active -> No warning because 800 < 838
    res_shapeoko = client.post("/api/generate/drilling/straight-plunge", json=payload)
    assert res_shapeoko.status_code == 200
    data_shapeoko = res_shapeoko.get_json()
    assert data_shapeoko["machine_profile"]["name"] == "Test Shapeoko"
    assert len(data_shapeoko["data"]["warnings"]) == 0

def test_generate_inches(client):
    payload = {
        "x": 1.0,
        "y": 2.0,
        "target_depth_z": -0.25,
        "units": "inch",
        "plunge_feed": 10.0,
    }
    response = client.post("/api/generate/drilling/straight-plunge", json=payload)
    assert response.status_code == 200
    gcode = response.get_json()["data"]["gcode"]
    assert "G20 G90 G94 G17" in gcode
    assert "G1 Z-0.250 F10.0" in gcode
