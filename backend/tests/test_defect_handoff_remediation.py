"""
Comprehensive Regression Test Suite for ConversationalCNC Defect Handoff v1.0 (CNC-001 through CNC-014).
"""
import math
from pathlib import Path
import pytest

from app import create_app
from app.config import TestingConfig
from app.models import db
from app.generators.base import BoundingBox, WorkEnvelope, strip_header_and_footer
from app.generators.contouring import generate_contour_profile
from app.generators import chamfering as chamfering_mod
from app.generators.sequencer import generate_job_sequence
from app.generators.drilling import generate_straight_plunge
from app.generators.circular_pocket import generate_circular_pocket
from app.generators.surfacing import generate_surfacing
from .gcode_validator import validate_gcode_program, strip_gcode_comments


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


# ==============================================================================
# CNC-001: Arc Cutter Compensation Applied to Emitted Geometry
# ==============================================================================
def test_cnc_001_arc_cutter_compensation_outside_inside_and_joins():
    """
    Closed CCW circle of nominal radius 10.000 mm, center (0,0), tool diameter 3.000 mm,
    zero finishing allowance, expressed as two 180-deg arcs:
      Start (10, 0) -> (-10, 0) with I=-10, J=0 (CCW)
      (-10, 0) -> (10, 0) with I=10, J=0 (CCW)
    For CCW loop:
      - right of path is OUTSIDE material -> tool-center radius = 11.500 mm
      - left of path is INSIDE material -> tool-center radius = 8.500 mm
    """
    ccw_circle_segments = [
        {"type": "arc", "x": -10.0, "y": 0.0, "i": -10.0, "j": 0.0, "cw": False},
        {"type": "arc", "x": 10.0, "y": 0.0, "i": 10.0, "j": 0.0, "cw": False},
    ]

    # 1. Outside profile on CCW loop (side='right' -> tool center radius 11.500 mm)
    res_out_ccw = generate_contour_profile(
        segments=ccw_circle_segments,
        start_point=(10.0, 0.0),
        is_closed=True,
        side="right",
        lead_in_type="direct",
        lead_in_radius=0.0,
        target_depth_z=-2.0,
        start_z=0.0,
        stepdown_z=2.0,
        finish_allowance=0.0,
        spring_pass=False,
        tool_diameter=3.0,
    )
    report_out_ccw = validate_gcode_program(res_out_ccw["gcode"], expected_clearance_z=5.0)
    assert report_out_ccw.valid, f"Validator errors: {report_out_ccw.errors}"
    assert len(report_out_ccw.arcs) == 2
    for arc in report_out_ccw.arcs:
        assert math.isclose(arc.r_start, 11.5, abs_tol=0.002)
        assert math.isclose(arc.r_end, 11.5, abs_tol=0.002)
        assert math.isclose(arc.center_xy[0], 0.0, abs_tol=0.002)
        assert math.isclose(arc.center_xy[1], 0.0, abs_tol=0.002)
    assert math.isclose(res_out_ccw["bounds"]["max_x"], 11.5, abs_tol=0.01)
    assert math.isclose(res_out_ccw["bounds"]["min_x"], -11.5, abs_tol=0.01)

    # 2. Reverse winding (CW circle) with side='left' (climb outside) -> also 11.500 mm
    cw_circle_segments = [
        {"type": "arc", "x": -10.0, "y": 0.0, "i": -10.0, "j": 0.0, "cw": True},
        {"type": "arc", "x": 10.0, "y": 0.0, "i": 10.0, "j": 0.0, "cw": True},
    ]
    res_out_cw = generate_contour_profile(
        segments=cw_circle_segments,
        start_point=(10.0, 0.0),
        is_closed=True,
        side="left",
        lead_in_type="direct",
        lead_in_radius=0.0,
        target_depth_z=-2.0,
        start_z=0.0,
        stepdown_z=2.0,
        finish_allowance=0.0,
        spring_pass=False,
        tool_diameter=3.0,
    )
    report_out_cw = validate_gcode_program(res_out_cw["gcode"], expected_clearance_z=5.0)
    assert report_out_cw.valid, f"Validator errors: {report_out_cw.errors}"
    for arc in report_out_cw.arcs:
        assert arc.motion == "G2"
        assert math.isclose(arc.r_start, 11.5, abs_tol=0.002)
        assert math.isclose(arc.r_end, 11.5, abs_tol=0.002)

    # 3. Inside profile (tool-center radius 8.500 mm)
    res_in_ccw = generate_contour_profile(
        segments=ccw_circle_segments,
        start_point=(10.0, 0.0),
        is_closed=True,
        side="left",
        lead_in_type="direct",
        lead_in_radius=0.0,
        target_depth_z=-2.0,
        start_z=0.0,
        stepdown_z=2.0,
        finish_allowance=0.0,
        spring_pass=False,
        tool_diameter=3.0,
    )
    report_in_ccw = validate_gcode_program(res_in_ccw["gcode"], expected_clearance_z=5.0)
    assert report_in_ccw.valid, f"Validator errors: {report_in_ccw.errors}"
    for arc in report_in_ccw.arcs:
        assert math.isclose(arc.r_start, 8.5, abs_tol=0.002)
        assert math.isclose(arc.r_end, 8.5, abs_tol=0.002)

    # 4. Tangent line-to-arc join continuity:
    # Line from (0, 0) -> (20, 0), then 90-deg CCW arc to (30, 10) with center (20, 10) (I=0, J=10)
    line_arc_segs = [
        {"type": "line", "x": 20.0, "y": 0.0},
        {"type": "arc", "x": 30.0, "y": 10.0, "i": 0.0, "j": 10.0, "cw": False},
    ]
    res_join = generate_contour_profile(
        segments=line_arc_segs,
        start_point=(0.0, 0.0),
        is_closed=False,
        side="right",
        lead_in_type="direct",
        lead_in_radius=0.0,
        target_depth_z=-1.0,
        stepdown_z=1.0,
        finish_allowance=0.0,
        spring_pass=False,
        tool_diameter=3.0,
    )
    report_join = validate_gcode_program(res_join["gcode"], expected_clearance_z=5.0)
    assert report_join.valid, f"Validator errors: {report_join.errors}"
    assert len(report_join.arcs) == 1
    assert math.isclose(report_join.arcs[0].r_start, 11.5, abs_tol=0.002)
    assert math.isclose(report_join.arcs[0].r_end, 11.5, abs_tol=0.002)

    # 5. Reject collapsed arc radius <= 0 (e.g. inside of R=2mm arc with D=6mm tool -> r_offset = -1mm)
    with pytest.raises(ValueError, match="radius"):
        generate_contour_profile(
            segments=[{"type": "arc", "x": -2.0, "y": 0.0, "i": -2.0, "j": 0.0, "cw": False}],
            start_point=(2.0, 0.0),
            is_closed=False,
            side="left",
            lead_in_type="direct",
            lead_in_radius=0.0,
            tool_diameter=6.0,
            finish_allowance=0.0,
            spring_pass=False,
        )


