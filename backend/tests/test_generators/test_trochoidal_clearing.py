import pytest
from app.generators.base import WorkEnvelope
from app.generators.slotting import generate_linear_slot, generate_arc_slot
from app.generators.rectangular_pocket import generate_rectangular_pocket
from app.generators.sequencer import generate_job_sequence
from app.models import db, Tool
from tests.gcode_validator import (
    validate_gcode_program,
    verify_swept_slot_containment,
    verify_swept_pocket_containment,
)


def test_linear_slot_trochoidal_arc_validity_and_non_gouge():
    """Verify trochoidal linear slot emits valid GRBL G3 loops, ramp entry, cleanup pass, and zero wall overcut."""
    program = generate_linear_slot(
        start_x=10.0,
        start_y=15.0,
        end_x=35.0,
        end_y=15.0,
        slot_width=6.0,
        target_depth_z=-2.0,
        stepdown_z=1.0,
        retract_z=5.0,
        tool_diameter=3.175,
        cutting_strategy="trochoidal",
        trochoidal_stepover_pct=15.0,
    )
    report = validate_gcode_program(
        program.gcode,
        arc_tol=0.002,
        expected_clearance_z=5.0,
        require_retract_before_m5=True,
        dialect="grbl",
    )
    assert report.valid, f"GRBL validation failed: {report.errors}"
    assert len(report.arcs) >= 5, "Expected multiple trochoidal G3 loops and cleanup arcs"
    assert all(a.motion == "G3" for a in report.arcs), "Trochoidal loops and cleanup should use G3 climb milling"

    containment = verify_swept_slot_containment(
        program.gcode,
        slot_width=6.0,
        tool_diameter=3.175,
        start_x=10.0,
        start_y=15.0,
        end_x=35.0,
        end_y=15.0,
    )
    assert containment["contained"], f"Swept slot overcut detected: {containment}"


def test_arc_slot_trochoidal_and_conventional():
    """Verify generate_arc_slot in both conventional and trochoidal modes with outer-wall pitch scaling."""
    conv = generate_arc_slot(
        center_x=50.0,
        center_y=50.0,
        radius=25.0,
        start_angle_deg=0.0,
        end_angle_deg=90.0,
        slot_width=6.0,
        target_depth_z=-1.5,
        stepdown_z=1.5,
        retract_z=5.0,
        tool_diameter=3.175,
        cutting_strategy="conventional",
    )
    conv_report = validate_gcode_program(conv.gcode, arc_tol=0.002, expected_clearance_z=5.0, dialect="grbl")
    assert conv_report.valid, f"Conventional arc slot failed: {conv_report.errors}"
    conv_contain = verify_swept_slot_containment(
        conv.gcode,
        slot_width=6.0,
        tool_diameter=3.175,
        center_x=50.0,
        center_y=50.0,
        radius=25.0,
        start_angle_deg=0.0,
        end_angle_deg=90.0,
    )
    assert conv_contain["contained"], f"Conventional arc slot overcut: {conv_contain}"

    troch = generate_arc_slot(
        center_x=50.0,
        center_y=50.0,
        radius=25.0,
        start_angle_deg=0.0,
        end_angle_deg=90.0,
        slot_width=6.0,
        target_depth_z=-1.5,
        stepdown_z=1.5,
        retract_z=5.0,
        tool_diameter=3.175,
        cutting_strategy="trochoidal",
        trochoidal_stepover_pct=15.0,
    )
    troch_report = validate_gcode_program(troch.gcode, arc_tol=0.002, expected_clearance_z=5.0, dialect="grbl")
    assert troch_report.valid, f"Trochoidal arc slot failed: {troch_report.errors}"
    assert len(troch_report.arcs) >= 10, "Expected trochoidal loops along arc slot"
    troch_contain = verify_swept_slot_containment(
        troch.gcode,
        slot_width=6.0,
        tool_diameter=3.175,
        center_x=50.0,
        center_y=50.0,
        radius=25.0,
        start_angle_deg=0.0,
        end_angle_deg=90.0,
    )
    assert troch_contain["contained"], f"Trochoidal arc slot overcut: {troch_contain}"


