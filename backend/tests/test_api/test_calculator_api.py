def test_get_materials_catalog(client):
    res = client.get("/api/calculator/materials-catalog")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "softwood_pine" in data["materials"]
    assert "aluminum_6061" in data["materials"]


def test_api_calculate_feeds_speeds(client):
    payload = {
        "material_key": "aluminum_6061",
        "tool_diameter_mm": 6.35,
        "num_flutes": 2,
        "stepover_mm": 2.0,
        "stepdown_mm": 1.5,
    }
    res = client.post("/api/calculator/feeds-speeds", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    calc = data["data"]
    assert calc["recommended_rpm"] > 5000
    assert calc["recommended_feed_xy"] > 100
    assert calc["mrr_cm3_min"] > 0
