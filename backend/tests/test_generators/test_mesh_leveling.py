"""
Unit tests for Workpiece Surface Mesh Leveling & Auto-Warping Generator.
"""
import pytest
import math
from app.generators.mesh_leveling import (
    generate_rectangular_probe_points,
    generate_circular_probe_points,
    generate_polygon_probe_points,
    delaunay_triangulation_2d,
    WorkpieceMeshMap,
    generate_mesh_probe_macro,
    parse_probe_log,
)
from app.generators.sequencer import generate_job_sequence


def test_generate_rectangular_probe_points():
    pts = generate_rectangular_probe_points(
        x_min=0.0,
        y_min=0.0,
        x_max=100.0,
        y_max=50.0,
        grid_x=5,
        grid_y=3,
        margin=5.0,
    )
    assert len(pts) == 15  # 5 * 3
    # With margin=5.0, X ranges from 5.0 to 95.0, Y from 5.0 to 45.0
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    assert min(xs) == 5.0
    assert max(xs) == 95.0
    assert min(ys) == 5.0
    assert max(ys) == 45.0
    assert all(p["active"] is True for p in pts)


def test_generate_circular_disc_and_donut_probe_points():
    # Circular disc
    disc_pts = generate_circular_probe_points(
        center_x=50.0,
        center_y=50.0,
        radius=40.0,
        inner_radius=0.0,
        grid_resolution=5,
        margin=2.0,
    )
    assert len(disc_pts) > 10
    # Every point must be within eff_outer_r (38.0mm) of center (50, 50)
    for p in disc_pts:
        dist = math.hypot(p["x"] - 50.0, p["y"] - 50.0)
        assert dist <= 38.01

    # Donut / Annulus with inner bore
    donut_pts = generate_circular_probe_points(
        center_x=0.0,
        center_y=0.0,
        radius=50.0,
        inner_radius=20.0,
        grid_resolution=5,
        margin=2.0,
    )
    # Points must be between (20 + 2 = 22mm) and (50 - 2 = 48mm)
    for p in donut_pts:
        dist = math.hypot(p["x"], p["y"])
        assert dist >= 21.99
        assert dist <= 48.01


def test_generate_polygon_probe_points():
    triangle_vertices = [(0.0, 0.0), (100.0, 0.0), (50.0, 80.0)]
    pts = generate_polygon_probe_points(vertices=triangle_vertices, grid_spacing=20.0)
    assert len(pts) > 3
    # Check that centroid (50, 26) is enclosed
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    assert min(xs) >= 0.0
    assert max(xs) <= 100.0
    assert min(ys) >= 0.0
    assert max(ys) <= 80.0


def test_delaunay_triangulation_2d():
    # Regular 3x3 grid
    pts_2d = [
        (0.0, 0.0), (50.0, 0.0), (100.0, 0.0),
        (0.0, 50.0), (50.0, 50.0), (100.0, 50.0),
        (0.0, 100.0), (50.0, 100.0), (100.0, 100.0),
    ]
    triangles = delaunay_triangulation_2d(pts_2d)
    assert len(triangles) >= 8  # 2 per grid cell
    for tri in triangles:
        assert len(tri) == 3
        assert all(0 <= idx < len(pts_2d) for idx in tri)


def test_workpiece_mesh_map_interpolation():
    # 4 corner points with a ramp slope in Z
    points = [
        {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0, "active": True},
        {"id": 1, "x": 100.0, "y": 0.0, "z": 1.0, "active": True},
        {"id": 2, "x": 0.0, "y": 100.0, "z": 2.0, "active": True},
        {"id": 3, "x": 100.0, "y": 100.0, "z": 3.0, "active": True},
    ]
    mesh = WorkpieceMeshMap(points, shape_type="rectangle")

    # Corner tests
    assert pytest.approx(mesh.interpolate_z(0.0, 0.0), 0.01) == 0.0
    assert pytest.approx(mesh.interpolate_z(100.0, 0.0), 0.01) == 1.0
    assert pytest.approx(mesh.interpolate_z(0.0, 100.0), 0.01) == 2.0
    assert pytest.approx(mesh.interpolate_z(100.0, 100.0), 0.01) == 3.0

    # Center point (50, 50) -> should interpolate to 1.5mm
    assert pytest.approx(mesh.interpolate_z(50.0, 50.0), 0.05) == 1.5


