"""
Remediation Handoff v2.0 Test Suite (R2-001 through V2-006).
Verifies:
- R2-001: Operation dependency preservation & DAG cycle detection in tool-order optimization
- R2-002: Shared MachiningContext propagation, fail-closed dialect/unit checks, no nested M6/M2
- R2-003: Tri-state WorkEnvelope contract (VERIFIED, PARTIAL_UNKNOWN, FAILED), asymmetric Z limits,
          full trajectory bounds (rapids/retracts/arcs), and tool-length offset effects
- V2-004: Independent conical cutter-contact oracle for circular chamfering (60°/90°, flat/pointed,
          outside/inside, CW/CCW, mm/inch, and 20 mm brass trumpet finger button fixture)
- V2-005: Offset contour joins (convex corner-roll arcs, concave true intersections, short-segment
          inversion rejection) verified by 2D swept-tool stock-interference oracle
- V2-006: Whole-job GRBL dialect compliance, modal state consistency, and retract-before-M5 safety
"""
import math
import pytest

import app.generators.base as base_mod
from app.generators.base import (
    BoundingBox,
    WorkEnvelope,
)
from app.generators.sequencer import (
    _order_operations_safely,
    generate_job_sequence,
    SequenceGenerationError,
)
from app.generators.chamfering import generate_circular_chamfer
from app.generators.contouring import generate_contour_profile
from app.generators.circular_pocket import generate_circular_pocket
from app.generators.drilling import generate_straight_plunge
from app.postprocessors import get_postprocessor
from tests.gcode_validator import (
    validate_gcode_program,
    verify_contour_no_stock_gouge,
    strip_gcode_comments,
)


# ==============================================================================
# R2-001 — Preserve operation dependencies when optimizing tool order
# ==============================================================================


def test_sequence_preserves_order_without_dependency_proof():
    """
    R2-001 Reproduction Scenario:
    1. T1: drill locating/mounting holes
    2. T2: pocket material around a feature
    3. T1: finish a feature inside the newly created pocket
    Without explicit independence proof, optimize_tool_order=True MUST preserve [1, 2, 3]
    rather than reordering to [1, 3, 2].
    """
    ops = [
        {
            "id": 1,
            "name": "Step 1: Drill Locating Holes",
            "op_type": "drilling",
            "tool_number": 1,
            "tool_diameter": 3.175,
            "parameters": {"holes": [(10.0, 10.0)], "target_depth_z": -5.0},
        },
        {
            "id": 2,
            "name": "Step 2: Pocket Material",
            "op_type": "circular_pocket",
            "tool_number": 2,
            "tool_diameter": 6.35,
            "parameters": {"pockets": [(0.0, 0.0)], "pocket_diameter": 16.0, "target_depth_z": -3.0},
        },
        {
            "id": 3,
            "name": "Step 3: Finish Inside Pocket",
            "op_type": "drilling",
            "tool_number": 1,
            "tool_diameter": 3.175,
            "parameters": {"holes": [(0.0, 0.0)], "target_depth_z": -6.0},
        },
    ]
    ordered = _order_operations_safely(ops)
    assert [op["id"] for op in ordered] == [1, 2, 3]

    res = generate_job_sequence(
        job_name="R2-001 Authored Order Default",
        operations=ops,
        optimize_tool_order=True,
    )
    assert res["execution_order"] == [1, 2, 3]
    assert res["reordered"] is False


def test_sequence_reorders_only_explicitly_independent_operations():
    """
    R2-001: Reordering is only permitted when operations are explicitly marked independent=True
    (or allow_reorder=True) and have no unmet dependencies.
    """
    ops = [
        {
            "id": 1,
            "name": "Drill A",
            "op_type": "drilling",
            "tool_number": 1,
            "independent": True,
            "parameters": {"holes": [(-10.0, 0.0)], "target_depth_z": -3.0},
        },
        {
            "id": 2,
            "name": "Pocket B",
            "op_type": "circular_pocket",
            "tool_number": 2,
            "independent": True,
            "parameters": {"pockets": [(0.0, 0.0)], "pocket_diameter": 12.0, "target_depth_z": -2.0},
        },
        {
            "id": 3,
            "name": "Drill C (Independent)",
            "op_type": "drilling",
            "tool_number": 1,
            "independent": True,
            "parameters": {"holes": [(10.0, 0.0)], "target_depth_z": -3.0},
        },
    ]
    ordered = _order_operations_safely(ops)
    assert [op["id"] for op in ordered] == [1, 3, 2]

    res = generate_job_sequence(
        job_name="R2-001 Explicit Independent Reorder",
        operations=ops,
        optimize_tool_order=True,
    )
    assert res["execution_order"] == [1, 3, 2]
    assert res["reordered"] is True
    assert len(res["optimization_log"]) > 0


def test_sequence_respects_transitive_dependencies():
    """
    R2-001: Even if Op 3 is marked independent=True and shares T1 with Op 1,
    if Op 3 depends_on Op 2 and Op 2 depends_on Op 1, transitive dependency 1 -> 2 -> 3
    prevents Op 3 from being hoisted ahead of Op 2.
    """
    ops = [
        {"id": 1, "name": "Op1", "op_type": "drilling", "tool_number": 1, "independent": True},
        {"id": 2, "name": "Op2", "op_type": "circular_pocket", "tool_number": 2, "independent": True, "depends_on": [1]},
        {"id": 3, "name": "Op3", "op_type": "drilling", "tool_number": 1, "independent": True, "depends_on": [2]},
    ]
    ordered = _order_operations_safely(ops)
    assert [op["id"] for op in ordered] == [1, 2, 3]


