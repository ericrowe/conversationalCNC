def test_tool_crud(client):
    # Create tool
    new_tool = {
        "tool_number": 10,
        "name": "1/4in 90-Deg V-Groove Bit",
        "tool_type": "v-bit",
        "diameter": 6.35,
        "flute_length": 12.7,
        "overall_length": 45.0,
        "flute_count": 1,
        "notes": "Letter engraving",
    }
    res_create = client.post("/api/tools", json=new_tool)
    assert res_create.status_code == 201
    created = res_create.get_json()
    assert created["tool_number"] == 10
    tool_id = created["id"]

    # Get tool
    res_get = client.get(f"/api/tools/{tool_id}")
    assert res_get.status_code == 200
    assert res_get.get_json()["name"] == "1/4in 90-Deg V-Groove Bit"

    # Update tool
    res_update = client.put(f"/api/tools/{tool_id}", json={"name": "1/4in 90-Deg Chamfer Mill"})
    assert res_update.status_code == 200
    assert res_update.get_json()["name"] == "1/4in 90-Deg Chamfer Mill"

    # Delete tool
    res_delete = client.delete(f"/api/tools/{tool_id}")
    assert res_delete.status_code == 200

    # Verify 404
    res_404 = client.get(f"/api/tools/{tool_id}")
    assert res_404.status_code == 404

def test_duplicate_tool_number_rejected(client):
    dup = {
        "tool_number": 1,  # T1 already exists in conftest seed
        "name": "Another T1",
        "diameter": 3.175,
    }
    res = client.post("/api/tools", json=dup)
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]

def test_material_presets_crud(client):
    # Add preset for tool 1
    new_preset = {
        "material_name": "Delrin / Acetal",
        "spindle_speed": 15000,
        "feed_rate_xy": 1200.0,
        "plunge_rate_z": 450.0,
        "pass_depth": 2.0,
    }
    res_create = client.post("/api/materials/tool/1", json=new_preset)
    assert res_create.status_code == 201
    preset_id = res_create.get_json()["id"]

    # List presets for tool 1
    res_list = client.get("/api/materials?tool_id=1")
    assert res_list.status_code == 200
    presets = res_list.get_json()
    assert any(p["material_name"] == "Delrin / Acetal" for p in presets)

    # Delete preset
    res_del = client.delete(f"/api/materials/{preset_id}")
    assert res_del.status_code == 200
