"""
API integration tests for Workpiece Surface Mesh Leveling & Auto-Warping.
"""
import json
import pytest
from app import create_app
from app.config import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        yield client


def test_api_generate_points_rectangle(client):
    res = client.post(
        "/api/mesh/generate-points",
        json={
            "shape_type": "rectangle",
            "x_min": 0,
            "y_min": 0,
            "x_max": 100,
            "y_max": 80,
            "grid_x": 4,
            "grid_y": 3,
            "margin": 2.0,
        },
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["shape_type"] == "rectangle"
    assert data["point_count"] == 12
    assert len(data["points"]) == 12


def test_api_generate_points_circle_and_donut(client):
    # Disc
    res_disc = client.post(
        "/api/mesh/generate-points",
        json={
            "shape_type": "circle",
            "center_x": 50,
            "center_y": 50,
            "radius": 40,
            "grid_resolution": 4,
            "margin": 2.0,
        },
    )
    assert res_disc.status_code == 200
    disc_data = res_disc.get_json()["data"]
    assert disc_data["point_count"] > 5

    # Donut
    res_donut = client.post(
        "/api/mesh/generate-points",
        json={
            "shape_type": "donut",
            "center_x": 50,
            "center_y": 50,
            "radius": 50,
            "inner_radius": 25,
            "grid_resolution": 4,
            "margin": 2.0,
        },
    )
    assert res_donut.status_code == 200
    donut_data = res_donut.get_json()["data"]
    assert donut_data["point_count"] > 0


def test_api_probe_macro(client):
    pts = [
        {"id": 0, "x": 0.0, "y": 0.0, "active": True},
        {"id": 1, "x": 50.0, "y": 0.0, "active": False},
        {"id": 2, "x": 100.0, "y": 0.0, "active": True},
    ]
    res = client.post(
        "/api/mesh/probe-macro",
        json={
            "points": pts,
            "shape_type": "rectangle",
            "search_dist": 15.0,
            "fast_feed": 100.0,
            "slow_feed": 20.0,
            "safe_traverse_z": 5.0,
        },
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["point_count"] == 2
    assert "G38.2" in data["gcode"]


def test_api_parse_log(client):
    log = "[PRB:25.000,25.000,-0.450:1]\n[PRB:75.000,75.000,-0.200:1]"
    res = client.post(
        "/api/mesh/parse-log",
        json={
            "log_text": log,
            "plate_thickness": 0.0,
        },
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["active_point_count"] == 2
    assert data["z_min"] == -0.450
    assert data["z_max"] == -0.200


def test_api_warp_gcode(client):
    pts = [
        {"id": 0, "x": 0.0, "y": 0.0, "z": 0.1, "active": True},
        {"id": 1, "x": 50.0, "y": 0.0, "z": 0.2, "active": True},
        {"id": 2, "x": 0.0, "y": 50.0, "z": 0.3, "active": True},
        {"id": 3, "x": 50.0, "y": 50.0, "z": 0.4, "active": True},
    ]
    gcode = "G0 X0.0 Y0.0\nG1 Z-1.0 F200\nG1 X50.0 Y50.0 F800\nG0 Z5.0"
    res = client.post(
        "/api/mesh/warp-gcode",
        json={
            "gcode_text": gcode,
            "points": pts,
            "shape_type": "rectangle",
            "max_segment_length": 5.0,
        },
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "WORKPIECE MESH LEVELING APPLIED" in data["gcode"]
    assert data["active_points"] == 4