def test_workpiece_mesh_warp_gcode():
    # Simple tilted plane: Z = 0.5 at X=50, Y=50
    points = [
        {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0, "active": True},
        {"id": 1, "x": 100.0, "y": 0.0, "z": 0.0, "active": True},
        {"id": 2, "x": 0.0, "y": 100.0, "z": 0.0, "active": True},
        {"id": 3, "x": 100.0, "y": 100.0, "z": 0.0, "active": True},
        {"id": 4, "x": 50.0, "y": 50.0, "z": 0.5, "active": True},
    ]
    mesh = WorkpieceMeshMap(points)

    raw_gcode = """G0 Z5.000
G0 X0.000 Y50.000
G1 Z-1.000 F200.0
G1 X100.000 Y50.000 F800.0
G0 Z5.000
"""
    warped = mesh.warp_gcode(raw_gcode, max_segment_length=5.0)

    assert "WORKPIECE MESH LEVELING APPLIED" in warped
    # The linear cut passing through (50, 50) at nominal Z-1.0 should be warped to approx Z -0.5 (-1.0 + 0.5)
    assert "X50.000 Y50.000" in warped or "X50." in warped
    lines = warped.splitlines()
    # Should have subdivided the 100mm move into >= 20 segments
    assert len(lines) > 20


def test_generate_mesh_probe_macro():
    points = [
        {"id": 0, "x": 10.0, "y": 10.0, "active": True},
        {"id": 1, "x": 50.0, "y": 10.0, "active": False},  # Clamp excluded
        {"id": 2, "x": 90.0, "y": 10.0, "active": True},
    ]
    macro_res = generate_mesh_probe_macro(
        points=points,
        search_dist=15.0,
        fast_feed=120.0,
        slow_feed=20.0,
        safe_traverse_z=8.0,
    )
    gcode = macro_res["gcode"]
    assert macro_res["point_count"] == 2
    assert "G38.2 Z-15.000 F120.0" in gcode
    assert "G38.2 Z-3.000 F20.0" in gcode
    assert "X10.000 Y10.000" in gcode
    assert "X90.000 Y10.000" in gcode
    assert "X50.000 Y10.000" not in gcode  # Excluded point skipped


def test_parse_probe_log_grbl():
    log_text = """
ok
[PRB:10.000,10.000,-1.420:1]
ok
[PRB:90.000,10.000,-1.150:1]
ok
"""
    template = [
        {"id": 0, "x": 10.0, "y": 10.0, "z": 0.0, "active": True},
        {"id": 1, "x": 90.0, "y": 10.0, "z": 0.0, "active": True},
    ]
    mesh = parse_probe_log(log_text, points_template=template, plate_thickness=1.0)
    assert len(mesh.coords_3d) == 2
    # Z should be -1.420 - 1.0 = -2.420
    assert pytest.approx(mesh.coords_3d[0][2], 0.01) == -2.420
    assert pytest.approx(mesh.coords_3d[1][2], 0.01) == -2.150


def test_sequencer_auto_mesh_leveling():
    # Test that Job Builder sequencer integrates mesh leveling across operations
    points = [
        {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0, "active": True},
        {"id": 1, "x": 100.0, "y": 0.0, "z": 0.2, "active": True},
        {"id": 2, "x": 0.0, "y": 100.0, "z": 0.2, "active": True},
        {"id": 3, "x": 100.0, "y": 100.0, "z": 0.4, "active": True},
    ]
    mesh_data = {"shape_type": "rectangle", "points": points}

    operations = [
        {
            "op_name": "Test Plunge",
            "op_type": "drilling",
            "tool_number": 1,
            "tool_name": "Drill",
            "tool_diameter": 3.175,
            "spindle_speed": 12000,
            "params": {
                "holes": [(100.0, 100.0)],
                "target_depth_z": -5.0,
                "plunge_feed": 150.0,
            }
        }
    ]

    result = generate_job_sequence(
        job_name="Mesh Warped Test Job",
        operations=operations,
        apply_mesh_leveling=True,
        mesh_data=mesh_data,
    )

    assert result["mesh_leveling_applied"] is True
    gcode = result["gcode"]
    assert "Workpiece Surface Mesh Compensation: RECTANGLE" in gcode
    # Target depth -5.0 + 0.4 delta at (100, 100) -> Z-4.600
    assert "Z-4.600" in gcode