# ==============================================================================
# CNC-002 & CNC-003: Tangential Lead-In and Lead-Out Circular Geometry
# ==============================================================================
@pytest.mark.parametrize(
    "dir_vec,side",
    [
        ((10.0, 0.0), "left"),
        ((10.0, 0.0), "right"),
        ((-10.0, 0.0), "left"),
        ((-10.0, 0.0), "right"),
        ((0.0, 10.0), "left"),
        ((0.0, 10.0), "right"),
        ((0.0, -10.0), "left"),
        ((0.0, -10.0), "right"),
    ],
)
def test_cnc_002_and_003_tangential_lead_in_and_out_arcs_all_cardinals(dir_vec, side):
    dx, dy = dir_vec
    res = generate_contour_profile(
        segments=[{"type": "line", "x": dx, "y": dy}],
        start_point=(0.0, 0.0),
        is_closed=False,
        side=side,
        lead_in_type="tangential_arc",
        lead_in_radius=5.0,
        target_depth_z=-1.0,
        stepdown_z=1.0,
        finish_allowance=0.0,
        spring_pass=False,
        tool_diameter=3.0,
    )
    report = validate_gcode_program(res["gcode"], expected_clearance_z=5.0, arc_tol=0.002)
    assert report.valid, f"Invalid arc geometry for dir={dir_vec}, side={side}: {report.errors}"
    # Should have 1 lead-in arc and 1 lead-out arc
    assert len(report.arcs) == 2
    lead_in_arc, lead_out_arc = report.arcs
    assert abs(lead_in_arc.r_start - 5.0) <= 0.002
    assert abs(lead_in_arc.r_end - 5.0) <= 0.002
    assert abs(lead_in_arc.r_start - lead_in_arc.r_end) <= 0.001

    assert abs(lead_out_arc.r_start - 5.0) <= 0.002
    assert abs(lead_out_arc.r_end - 5.0) <= 0.002
    assert abs(lead_out_arc.r_start - lead_out_arc.r_end) <= 0.001

    # Sweep sense: left side offset curves left (G3), right side offset curves right (G2)
    expected_g = "G3" if side == "left" else "G2"
    assert lead_in_arc.motion == expected_g
    assert lead_out_arc.motion == expected_g


