def test_get_machines(client):
    response = client.get("/api/machines")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]["name"] == "Test X-Carve"
    assert data[0]["is_active"] is True

def test_get_active_machine(client):
    response = client.get("/api/machines/active")
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Test X-Carve"
    assert data["is_active"] is True

def test_activate_machine(client):
    # Activate Shapeoko (id=2)
    response = client.post("/api/machines/2/activate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == 2
    assert data["is_active"] is True

    # Verify X-Carve is now inactive
    res_list = client.get("/api/machines")
    machines = res_list.get_json()
    assert machines[0]["is_active"] is False
    assert machines[1]["is_active"] is True

def test_create_and_delete_machine(client):
    payload = {
        "name": "PrintNC Mill",
        "controller_dialect": "linuxcnc",
        "work_area_x": 1000.0,
        "work_area_y": 600.0,
        "work_area_z": 150.0,
        "max_feed_xy": 12000.0,
        "max_feed_z": 2000.0,
        "rapid_feed_rate": 8000.0,
        "min_spindle_rpm": 6000,
        "max_spindle_rpm": 24000,
        "spindle_dwell_seconds": 3.0,
        "z_probe_thickness": 20.0,
        "safe_z_retract": 15.0,
    }
    res_create = client.post("/api/machines", json=payload)
    assert res_create.status_code == 201
    created_id = res_create.get_json()["id"]

    # Delete
    res_del = client.delete(f"/api/machines/{created_id}")
    assert res_del.status_code == 200

def test_update_active_machine(client):
    # Get active X-Carve (id=1)
    res_active = client.get("/api/machines/active")
    assert res_active.status_code == 200
    machine = res_active.get_json()
    assert machine["id"] == 1

    # Update X-Carve dimensions and notes
    update_payload = {
        "name": "Upgraded X-Carve 1000mm",
        "work_area_x": 800.0,
        "work_area_y": 800.0,
        "work_area_z": 75.0,
        "safe_z_retract": 8.0,
        "z_probe_thickness": 15.2,
        "notes": "Upgraded Y-axis extrusions and direct Z probe",
    }
    res_update = client.put("/api/machines/1", json=update_payload)
    assert res_update.status_code == 200
    updated = res_update.get_json()
    assert updated["name"] == "Upgraded X-Carve 1000mm"
    assert updated["work_area_x"] == 800.0
    assert updated["safe_z_retract"] == 8.0
    assert updated["z_probe_thickness"] == 15.2
    assert updated["is_active"] is True