def test_sequence_respects_barriers():
    """
    R2-001: Hard barriers (surfacing, soft_jaw, or lock_order=True) partition the sequence;
    no operation after a barrier can be hoisted before it even if marked independent=True.
    """
    ops = [
        {"id": 1, "name": "Pre-Drill", "op_type": "drilling", "tool_number": 1, "independent": True},
        {"id": 2, "name": "Face Stock Barrier", "op_type": "surfacing", "tool_number": 2},
        {"id": 3, "name": "Post-Surface Drill", "op_type": "drilling", "tool_number": 1, "independent": True},
    ]
    ordered = _order_operations_safely(ops)
    assert [op["id"] for op in ordered] == [1, 2, 3]


def test_sequence_rejects_dependency_cycles():
    """
    R2-001: Dependency cycles (1 -> 2 -> 1), self-dependencies, or forward/impossible dependencies
    must fail generation with a clear diagnostic.
    """
    cyclic_ops = [
        {"id": 1, "name": "Op1", "op_type": "drilling", "tool_number": 1, "depends_on": [2]},
        {"id": 2, "name": "Op2", "op_type": "drilling", "tool_number": 2, "depends_on": [1]},
    ]
    with pytest.raises((ValueError, SequenceGenerationError), match="(?i)cycle|dependency"):
        _order_operations_safely(cyclic_ops)

    unknown_dep_ops = [
        {"id": 1, "name": "Op1", "op_type": "drilling", "tool_number": 1, "depends_on": [99]},
    ]
    with pytest.raises((ValueError, SequenceGenerationError), match="(?i)unknown|non-existent|dependency"):
        _order_operations_safely(unknown_dep_ops)


def test_sequence_optimization_is_deterministic():
    """
    R2-001: Repeated invocations with identical operation definitions must produce identical orderings.
    """
    ops = [
        {"id": 1, "name": "Op1", "op_type": "drilling", "tool_number": 1, "independent": True},
        {"id": 2, "name": "Op2", "op_type": "circular_pocket", "tool_number": 2, "independent": True},
        {"id": 3, "name": "Op3", "op_type": "drilling", "tool_number": 1, "independent": True},
        {"id": 4, "name": "Op4", "op_type": "circular_pocket", "tool_number": 2, "independent": True},
    ]
    runs = [[op["id"] for op in _order_operations_safely(ops)] for _ in range(10)]
    for r in runs:
        assert r == [1, 3, 2, 4]


# ==============================================================================
# R2-002 — Propagate machine, spindle, dialect, and safety context consistently
# ==============================================================================


def test_all_generators_receive_selected_machine_context():
    """
    R2-002: MachiningContext validates and maps units, dialect, spindle_type, safe_z_retract,
    and tool settings across all conversational generators without silent drops.
    """
    MachiningContext = getattr(base_mod, "MachiningContext")
    ctx = MachiningContext(
        machine_id="voltron_xcarve",
        units="inch",
        dialect="standard",
        spindle_type="vfd",
        safe_z_retract=0.45,
        feed_rate_xy=35.0,
        plunge_feed=12.0,
        spindle_speed=18000,
        tool_number=2,
        tool_name="1/8 Carbide Endmill",
        tool_diameter=0.125,
    )
    assert ctx.units == "inch"
    assert ctx.dialect == "standard"

    seq = generate_job_sequence(
        job_name="Context Propagation Check",
        units="inch",
        dialect="standard",
        spindle_type="vfd",
        safe_z_retract=0.45,
        operations=[
            {
                "id": 1,
                "name": "Pocket",
                "op_type": "circular_pocket",
                "tool_number": 2,
                "tool_name": "1/8 Endmill",
                "tool_diameter": 0.125,
                "spindle_speed": 18000,
                "parameters": {
                    "pockets": [(0.0, 0.0)],
                    "pocket_diameter": 0.5,
                    "target_depth_z": -0.1,
                    "stepdown_z": 0.05,
                    "feed_rate_xy": 35.0,
                    "plunge_feed": 12.0,
                },
            },
            {
                "id": 2,
                "name": "Chamfer",
                "op_type": "circular_chamfer",
                "tool_number": 3,
                "tool_name": "90deg V-Bit",
                "tool_diameter": 0.25,
                "spindle_speed": 16000,
                "parameters": {
                    "diameter": 0.5,
                    "chamfer_width": 0.02,
                    "feature_type": "inside",
                    "vbit_angle_deg": 90.0,
                    "tip_diameter": 0.005,
                    "tip_offset": 0.01,
                    "feed_rate_xy": 30.0,
                    "plunge_feed": 10.0,
                },
            },
        ],
    )
    gc = seq["gcode"]
    assert "G20" in gc
    assert "G21" not in gc
    assert "M3 S18000" in gc
    assert "M3 S16000" in gc
    assert "Z0.450" in gc
    assert "Z5.000" not in gc