# ==============================================================================
# CNC-004: Intermediate M2 / M30 Stripped Even With Inline Comments
# ==============================================================================
def test_cnc_004_intermediate_m2_m30_and_park_stripped_in_sequencer():
    snippet = "\n".join([
        "G21 G90 G17",
        "G1 X1.000 F100",
        "M5 (Spindle Stop)",
        "G0 X0.000 Y0.000 (Park)",
        "M2 (Program End)",
    ])
    stripped = strip_header_and_footer(snippet)
    for line in stripped:
        code_only = strip_gcode_comments(line).upper()
        assert code_only not in ("M2", "M02", "M30", "M5")
        assert "(PARK)" not in line.upper()

    # Sequence two real operations
    job = generate_job_sequence(
        job_name="Two Op Test",
        operations=[
            {
                "op_name": "Drill 1",
                "op_type": "drilling",
                "tool_number": 1,
                "params": {"holes": [(5.0, 5.0)], "target_depth_z": -2.0},
            },
            {
                "op_name": "Pocket 2",
                "op_type": "circular_pocket",
                "tool_number": 1,
                "params": {"pockets": [(20.0, 20.0)], "pocket_diameter": 12.0, "target_depth_z": -2.0, "tool_diameter": 3.175},
            },
        ],
    )
    report = validate_gcode_program(job["gcode"])
    assert report.valid, f"Sequenced job failed validation: {report.errors}"
    assert len(report.termination_lines) == 1
    assert len(report.moves_after_termination) == 0


# ==============================================================================
# CNC-005: Generation Failure Fails Atomically (Never Exported as Partial Job)
# ==============================================================================
def test_cnc_005_sequencer_atomic_failure_on_bad_sub_operation_and_api_400(client):
    # 1. Unknown operation type must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        generate_job_sequence(
            job_name="Broken Job",
            operations=[
                {"op_name": "Good Drill", "op_type": "drilling", "params": {"holes": [(0.0, 0.0)], "target_depth_z": -2.0}},
                {"op_name": "Bad Laser", "op_type": "nonexistent_laser_op", "params": {}},
            ],
        )
    assert "Bad Laser" in str(exc_info.value) or "nonexistent_laser_op" in str(exc_info.value)

    # 2. Invalid parameter inside sub-operation must raise ValueError
    with pytest.raises(ValueError):
        generate_job_sequence(
            job_name="Invalid Param Job",
            operations=[
                {"op_name": "Good Drill", "op_type": "drilling", "params": {"holes": [(0.0, 0.0)], "target_depth_z": -2.0}},
                {"op_name": "Bad Pocket", "op_type": "circular_pocket", "params": {"diameter": 2.0, "tool_diameter": 6.0, "target_depth_z": -2.0}},
            ],
        )

    # 3. API endpoint returns HTTP 400 with structured error and no runnable gcode
    res = client.post(
        "/api/generate/job-sequence",
        json={
            "job_name": "API Broken Job",
            "operations": [
                {"op_name": "Op1", "op_type": "drilling", "params": {"holes": [[0, 0]], "target_depth_z": -2.0}},
                {"op_name": "Op2", "op_type": "unknown_op", "params": {}},
            ],
        },
    )
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body
    assert "gcode" not in body.get("data", {})