def test_trochoidal_rejects_narrow_slot_and_invalid_stepover():
    """Verify trochoidal mode rejects slot_width < 1.05 * tool_diameter and out-of-range stepover."""
    with pytest.raises(ValueError, match="1.05|wider|Trochoidal"):
        generate_linear_slot(
            start_x=0.0,
            start_y=0.0,
            end_x=20.0,
            end_y=0.0,
            slot_width=3.175,
            tool_diameter=3.175,
            cutting_strategy="trochoidal",
        )

    with pytest.raises(ValueError, match="1.05|wider|Trochoidal"):
        generate_arc_slot(
            center_x=30.0,
            center_y=30.0,
            radius=15.0,
            start_angle_deg=0.0,
            end_angle_deg=60.0,
            slot_width=3.2,
            tool_diameter=3.175,
            cutting_strategy="trochoidal",
        )

    with pytest.raises(ValueError, match="trochoidal_stepover_pct"):
        generate_linear_slot(
            start_x=0.0,
            start_y=0.0,
            end_x=20.0,
            end_y=0.0,
            slot_width=6.0,
            tool_diameter=3.175,
            cutting_strategy="trochoidal",
            trochoidal_stepover_pct=45.0,
        )


def test_api_trochoidal_endpoints_and_tool_id_validation(client, app):
    """Verify REST API forwarding for linear slot, arc slot, pocket, and tool_id-resolved HTTP 400 validation."""
    with app.app_context():
        tool = Tool(tool_number=99, name="Test 6.35mm Endmill", tool_type="endmill", diameter=6.35, flute_count=2)
        db.session.add(tool)
        db.session.commit()
        tool_id = tool.id

    # Valid trochoidal linear slot
    res_lin = client.post(
        "/api/generate/slotting/linear",
        json={
            "start_x": 10.0,
            "start_y": 10.0,
            "end_x": 40.0,
            "end_y": 10.0,
            "slot_width": 6.0,
            "target_depth_z": -2.0,
            "tool_diameter": 3.175,
            "cutting_strategy": "trochoidal",
            "trochoidal_stepover_pct": 15.0,
        },
    )
    assert res_lin.status_code == 200
    assert "G3" in res_lin.get_json()["data"]["gcode"]

    # tool_id resolves to 6.35mm -> slot_width 6.35mm must fail with HTTP 400 in trochoidal mode
    res_bad_tool = client.post(
        "/api/generate/slotting/linear",
        json={
            "start_x": 10.0,
            "start_y": 10.0,
            "end_x": 40.0,
            "end_y": 10.0,
            "slot_width": 6.35,
            "target_depth_z": -2.0,
            "tool_id": tool_id,
            "cutting_strategy": "trochoidal",
        },
    )
    assert res_bad_tool.status_code == 400

    # Valid trochoidal arc slot endpoint
    res_arc = client.post(
        "/api/generate/slotting/arc",
        json={
            "center_x": 40.0,
            "center_y": 40.0,
            "radius": 20.0,
            "start_angle_deg": 0.0,
            "end_angle_deg": 90.0,
            "slot_width": 6.0,
            "target_depth_z": -2.0,
            "tool_diameter": 3.175,
            "cutting_strategy": "trochoidal",
            "trochoidal_stepover_pct": 15.0,
        },
    )
    assert res_arc.status_code == 200
    assert "G3" in res_arc.get_json()["data"]["gcode"]

    # Valid rectangular pocket with trochoidal_entry
    res_pkt = client.post(
        "/api/generate/pocket/rectangular",
        json={
            "origin_x": 50.0,
            "origin_y": 50.0,
            "length_x": 40.0,
            "width_y": 25.0,
            "target_depth_z": -3.0,
            "tool_diameter": 3.175,
            "trochoidal_entry": True,
            "trochoidal_stepover_pct": 15.0,
        },
    )
    assert res_pkt.status_code == 200
    assert "G3" in res_pkt.get_json()["data"]["gcode"]