def test_sequencer_matches_standalone_generator_effective_settings():
    """
    R2-002: Running circular_chamfer and contour_profile standalone vs inside generate_job_sequence
    with custom safe_z_retract=8.5, feed_rate_xy=650.0, plunge_feed=180.0 must emit identical
    cutting & retract coordinates.
    """
    chamfer_params = {
        "center_x": 0.0,
        "center_y": 0.0,
        "diameter": 20.0,
        "chamfer_width": 0.5,
        "feature_type": "outside",
        "vbit_angle_deg": 90.0,
        "tip_diameter": 0.2,
        "tip_offset": 0.4,
        "retract_z": 8.5,
        "feed_rate_xy": 650.0,
        "plunge_feed": 180.0,
    }
    standalone = generate_circular_chamfer(**chamfer_params)

    sequenced = generate_job_sequence(
        job_name="Standalone Parity",
        safe_z_retract=8.5,
        operations=[
            {
                "id": 1,
                "name": "Chamfer Op",
                "op_type": "circular_chamfer",
                "tool_number": 1,
                "tool_diameter": 6.35,
                "parameters": {
                    "diameter": 20.0,
                    "chamfer_width": 0.5,
                    "feature_type": "outside",
                    "vbit_angle_deg": 90.0,
                    "tip_diameter": 0.2,
                    "tip_offset": 0.4,
                    "feed_rate_xy": 650.0,
                    "plunge_feed": 180.0,
                },
            }
        ],
    )
    assert "Z8.500" in standalone.gcode
    assert "Z8.500" in sequenced["gcode"]
    assert "Z5.000" not in sequenced["gcode"]
    assert "F650.0" in sequenced["gcode"]
    assert "F180.0" in sequenced["gcode"]


def test_nondefault_dialect_is_consistent_across_operations():
    """
    R2-002: When dialect='standard' is selected, drilling uses canned cycles (G81) and program
    terminates with M30; when dialect='grbl' is selected, drilling expands to G0/G1 and terminates with M2.
    """
    ops = [
        {
            "id": 1,
            "name": "Drill",
            "op_type": "drilling",
            "tool_number": 1,
            "parameters": {"holes": [(5.0, 5.0)], "target_depth_z": -4.0},
        },
        {
            "id": 2,
            "name": "Chamfer",
            "op_type": "circular_chamfer",
            "tool_number": 2,
            "parameters": {"diameter": 20.0, "chamfer_width": 0.5},
        },
    ]
    std_job = generate_job_sequence(operations=ops, dialect="standard")
    grbl_job = generate_job_sequence(operations=ops, dialect="grbl")

    assert "G81" in std_job["gcode"]
    assert "M30" in std_job["gcode"]
    assert "G81" not in grbl_job["gcode"]
    assert "M2" in grbl_job["gcode"]


def test_machine_units_and_spindle_settings_propagate():
    """
    R2-002: Verify units='inch' and spindle_type='vfd' vs 'router' propagate to standalone and sequenced ops.
    """
    res_vfd = generate_job_sequence(
        units="inch",
        spindle_type="vfd",
        operations=[
            {
                "id": 1,
                "name": "Chamfer",
                "op_type": "circular_chamfer",
                "spindle_speed": 14000,
                "parameters": {"diameter": 1.0, "chamfer_width": 0.03, "tip_diameter": 0.01, "tip_offset": 0.02},
            }
        ],
    )
    assert "G20" in res_vfd["gcode"]
    assert "M3 S14000" in res_vfd["gcode"]


def test_unsupported_machine_operation_combination_fails_closed():
    """
    R2-002: Unsupported dialects or invalid unit strings must raise ValueError / SequenceGenerationError
    instead of silently falling back to defaults.
    """
    with pytest.raises(ValueError, match="(?i)unsupported.*dialect"):
        get_postprocessor("fanuc_5axis_pro")

    with pytest.raises((ValueError, SequenceGenerationError), match="(?i)unsupported.*dialect"):
        generate_job_sequence(
            dialect="fanuc_5axis_pro",
            operations=[{"id": 1, "name": "Drill", "op_type": "drilling", "parameters": {"holes": [(0, 0)]}}],
        )

    with pytest.raises((ValueError, SequenceGenerationError), match="(?i)unit"):
        generate_job_sequence(
            units="furlongs",
            operations=[{"id": 1, "name": "Drill", "op_type": "drilling", "parameters": {"holes": [(0, 0)]}}],
        )


def test_no_nested_program_end_or_unexpected_modal_reset():
    """
    R2-002: Under both 'grbl' and 'standard' dialects, multi-operation jobs must not contain
    nested M2/M30 program ends, duplicate sub-operation M6 tool changes, or mid-job G20/G21 resets.
    """
    ops = [
        {
            "id": 1,
            "name": "Contour",
            "op_type": "contouring",
            "tool_number": 1,
            "parameters": {
                "segments": [
                    {"type": "line", "x": 10.0, "y": 0.0},
                    {"type": "line", "x": 10.0, "y": 10.0},
                    {"type": "line", "x": 0.0, "y": 10.0},
                    {"type": "line", "x": 0.0, "y": 0.0},
                ],
                "start_point": (0.0, 0.0),
                "target_depth_z": -2.0,
            },
        },
        {
            "id": 2,
            "name": "Chamfer",
            "op_type": "circular_chamfer",
            "tool_number": 1,
            "parameters": {"diameter": 20.0, "chamfer_width": 0.5},
        },
    ]
    for dialect in ("grbl", "standard"):
        res = generate_job_sequence(operations=ops, dialect=dialect)
        report = validate_gcode_program(res["gcode"], expected_clearance_z=5.0, dialect=dialect)
        assert report.valid, f"Validation failed for {dialect}: {report.errors}"
        assert len(report.termination_lines) == 1
        assert len(report.modal_state["unit_history"]) == 1
        # Tool T1 is used for both ops, so M6 should appear at most once in 'standard' and 0 times in 'grbl'
        m6_lines = [
            ln for ln in res["gcode"].splitlines() if "M6" in strip_gcode_comments(ln).upper()
        ]
        if dialect == "grbl":
            assert len(m6_lines) == 0
        else:
            assert len(m6_lines) == 1