# ==============================================================================
# CNC-006: Depth Sign and Finish Allowance Edge Cases
# ==============================================================================
def test_cnc_006_contour_depth_sign_and_finish_allowance_validation():
    segs = [{"type": "line", "x": 10.0, "y": 0.0}]

    # Reject target_depth_z >= start_z (upward / zero depth cut)
    with pytest.raises(ValueError, match="target_depth_z"):
        generate_contour_profile(
            segments=segs,
            start_point=(0.0, 0.0),
            is_closed=False,
            start_z=0.0,
            target_depth_z=2.5,
        )

    with pytest.raises(ValueError, match="target_depth_z"):
        generate_contour_profile(
            segments=segs,
            start_point=(0.0, 0.0),
            is_closed=False,
            start_z=-1.0,
            target_depth_z=-0.5,
        )

    # Reject finish_allowance > 0 when side == 'center' (material side ambiguous)
    with pytest.raises(ValueError, match="finish_allowance"):
        generate_contour_profile(
            segments=segs,
            start_point=(0.0, 0.0),
            is_closed=False,
            side="center",
            finish_allowance=0.2,
        )

    # Valid multi-pass from start_z = -1.0 to target_depth_z = -3.0 at stepdown = 1.0
    res = generate_contour_profile(
        segments=segs,
        start_point=(0.0, 0.0),
        is_closed=False,
        side="left",
        lead_in_type="direct",
        lead_in_radius=0.0,
        start_z=-1.0,
        target_depth_z=-3.0,
        stepdown_z=1.0,
        finish_allowance=0.25,
        spring_pass=False,
        tool_diameter=4.0,
    )
    report = validate_gcode_program(res["gcode"])
    assert report.valid
    assert math.isclose(report.bounds["min_z"], -3.0, abs_tol=0.001)


# ==============================================================================
# CNC-007: Work-Coordinate Envelope vs Machine Limits & Z Validation
# ==============================================================================
def test_cnc_007_work_envelope_wcs_vs_machine_limits_and_z_validation():
    env = WorkEnvelope(work_area_x=750.0, work_area_y=750.0, work_area_z=100.0)

    # 1. Legal local negative WCS move (e.g. centered around G54 X0 Y0) within 750x750x100 span
    local_bounds = BoundingBox(min_x=-5.0, max_x=5.0, min_y=-5.0, max_y=5.0, min_z=-10.0, max_z=5.0)
    violations = env.validate_bounds(local_bounds)
    assert violations == []

    eval_no_wcs = env.evaluate_envelope(local_bounds)
    assert eval_no_wcs["machine_limits_status"] == "unavailable"

    # 2. Excessive Z span (> 100 mm) must be flagged
    deep_z_bounds = BoundingBox(min_x=0.0, max_x=10.0, min_y=0.0, max_y=10.0, min_z=-95.0, max_z=15.0)
    z_violations = env.validate_bounds(deep_z_bounds)
    assert any("Z" in v for v in z_violations)

    # 3. With explicit WCS offset (e.g. fixture at machine X=100, Y=100), X=700 exceeds 750 machine limit (100+700=800 > 750)
    env_with_wcs = WorkEnvelope(
        work_area_x=750.0,
        work_area_y=750.0,
        work_area_z=100.0,
        wcs_origin_x=100.0,
        wcs_origin_y=100.0,
        wcs_origin_z=-20.0,
    )
    over_bounds = BoundingBox(min_x=0.0, max_x=700.0, min_y=0.0, max_y=50.0, min_z=-5.0, max_z=5.0)
    wcs_violations = env_with_wcs.validate_bounds(over_bounds)
    assert any("X" in v and "750" in v for v in wcs_violations)