def test_rectangular_pocket_trochoidal_orientations_and_sequencer():
    """Verify trochoidal_entry on horizontal, vertical (width_y > length_x), square, and narrow pockets + sequencer."""
    cases = [
        (40.0, 25.0, 3.175),  # horizontal
        (25.0, 40.0, 3.175),  # vertical
        (30.0, 30.0, 3.175),  # square
        (20.0, 6.0, 3.175),   # narrow
    ]
    for lx, wy, td in cases:
        prog = generate_rectangular_pocket(
            origin_x=50.0,
            origin_y=50.0,
            length_x=lx,
            width_y=wy,
            origin_mode="center",
            target_depth_z=-2.0,
            stepdown_z=2.0,
            retract_z=5.0,
            tool_diameter=td,
            trochoidal_entry=True,
            trochoidal_stepover_pct=15.0,
            work_envelope=WorkEnvelope(work_area_x=300.0, work_area_y=300.0, work_area_z=100.0),
        )
        rep = validate_gcode_program(prog.gcode, arc_tol=0.002, expected_clearance_z=5.0, dialect="grbl")
        assert rep.valid, f"Pocket {lx}x{wy} invalid: {rep.errors}"
        contain = verify_swept_pocket_containment(
            prog.gcode,
            min_x=50.0 - lx / 2.0,
            max_x=50.0 + lx / 2.0,
            min_y=50.0 - wy / 2.0,
            max_y=50.0 + wy / 2.0,
            tool_diameter=td,
        )
        assert contain["contained"], f"Pocket {lx}x{wy} overcut: {contain}"

    # Multi-op sequencer composition
    seq = generate_job_sequence(
        [
            {
                "type": "linear_slot",
                "params": {
                    "start_x": 10.0,
                    "start_y": 10.0,
                    "end_x": 35.0,
                    "end_y": 10.0,
                    "slot_width": 6.0,
                    "target_depth_z": -1.5,
                    "tool_diameter": 3.175,
                    "cutting_strategy": "trochoidal",
                    "trochoidal_stepover_pct": 15.0,
                },
            },
            {
                "type": "arc_slot",
                "params": {
                    "center_x": 60.0,
                    "center_y": 60.0,
                    "radius": 20.0,
                    "start_angle_deg": 0.0,
                    "end_angle_deg": 60.0,
                    "slot_width": 6.0,
                    "target_depth_z": -1.5,
                    "tool_diameter": 3.175,
                    "cutting_strategy": "trochoidal",
                    "trochoidal_stepover_pct": 15.0,
                },
            },
            {
                "type": "rectangular_pocket",
                "params": {
                    "origin_x": 120.0,
                    "origin_y": 60.0,
                    "length_x": 30.0,
                    "width_y": 20.0,
                    "target_depth_z": -1.5,
                    "tool_diameter": 3.175,
                    "trochoidal_entry": True,
                },
            },
        ]
    )
    seq_rep = validate_gcode_program(seq["gcode"], arc_tol=0.002, expected_clearance_z=5.0, dialect="grbl")
    assert seq_rep.valid, f"Sequenced trochoidal program invalid: {seq_rep.errors}"


def test_conventional_slotting_backward_compatibility():
    """Ensure default conventional linear slot preserves exact legacy bounds and single centerline pass."""
    prog = generate_linear_slot(
        start_x=10.0,
        start_y=20.0,
        end_x=60.0,
        end_y=20.0,
        slot_width=3.175,
        target_depth_z=-2.0,
        stepdown_z=1.0,
        tool_diameter=3.175,
    )
    assert prog.bounds.min_x == 10.0
    assert prog.bounds.max_x == 60.0
    assert "G3" not in prog.gcode