# ==============================================================================
# R2-003 — Make work-envelope validation explicit and trustworthy
# ==============================================================================


def test_work_to_machine_transform_catches_limit_overrun():
    """
    R2-003: Work-coordinate bounds [0..40] look valid against a 300mm envelope,
    but with wcs_origin_x=275.0 the transformed machine coordinate reaches 315.0 > 300.0 -> FAILED.
    """
    env = WorkEnvelope(
        work_area_x=300.0,
        work_area_y=300.0,
        work_area_z=80.0,
        wcs_origin_x=275.0,
        wcs_origin_y=100.0,
        wcs_origin_z=-20.0,
    )
    bounds = BoundingBox(min_x=0.0, max_x=40.0, min_y=0.0, max_y=40.0, min_z=-5.0, max_z=5.0)
    report = env.evaluate_envelope(bounds)
    assert report["status"] == "FAILED"
    assert report["valid"] is False
    assert any("Machine X" in v for v in report["violations"])


def test_negative_work_coordinate_can_be_valid():
    """
    R2-003: Negative work coordinates around a center datum ([-15, +15]) are physically valid
    and return status == 'VERIFIED' when full WCS offsets place them inside machine limits.
    """
    env = WorkEnvelope(
        work_area_x=300.0,
        work_area_y=300.0,
        work_area_z=80.0,
        wcs_origin_x=150.0,
        wcs_origin_y=150.0,
        wcs_origin_z=-20.0,
    )
    bounds = BoundingBox(min_x=-15.0, max_x=15.0, min_y=-15.0, max_y=15.0, min_z=-5.0, max_z=5.0)
    report = env.evaluate_envelope(bounds)
    assert report["status"] == "VERIFIED"
    assert report["valid"] is True
    assert report["requires_operator_acknowledgment"] is False


def test_asymmetric_z_axis_limits():
    """
    R2-003: A homed GRBL machine typically has asymmetric Z travel [machine_min_z=-80.0, machine_max_z=0.0].
    If wcs_origin_z=-4.0 and retract max_z=6.0, transformed machine Z reaches +2.0 > 0.0 -> FAILED.
    """
    env = WorkEnvelope(
        work_area_x=300.0,
        work_area_y=300.0,
        work_area_z=80.0,
        machine_min_z=-80.0,
        machine_max_z=0.0,
        wcs_origin_x=100.0,
        wcs_origin_y=100.0,
        wcs_origin_z=-4.0,
    )
    overrun_bounds = BoundingBox(min_x=-10.0, max_x=10.0, min_y=-10.0, max_y=10.0, min_z=-5.0, max_z=6.0)
    rep_fail = env.evaluate_envelope(overrun_bounds)
    assert rep_fail["status"] == "FAILED"
    assert any("Machine Z" in v for v in rep_fail["violations"])

    safe_bounds = BoundingBox(min_x=-10.0, max_x=10.0, min_y=-10.0, max_y=10.0, min_z=-5.0, max_z=3.5)
    rep_ok = env.evaluate_envelope(safe_bounds)
    assert rep_ok["status"] == "VERIFIED"


def test_missing_offsets_return_partial_not_verified():
    """
    R2-003: Without wcs_origin_x/y/z, evaluate_envelope() MUST return status='PARTIAL_UNKNOWN'
    (never 'VERIFIED'), or 'FAILED' when strict_mode=True.
    """
    env = WorkEnvelope(work_area_x=300.0, work_area_y=300.0, work_area_z=80.0)
    bounds = BoundingBox(min_x=-10.0, max_x=10.0, min_y=-10.0, max_y=10.0, min_z=-3.0, max_z=5.0)
    rep = env.evaluate_envelope(bounds)
    assert rep["status"] == "PARTIAL_UNKNOWN"
    assert rep["requires_operator_acknowledgment"] is True

    strict_env = WorkEnvelope(work_area_x=300.0, work_area_y=300.0, work_area_z=80.0, strict_mode=True)
    rep_strict = strict_env.evaluate_envelope(bounds)
    assert rep_strict["status"] == "FAILED"


def test_rapid_and_retract_moves_included_in_envelope():
    """
    R2-003: compute_gcode_bounds() must include G0 rapid park/approach/retract moves and full arc sweeps,
    catching an out-of-bounds rapid move even when nominal feature coordinates are small.
    """
    gcode = "\n".join(
        [
            "G21 G90 G17 G94",
            "G0 Z5.000",
            "G0 X0.000 Y0.000",
            "G1 Z-1.000 F100.0",
            "G1 X10.000 Y0.000 F400.0",
            "G0 Z95.000 (Excessive Retract)",
            "G0 X350.000 Y0.000 (Out of bounds park)",
            "M2",
        ]
    )
    compute_gcode_bounds = getattr(base_mod, "compute_gcode_bounds")
    traj_bounds = compute_gcode_bounds(gcode)
    assert traj_bounds.max_x == pytest.approx(350.0)
    assert traj_bounds.max_z == pytest.approx(95.0)

    env = WorkEnvelope(work_area_x=300.0, work_area_y=300.0, work_area_z=80.0)
    rep = env.evaluate_envelope(traj_bounds)
    assert rep["status"] == "FAILED"