# ==============================================================================
# CNC-008: First-Class Circular Chamfer Generator (20mm Brass Trumpet Button)
# ==============================================================================
def test_cnc_008_circular_chamfer_20mm_trumpet_button_outside_and_inside(client):
    assert hasattr(chamfering_mod, "generate_circular_chamfer"), "generate_circular_chamfer must be implemented"
    generate_circular_chamfer = chamfering_mod.generate_circular_chamfer

    # 20mm OD trumpet finger button, 1.0mm chamfer, 90-deg V-cutter, tip_dia=0.2mm, tip_offset=0.5mm
    # Analytic expectation:
    #   tan(45) = 1.0
    #   depth_z = -(1.0 / 1.0 + 0.5) = -1.500 mm
    #   radial_offset = 0.2/2 + 0.5*1.0 = 0.600 mm
    #   Outside boss path radius = 10.0 + 0.6 = 10.600 mm
    #   Inside bore path radius = 10.0 - 0.6 = 9.400 mm
    prog_out = generate_circular_chamfer(
        center_x=0.0,
        center_y=0.0,
        diameter=20.0,
        chamfer_width=1.0,
        feature_type="outside",
        cut_direction="cw",
        vbit_angle_deg=90.0,
        tip_diameter=0.2,
        tip_offset=0.5,
        lead_in_radius=0.0,
    )
    rep_out = validate_gcode_program(prog_out.gcode, expected_clearance_z=5.0)
    assert rep_out.valid, f"Outer circular chamfer invalid: {rep_out.errors}"
    assert len(rep_out.arcs) == 2
    for arc in rep_out.arcs:
        assert arc.motion == "G2"
        assert math.isclose(arc.r_start, 10.6, abs_tol=0.002)
        assert math.isclose(arc.r_end, 10.6, abs_tol=0.002)
    assert math.isclose(rep_out.bounds["min_z"], -1.5, abs_tol=0.002)

    prog_in = generate_circular_chamfer(
        center_x=0.0,
        center_y=0.0,
        diameter=20.0,
        chamfer_width=1.0,
        feature_type="inside",
        cut_direction="ccw",
        vbit_angle_deg=90.0,
        tip_diameter=0.2,
        tip_offset=0.5,
        lead_in_radius=0.0,
    )
    rep_in = validate_gcode_program(prog_in.gcode, expected_clearance_z=5.0)
    assert rep_in.valid, f"Inner circular chamfer invalid: {rep_in.errors}"
    assert len(rep_in.arcs) == 2
    for arc in rep_in.arcs:
        assert arc.motion == "G3"
        assert math.isclose(arc.r_start, 9.4, abs_tol=0.002)
        assert math.isclose(arc.r_end, 9.4, abs_tol=0.002)

    # Reject impossible inner bore smaller than radial offset
    with pytest.raises(ValueError):
        generate_circular_chamfer(
            center_x=0.0,
            center_y=0.0,
            diameter=1.0,  # radius 0.5 < radial_offset 0.6
            chamfer_width=1.0,
            feature_type="inside",
            vbit_angle_deg=90.0,
            tip_diameter=0.2,
            tip_offset=0.5,
        )

    # Verify REST API endpoint POST /api/generate/chamfering/circular
    resp = client.post(
        "/api/generate/chamfering/circular",
        json={
            "center_x": 0.0,
            "center_y": 0.0,
            "diameter": 20.0,
            "chamfer_width": 1.0,
            "feature_type": "outside",
            "cut_direction": "cw",
            "vbit_angle_deg": 90.0,
            "tip_diameter": 0.2,
            "tip_offset": 0.5,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert "G2" in data["gcode"]


# ==============================================================================
# CNC-009: Reject Missing Geometry & Invalid Contour Inputs
# ==============================================================================
def test_cnc_009_reject_missing_geometry_and_invalid_contour_inputs(client):
    # 1. None or empty segments must raise ValueError (never substitute a 40x30 rectangle)
    with pytest.raises(ValueError, match="segments"):
        generate_contour_profile(segments=None)

    with pytest.raises(ValueError, match="segments"):
        generate_contour_profile(segments=[])

    # 2. Zero or negative tool diameter must raise ValueError
    with pytest.raises(ValueError, match="tool_diameter"):
        generate_contour_profile(
            segments=[{"type": "line", "x": 10.0, "y": 0.0}],
            tool_diameter=0.0,
        )

    # 3. Inconsistent arc center (start radius != end radius) must raise ValueError
    with pytest.raises(ValueError, match="arc"):
        generate_contour_profile(
            segments=[{"type": "arc", "x": 10.0, "y": 10.0, "i": 2.0, "j": 0.0, "cw": False}],
            start_point=(0.0, 0.0),
            is_closed=False,
        )

    # 4. API must also reject empty segments with HTTP 400
    res = client.post("/api/generate/milling/contour", json={"segments": []})
    assert res.status_code == 400


# ==============================================================================
# CNC-010: Tool-Order Optimization Preserves Machining Dependencies
# ==============================================================================
def test_cnc_010_tool_order_optimization_preserves_machining_dependencies():
    # Op 1 surfaces stock with T2; Op 2 profiles a feature with T1 that relies on surfacing
    res = generate_job_sequence(
        job_name="Dependency Safe Job",
        optimize_tool_order=True,
        operations=[
            {
                "op_name": "Surface Stock",
                "op_type": "surfacing",
                "tool_number": 2,
                "tool_diameter": 25.4,
                "params": {"length_x": 50.0, "width_y": 50.0, "total_depth_z": -0.5, "stepdown_z": 0.5},
            },
            {
                "op_name": "Profile Button",
                "op_type": "circular_pocket",
                "tool_number": 1,
                "tool_diameter": 3.175,
                "params": {"pockets": [(25.0, 25.0)], "pocket_diameter": 20.0, "target_depth_z": -2.0},
            },
        ],
    )
    gcode = res["gcode"]
    idx_surface = gcode.find("SURFACE STOCK")
    idx_profile = gcode.find("PROFILE BUTTON")
    assert idx_surface != -1 and idx_profile != -1
    assert idx_surface < idx_profile, "Surfacing (Op 1, T2) must NOT be reordered after Profile Button (Op 2, T1)"


# ==============================================================================
# CNC-011: Invalid Surface Mesh Raises Fatal Error When Mesh Leveling Requested
# ==============================================================================
def test_cnc_011_invalid_mesh_raises_error_when_mesh_leveling_requested():
    ops = [
        {"op_name": "Drill", "op_type": "drilling", "params": {"holes": [(5.0, 5.0)], "target_depth_z": -2.0}}
    ]
    # 1. Missing mesh_data when apply_mesh_leveling=True
    with pytest.raises(ValueError, match="[Mm]esh"):
        generate_job_sequence(job_name="Mesh Job", operations=ops, apply_mesh_leveling=True, mesh_data=None)

    # 2. Insufficient points (< 3) when apply_mesh_leveling=True
    with pytest.raises(ValueError):
        generate_job_sequence(
            job_name="Mesh Job",
            operations=ops,
            apply_mesh_leveling=True,
            mesh_data={"points": [(0.0, 0.0, 0.0), (10.0, 0.0, 0.1)]},
        )


# ==============================================================================
# CNC-012: GRBL Manual-Router Spindle and Tool-Change Safety
# ==============================================================================
def test_cnc_012_manual_router_tool_change_retract_order_and_pause_safety():
    res = generate_job_sequence(
        job_name="Two Tool Manual Router Job",
        spindle_type="router",
        router_model="dewalt_611",
        safe_z_retract=8.0,
        operations=[
            {
                "op_name": "Op1 Rough",
                "op_type": "drilling",
                "tool_number": 1,
                "tool_name": "1/8 Endmill",
                "params": {"holes": [(5.0, 5.0)], "target_depth_z": -2.0},
            },
            {
                "op_name": "Op2 Chamfer",
                "op_type": "drilling",
                "tool_number": 2,
                "tool_name": "90deg V-Bit",
                "params": {"holes": [(5.0, 5.0)], "target_depth_z": -1.0},
            },
        ],
    )
    lines = res["gcode"].splitlines()
    # Find Op2 banner
    op2_idx = next(i for i, l in enumerate(lines) if "OP 2/2" in l)
    tool_change_window = "\n".join(lines[op2_idx : op2_idx + 20])
    # 1. Safe Z retract must appear BEFORE spindle stop M5 during tool change
    pos_retract = tool_change_window.find("G0 Z8.000")
    pos_m5 = tool_change_window.find("M5")
    assert pos_retract != -1 and pos_m5 != -1
    assert pos_retract < pos_m5, f"Z retract must precede M5 during tool change:\n{tool_change_window}"
    # 2. Manual router tool change must include M0 pause and Z re-zero instruction
    assert "M0" in tool_change_window


# ==============================================================================
# CNC-013 & CNC-014: Independent Validator Golden Suite & README Consistency
# ==============================================================================
def test_cnc_013_independent_validator_golden_suite_across_generators():
    p_drill = generate_straight_plunge(holes=[(0.0, 0.0), (10.0, 10.0)], target_depth_z=-3.0, retract_z=5.0)
    assert validate_gcode_program(p_drill.gcode, expected_clearance_z=5.0).valid

    p_pocket = generate_circular_pocket(pockets=[(0.0, 0.0)], pocket_diameter=16.0, target_depth_z=-3.0, tool_diameter=3.175, retract_z=5.0)
    assert validate_gcode_program(p_pocket.gcode, expected_clearance_z=5.0).valid

    p_surf = generate_surfacing(length_x=40.0, width_y=40.0, total_depth_z=-1.0, stepdown_z=0.5, tool_diameter=12.7, retract_z=5.0)
    assert validate_gcode_program(p_surf.gcode, expected_clearance_z=5.0).valid


def test_cnc_014_readme_commissioning_and_test_consistency():
    readme_path = Path(__file__).resolve().parents[2] / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    assert "Spindle UNPLUGGED" in text
    assert "MACHINE_INTEGRATION_TEST_PLAN.md" in text
    # Should not have conflicting stale 150 vs 174 test claims
    assert "150 automated pytest" not in text
    assert "all 150 tests" not in text
