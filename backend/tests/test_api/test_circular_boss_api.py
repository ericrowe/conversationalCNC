def test_generate_circular_boss_api_round_stock(client):
    payload = {
        "boss_center_x": 10.0,
        "boss_center_y": 10.0,
        "boss_diameter": 10.0,
        "stock_shape": "circle",
        "stock_diameter": 25.0,
        "target_depth_z": -15.0,
        "stepdown_z": 3.0,
        "stepover_percent": 50.0,
        "finish_allowance": 0.2,
        "tool_diameter": 6.35,
        "feed_rate_xy": 900.0,
        "plunge_feed": 250.0,
    }
    response = client.post("/api/generate/pocket/circular-boss", json=payload)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["success"] is True
    assert "Circular Boss" in res_data["data"]["gcode"]
    assert "Plunge in Open Air" in res_data["data"]["gcode"]
    assert "Wall Finishing Pass" in res_data["data"]["gcode"]
    assert res_data["data"]["bounds"]["min_z"] == -15.0


def test_generate_circular_boss_api_validation_error(client):
    # Stock smaller than boss
    payload = {
        "boss_diameter": 20.0,
        "stock_diameter": 15.0,
        "stock_shape": "circle",
        "target_depth_z": -5.0,
    }
    response = client.post("/api/generate/pocket/circular-boss", json=payload)
    assert response.status_code == 400
    res_data = response.get_json()
    assert "Generation error" in res_data["error"]