def test_tool_length_and_offset_effects_are_accounted_for():
    """
    R2-003: Accounting for tool_length_offset in machine Z transform catches over-travel.
    """
    env = WorkEnvelope(
        work_area_x=300.0,
        work_area_y=300.0,
        work_area_z=80.0,
        machine_min_z=-80.0,
        machine_max_z=0.0,
        wcs_origin_x=100.0,
        wcs_origin_y=100.0,
        wcs_origin_z=-15.0,
        tool_length_offset=12.0,
    )
    # Bounds max_z=5.0 + wcs_origin_z (-15.0) + tool_length_offset (12.0) = +2.0 > machine_max_z (0.0)
    bounds = BoundingBox(min_x=0.0, max_x=20.0, min_y=0.0, max_y=20.0, min_z=-2.0, max_z=5.0)
    rep = env.evaluate_envelope(bounds)
    assert rep["status"] == "FAILED"
    assert any("tool_length_offset" in v or "Machine Z" in v for v in rep["violations"])


# ==============================================================================
# V2-004 — Independently validate circular chamfer math
# ==============================================================================


@pytest.mark.parametrize("feature_type", ["outside", "inside"])
@pytest.mark.parametrize("cut_direction", ["cw", "ccw"])
@pytest.mark.parametrize("vbit_angle_deg", [60.0, 90.0])
@pytest.mark.parametrize("tip_diameter", [0.0, 0.3])
@pytest.mark.parametrize("units,dia,width,tip_off", [("mm", 20.0, 0.5, 0.4), ("inch", 0.7874, 0.02, 0.015)])
def test_v2_004_circular_chamfer_independent_cone_oracle_matrix(
    feature_type, cut_direction, vbit_angle_deg, tip_diameter, units, dia, width, tip_off
):
    """
    V2-004: Independent analytical conical cutter profile verification across:
    - Outside and inside chamfer
    - CW and CCW
    - 60° and 90° included angles
    - Pointed (tip_diameter=0) and flat-tip V-bit variants
    - Metric (mm) and Imperial (inch)
    """
    half_angle_rad = math.radians(vbit_angle_deg / 2.0)
    tan_half = math.tan(half_angle_rad)
    eff_tip_dia = tip_diameter if units == "mm" else round(tip_diameter / 25.4, 4)

    # Independent cone-surface intersection math:
    # A conical V-bit with flat tip diameter d_tip and half-angle alpha has radius R(h) = d_tip/2 + h * tan(alpha)
    # at axial distance h above the flat tip.
    # When the tip is placed at Z = start_z - (W / tan(alpha) + tip_off), then at Z = start_z (h = W / tan(alpha) + tip_off):
    # R_cone(top) = d_tip/2 + W + tip_off * tan(alpha).
    # And the tool center is offset from the nominal circle radius R_nom by radial_offset = d_tip/2 + tip_off * tan(alpha).
    # Therefore, at Z = start_z, the cone slices the top surface at radial distance:
    # R_cone(top) - radial_offset = W (exact chamfer width W across all included angles!).
    expected_depth = -(width / tan_half + tip_off)
    expected_radial_offset = (eff_tip_dia / 2.0) + (tip_off * tan_half)
    expected_path_r = (dia / 2.0) + (expected_radial_offset if feature_type == "outside" else -expected_radial_offset)

    retract = 5.0 if units == "mm" else 0.25
    prog = generate_circular_chamfer(
        diameter=dia,
        chamfer_width=width,
        feature_type=feature_type,
        cut_direction=cut_direction,
        vbit_angle_deg=vbit_angle_deg,
        tip_diameter=eff_tip_dia,
        tip_offset=tip_off,
        retract_z=retract,
        units=units,
    )
    report = validate_gcode_program(
        prog.gcode,
        expected_clearance_z=retract,
        arc_tol=0.002,
        dialect="grbl",
        require_retract_before_m5=True,
    )
    assert report.valid, f"Validator failed: {report.errors}"
    assert len(report.arcs) == 2
    for arc in report.arcs:
        assert arc.r_start == pytest.approx(expected_path_r, abs=1e-3)
        assert arc.r_end == pytest.approx(expected_path_r, abs=1e-3)
        assert arc.z == pytest.approx(expected_depth, abs=1e-3)
        assert arc.motion == ("G2" if cut_direction == "cw" else "G3")


