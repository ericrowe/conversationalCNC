def test_api_generate_job_sequence(client):
    payload = {
        "job_name": "API Test Bracket",
        "operations": [
            {
                "op_name": "Surface Top",
                "op_type": "surfacing",
                "tool_number": 1,
                "tool_name": "Flycutter",
                "tool_diameter": 25.0,
                "spindle_speed": 14000,
                "params": {
                    "length_x": 50.0,
                    "width_y": 50.0,
                    "total_depth": 0.5,
                    "depth_per_pass": 0.5,
                    "stepover": 10.0,
                }
            },
            {
                "op_name": "Center Bore",
                "op_type": "circular_pocket",
                "tool_number": 2,
                "tool_name": "1/4 Endmill",
                "tool_diameter": 6.35,
                "spindle_speed": 16000,
                "params": {
                    "center_x": 25.0,
                    "center_y": 25.0,
                    "pocket_diameter": 20.0,
                    "target_depth": 3.0,
                    "depth_per_pass": 1.5,
                    "stepover": 2.5,
                }
            }
        ],
        "safe_z_retract": 5.0,
        "units": "mm",
        "dialect": "grbl"
    }

    res = client.post("/api/generate/job-sequence", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    gcode = data["data"]["gcode"]
    assert "Job: API Test Bracket" in gcode
    assert ">>> OP 1/2: SURFACE TOP" in gcode
    assert ">>> OP 2/2: CENTER BORE" in gcode
    assert data["data"]["operation_count"] == 2
