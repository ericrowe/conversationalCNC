# Walkthrough — Plan 09: Remediation Handoff v2.0 & Swept-Geometry Verification (`R2-001` – `V2-006`)

**Date**: 2026-11-05  
**Plan Reference**: [`2026-11-05-09_remediation_handoff_v2_and_swept_geometry_verification_plan.md`](./2026-11-05-09_remediation_handoff_v2_and_swept_geometry_verification_plan.md)  
**Pinned Baseline Commit**: `277e592` (`Conversational-CNC-Controller`) / `17b028e` (`server-rack`)

---

## 1. Summary of Remediations & Verification Gates (`R2-001` – `V2-006`)

| ID | Severity | Finding | Resolution | RED $\to$ GREEN |
| :--- | :--- | :--- | :--- | :--- |
| **`R2-001`** | **HIGH** | Sequencer `optimize_tool_order` Can Violate Machining Dependencies | Implemented `_order_operations_with_trace()` in [`sequencer.py`](../../../backend/app/generators/sequencer.py) preserving authored order `[1, 2, 3]` unless `independent=True`, validating DAG `depends_on` edges, rejecting cycles/unknown IDs, and returning `summary.optimization_trace`. | `5 failed` $\to$ `6 passed` |
| **`R2-002`** | **HIGH** | Machine/Postprocessor Context Not Propagated End-to-End | Added `MachiningContext` and `normalize_units()` in [`base.py`](../../../backend/app/generators/base.py), fail-closed `get_postprocessor()` in [`registry.py`](../../../backend/app/postprocessors/registry.py), context propagation in [`sequencer.py`](../../../backend/app/generators/sequencer.py), and inner `M6` stripping in `strip_header_and_footer()`. | `4 failed` $\to$ `6 passed` |
| **`R2-003`** | **HIGH** | WorkEnvelope Validation Uses Naive Positive-Only Bounds | Upgraded `WorkEnvelope` in [`base.py`](../../../backend/app/generators/base.py) with `min_x/max_x`, `min_y/max_y`, `min_z/max_z`, `wcs_origin_x/y/z`, `tool_length_offset`, `strict_mode`, `compute_gcode_bounds()`, and tri-state `status` (`VERIFIED`, `PARTIAL_UNKNOWN`, `FAILED`). | `6 failed` $\to$ `6 passed` |
| **`V2-004`** | **MEDIUM** | Circular Chamfer Independent Cone-Geometry Oracle | Added `units` (`mm`/`inch`), `dialect` resolution, unit-scaled lead-in clearance, and inside-bore radius collapse guard in [`chamfering.py`](../../../backend/app/generators/chamfering.py); verified against 32-case independent cone oracle matrix and 20 mm Brass Trumpet Finger Button fixture. | `17 failed` $\to$ `34 passed` |
| **`V2-005`** | **MEDIUM** | Contour Arc Offset Transitions & Swept-Tool Non-Gouge Proof | Replaced straight `G1` bridges at convex non-tangent transitions in [`contouring.py`](../../../backend/app/generators/contouring.py) with tangent corner-roll arcs (`G2`/`G3`) of radius `|active_offset|` centered at vertex $V=(vx,vy)$; tracked `orig_ox0/oy0` and `t_start/t_end` to reject concave segment inversions; verified with `verify_contour_no_stock_gouge()` in [`gcode_validator.py`](../../../backend/tests/gcode_validator.py). | `2 failed` $\to$ `3 passed` |
| **`V2-006`** | **MEDIUM** | Sequencer Whole-Job G-Code & Retract-Before-Stop Validation | Updated `GrblPostProcessor.format_footer()` in [`grbl.py`](../../../backend/app/postprocessors/grbl.py) to emit `G0 Z<park_z>` before `M5`; enhanced `validate_gcode()` in [`gcode_validator.py`](../../../backend/tests/gcode_validator.py) with dialect checks (`G81`–`G83`, `M6`), retract-before-`M5`, and modal history. | `2 failed` $\to$ `6 passed` |

---

## 2. Test & Coverage Scorecard

- **Remediation Handoff v2.0 Suite** ([`backend/tests/test_remediation_handoff_v2.py`](../../../backend/tests/test_remediation_handoff_v2.py)):
  - **Pre-Patch (RED)**: `36 failed, 25 passed in 0.33s`
  - **Post-Patch (GREEN)**: `61 passed in 0.06s`
- **Full Subsystem Test Suite** (`./Conversational-CNC-Controller/run_tests.sh`):
  - **Result**: `289 passed in 1.70s` (`+61` tests over Plan 08 baseline of `228`)
  - **Statement Coverage**: `87%` (`5,328 / 6,275` statements)
  - **Branch Coverage**: `82%` (`1,518 / 1,908` branches)
  - **Critical Domain Invariants**: `5 / 5` (`100.0%`)