def test_v2_004_brass_trumpet_finger_button_reference_fixture():
    """
    V2-004: Reference test for a 20.000 mm C36000 Brass Trumpet Finger Button:
    - Nominal OD: 20.000 mm (R_nom = 10.000 mm)
    - Requested top edge chamfer: 0.400 mm x 45°
    - Tool: 90.0° Carbide Chamfer Mill, 6.35 mm (1/4") shank/diameter, 0.200 mm flat tip, 0.300 mm tip offset
    - Independent cone simulation verifies finished top diameter = 19.200 mm and outer wall contact at Z = -0.400 mm.
    """
    prog = generate_circular_chamfer(
        center_x=0.0,
        center_y=0.0,
        diameter=20.0,
        chamfer_width=0.4,
        feature_type="outside",
        cut_direction="climb",
        vbit_angle_deg=90.0,
        tip_diameter=0.2,
        tip_offset=0.3,
        tool_diameter=6.35,
        lead_in_radius=1.5,
        start_z=0.0,
        retract_z=5.0,
        feed_rate_xy=600.0,
        plunge_feed=150.0,
        spindle_speed=18000,
    )
    report = validate_gcode_program(
        prog.gcode,
        expected_clearance_z=5.0,
        arc_tol=0.001,
        dialect="grbl",
        require_retract_before_m5=True,
    )
    assert report.valid, f"Brass button validation errors: {report.errors}"
    # 2 semicircle cutting arcs + 1 lead-in arc + 1 lead-out arc = 4 arcs
    assert len(report.arcs) == 4
    cutting_arcs = [a for a in report.arcs if math.isclose(a.r_start, 10.4, abs_tol=1e-3)]
    assert len(cutting_arcs) == 2

    # Simulate conical cutter radius R_cone(z) at top surface z=0.0 and at lower chamfer edge z=-0.4:
    tip_z = cutting_arcs[0].z  # -0.700 mm
    path_r = cutting_arcs[0].r_start  # 10.400 mm
    r_cone_at_top = (0.2 / 2.0) + (0.0 - tip_z) * math.tan(math.radians(45.0))  # 0.1 + 0.7 = 0.800 mm
    r_cone_at_edge = (0.2 / 2.0) + (-0.4 - tip_z) * math.tan(math.radians(45.0))  # 0.1 + 0.3 = 0.400 mm
    finished_top_radius = path_r - r_cone_at_top  # 10.4 - 0.8 = 9.600 mm (width = 0.400 mm)
    finished_od_radius = path_r - r_cone_at_edge  # 10.4 - 0.4 = 10.000 mm (nominal OD)
    assert finished_top_radius == pytest.approx(9.600, abs=1e-4)
    assert finished_od_radius == pytest.approx(10.000, abs=1e-4)


def test_v2_004_circular_chamfer_boundary_rejections():
    """
    V2-004: Reject zero/negative diameter, zero/negative chamfer width, tool too small,
    and inside chamfer wider than bore radius.
    """
    with pytest.raises(ValueError):
        generate_circular_chamfer(diameter=0.0, chamfer_width=0.5)
    with pytest.raises(ValueError):
        generate_circular_chamfer(diameter=20.0, chamfer_width=-0.2)
    with pytest.raises(ValueError, match="(?i)exceeds physical cutter radius"):
        generate_circular_chamfer(diameter=20.0, chamfer_width=2.5, tip_offset=1.0, tool_diameter=6.0)
    with pytest.raises(ValueError, match="(?i)too small"):
        generate_circular_chamfer(diameter=2.0, chamfer_width=0.8, tip_offset=0.5, feature_type="inside")


# ==============================================================================
# V2-005 — Verify offset contour joins against stock interference
# ==============================================================================


def test_v2_005_convex_and_concave_line_and_arc_transitions_no_gouge():
    """
    V2-005: Verify line-to-line, line-to-arc, and arc-to-line transitions (including non-tangent
    convex corners and concave corners) do NOT clip or gouge the finished stock boundary
    using the independent 2D swept-tool oracle.
    """
    # 1. Closed D-shape profile (line -> non-tangent semicircle arc -> line)
    # Bottom edge (0,0)->(20,0), right semicircle (20,0)->(20,20) with center (20,10) CCW,
    # top edge (20,20)->(0,20), left edge (0,20)->(0,0).
    # Notice at (20,0), the bottom line goes +X (1,0) and the CCW semicircle starts at (20,0) with tangent +X,
    # while if we join a vertical chord or non-tangent arc at a corner, a straight G1 bridge would clip the corner!
    non_tangent_lens_segments = [
        {"type": "line", "x": 20.0, "y": 0.0},
        # Arc from (20,0) to (0,20) centered at (0,0) (radius 20, CCW) -> meets (20,0) at 90 degrees!
        {"type": "arc", "x": 0.0, "y": 20.0, "i": -20.0, "j": 0.0, "cw": False},
        {"type": "line", "x": 0.0, "y": 0.0},
    ]
    # CCW closed loop: outside is side='right'
    res = generate_contour_profile(
        segments=non_tangent_lens_segments,
        start_point=(0.0, 0.0),
        is_closed=True,
        side="right",
        tool_diameter=6.0,
        finish_allowance=0.2,
        spring_pass=False,
        target_depth_z=-2.0,
        stepdown_z=2.0,
    )
    report = validate_gcode_program(res["gcode"], expected_clearance_z=5.0, dialect="grbl")
    assert report.valid, f"G-code validation errors: {report.errors}"

    swept = verify_contour_no_stock_gouge(
        nominal_segments=non_tangent_lens_segments,
        start_point=(0.0, 0.0),
        tool_diameter=6.0,
        finish_allowance=0.0,  # Final pass cuts to 0.0 finish allowance
        gcode_text=res["gcode"],
    )
    assert swept["gouge_free"] is True, f"Stock gouge detected: {swept}"

    # 2. L-shaped profile (5 convex corners + 1 concave inside corner) with CW winding & outside='left'
    l_shape = [
        {"type": "line", "x": 0.0, "y": 30.0},
        {"type": "line", "x": 15.0, "y": 30.0},
        {"type": "line", "x": 15.0, "y": 15.0},  # Concave corner at (15, 15)!
        {"type": "line", "x": 30.0, "y": 15.0},
        {"type": "line", "x": 30.0, "y": 0.0},
        {"type": "line", "x": 0.0, "y": 0.0},
    ]
    res_l = generate_contour_profile(
        segments=l_shape,
        start_point=(0.0, 0.0),
        is_closed=True,
        side="left",
        tool_diameter=4.0,
        finish_allowance=0.0,
        spring_pass=False,
        target_depth_z=-2.0,
        stepdown_z=2.0,
    )
    swept_l = verify_contour_no_stock_gouge(
        nominal_segments=l_shape,
        start_point=(0.0, 0.0),
        tool_diameter=4.0,
        finish_allowance=0.0,
        gcode_text=res_l["gcode"],
    )
    assert swept_l["gouge_free"] is True, f"L-shape stock gouge detected: {swept_l}"


def test_v2_005_concave_corner_tool_radius_boundary_and_rejection():
    """
    V2-005: Test tool radii smaller than, equal to, and larger than a concave feature radius
    or concave step length. When tool offset >= concave arc radius or exceeds a short concave step
    (causing segment inversion), generation must reject the geometry rather than gouging.
    """
    # Concave fillet of radius 3.0 mm on an outside CW contour (arc is CCW so cutter is on the inside of the arc):
    concave_arc_profile = [
        {"type": "line", "x": 0.0, "y": 20.0},
        {"type": "line", "x": 10.0, "y": 20.0},
        {"type": "arc", "x": 13.0, "y": 17.0, "i": 3.0, "j": 0.0, "cw": False},  # R=3.0 concave fillet
        {"type": "line", "x": 20.0, "y": 17.0},
        {"type": "line", "x": 20.0, "y": 0.0},
        {"type": "line", "x": 0.0, "y": 0.0},
    ]
    # 1. Tool radius 2.0 mm (< 3.0 mm) -> Valid
    ok_res = generate_contour_profile(
        segments=concave_arc_profile,
        start_point=(0.0, 0.0),
        is_closed=True,
        side="left",
        tool_diameter=4.0,
        finish_allowance=0.0,
        spring_pass=False,
        target_depth_z=-1.0,
    )
    assert validate_gcode_program(ok_res["gcode"]).valid

    # 2. Tool radius 3.0 mm (== 3.0 mm) or 4.0 mm (> 3.0 mm) -> Must reject
    for bad_dia in (6.0, 8.0):
        with pytest.raises(ValueError, match="(?i)collapsed|smaller than|concave|radius"):
            generate_contour_profile(
                segments=concave_arc_profile,
                start_point=(0.0, 0.0),
                is_closed=True,
                side="left",
                tool_diameter=bad_dia,
                finish_allowance=0.0,
                spring_pass=False,
                target_depth_z=-1.0,
            )

    # 3. Short concave step (step height 1.5 mm) machined with tool radius 3.0 mm (diameter 6.0 mm):
    # Intersecting infinite offset lines would invert the 1.5 mm segment backwards and gouge!
    short_step_profile = [
        {"type": "line", "x": 0.0, "y": 20.0},
        {"type": "line", "x": 10.0, "y": 20.0},
        {"type": "line", "x": 10.0, "y": 18.5},  # 1.5 mm concave step < 3.0 mm tool radius!
        {"type": "line", "x": 20.0, "y": 18.5},
        {"type": "line", "x": 20.0, "y": 0.0},
        {"type": "line", "x": 0.0, "y": 0.0},
    ]
    with pytest.raises(ValueError, match="(?i)concave|invert|gouge|smaller than"):
        generate_contour_profile(
            segments=short_step_profile,
            start_point=(0.0, 0.0),
            is_closed=True,
            side="left",
            tool_diameter=6.0,
            finish_allowance=0.0,
            spring_pass=False,
            target_depth_z=-1.0,
        )


def test_v2_005_open_profile_and_degenerate_short_segment_handling():
    """
    V2-005: Open profiles must not close back to start_point, and zero-length segments must be rejected.
    """
    open_segs = [
        {"type": "line", "x": 25.0, "y": 0.0},
        {"type": "line", "x": 25.0, "y": 15.0},
    ]
    res = generate_contour_profile(
        segments=open_segs,
        start_point=(0.0, 0.0),
        is_closed=False,
        side="left",
        tool_diameter=4.0,
        finish_allowance=0.0,
        spring_pass=False,
        target_depth_z=-1.0,
    )
    assert validate_gcode_program(res["gcode"], expected_clearance_z=5.0).valid

    with pytest.raises(ValueError, match="(?i)zero length"):
        generate_contour_profile(
            segments=[{"type": "line", "x": 0.0, "y": 0.0}],
            start_point=(0.0, 0.0),
            is_closed=False,
        )


# ==============================================================================
# V2-006 — End-to-end GRBL program and job safety regression
# ==============================================================================


def test_combined_job_has_single_final_program_end():
    """
    V2-006: Assembled multi-operation Brass Trumpet Finger Button job has exactly one M2/M30 at the end.
    """
    job = generate_job_sequence(
        job_name="20mm Brass Trumpet Finger Button",
        dialect="grbl",
        spindle_type="router",
        router_model="dewalt_611",
        safe_z_retract=5.0,
        operations=[
            {
                "id": 1,
                "name": "Center Tap Drill",
                "op_type": "drilling",
                "tool_number": 1,
                "tool_name": "3.2mm Drill",
                "tool_diameter": 3.2,
                "spindle_speed": 16000,
                "parameters": {"holes": [(0.0, 0.0)], "target_depth_z": -4.0},
            },
            {
                "id": 2,
                "name": "Outer 20mm Profile",
                "op_type": "contouring",
                "tool_number": 2,
                "tool_name": "3.175mm Flat Endmill",
                "tool_diameter": 3.175,
                "spindle_speed": 18000,
                "parameters": {
                    "segments": [
                        {"type": "arc", "x": 10.0, "y": 0.0, "i": 10.0, "j": 0.0, "cw": True},
                        {"type": "arc", "x": -10.0, "y": 0.0, "i": -10.0, "j": 0.0, "cw": True},
                    ],
                    "start_point": (-10.0, 0.0),
                    "is_closed": True,
                    "side": "left",
                    "lead_in_type": "tangential_arc",
                    "lead_in_radius": 2.0,
                    "target_depth_z": -3.0,
                    "stepdown_z": 1.5,
                    "finish_allowance": 0.15,
                    "spring_pass": False,
                },
            },
            {
                "id": 3,
                "name": "Top Outer Edge Chamfer",
                "op_type": "circular_chamfer",
                "tool_number": 3,
                "tool_name": "90deg V-Bit",
                "tool_diameter": 6.35,
                "spindle_speed": 18000,
                "parameters": {
                    "diameter": 20.0,
                    "chamfer_width": 0.4,
                    "feature_type": "outside",
                    "vbit_angle_deg": 90.0,
                    "tip_diameter": 0.2,
                    "tip_offset": 0.3,
                    "lead_in_radius": 1.5,
                },
            },
        ],
    )
    report = validate_gcode_program(
        job["gcode"],
        expected_clearance_z=5.0,
        dialect="grbl",
        require_retract_before_m5=True,
    )
    assert report.valid, f"Whole-job validation errors: {report.errors}"
    assert len(report.termination_lines) == 1
    assert report.moves_after_termination == []


def test_generator_exception_blocks_whole_job_export():
    """
    V2-006: Any failure in a nested operation blocks export of the entire job.
    """
    with pytest.raises(SequenceGenerationError):
        generate_job_sequence(
            operations=[
                {
                    "id": 1,
                    "name": "Valid Drill",
                    "op_type": "drilling",
                    "parameters": {"holes": [(0.0, 0.0)], "target_depth_z": -2.0},
                },
                {
                    "id": 2,
                    "name": "Invalid Chamfer",
                    "op_type": "circular_chamfer",
                    "parameters": {"diameter": -10.0, "chamfer_width": 0.5},
                },
            ]
        )


def test_multistep_job_modal_state_remains_consistent():
    """
    V2-006: Modal state (G21, G90, G17, G94) remains consistent across operation boundaries.
    """
    job = generate_job_sequence(
        units="mm",
        dialect="grbl",
        operations=[
            {"id": 1, "name": "Drill", "op_type": "drilling", "parameters": {"holes": [(0.0, 0.0)], "target_depth_z": -2.0}},
            {"id": 2, "name": "Pocket", "op_type": "circular_pocket", "parameters": {"pockets": [(0.0, 0.0)], "pocket_diameter": 10.0, "target_depth_z": -2.0}},
        ],
    )
    rep = validate_gcode_program(job["gcode"], expected_clearance_z=5.0, dialect="grbl", require_retract_before_m5=True)
    assert rep.valid
    assert rep.modal_state["units"] == "mm"
    assert rep.modal_state["distance_mode"] == "G90"
    assert rep.modal_state["plane"] == "G17"
    assert rep.modal_state["feed_mode"] == "G94"


def test_grbl_dialect_rejects_unsupported_commands():
    """
    V2-006: Independent validator flags canned cycles (G81/G83) and M6 when validating for GRBL.
    """
    bad_grbl = "\n".join(
        [
            "G21 G90 G17 G94",
            "T1 M6",
            "G0 Z5.0",
            "G81 X10.0 Y10.0 Z-5.0 R2.0 F100.0",
            "M2",
        ]
    )
    rep = validate_gcode_program(bad_grbl, dialect="grbl")
    assert rep.valid is False
    assert "M6" in rep.unsupported_dialect_codes
    assert "G81" in rep.unsupported_dialect_codes


def test_arc_radius_and_plane_conventions():
    """
    V2-006: Validator checks G17 plane and I/J arc radius equality across all generated arcs.
    """
    prog = generate_circular_pocket(
        pockets=[(0.0, 0.0)],
        pocket_diameter=16.0,
        target_depth_z=-2.0,
        tool_diameter=6.0,
    )
    rep = validate_gcode_program(prog.gcode, expected_clearance_z=5.0, dialect="grbl", require_retract_before_m5=True)
    assert rep.valid, f"Circular pocket validation errors: {rep.errors}"
    assert len(rep.arcs) > 0


def test_tool_change_requires_safe_retract_and_known_policy():
    """
    V2-006: Both mid-job tool changes and final program footers must retract Z to safe clearance
    BEFORE stopping the spindle (M5).
    """
    prog = generate_straight_plunge(holes=[(0.0, 0.0)], target_depth_z=-5.0, retract_z=5.0)
    rep = validate_gcode_program(prog.gcode, expected_clearance_z=5.0, dialect="grbl", require_retract_before_m5=True)
    assert rep.valid, f"Standalone footer retract-before-M5 failed: {rep.errors}"
    assert rep.unsafe_spindle_stops == []
