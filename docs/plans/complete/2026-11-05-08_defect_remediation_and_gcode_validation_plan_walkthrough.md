# Walkthrough — Plan 08: Defect Remediation, Circular Chamfering & Independent G-Code Validation Suite (`CNC-001` – `CNC-014`)

- **Archived Plan**: [`2026-11-05-08_defect_remediation_and_gcode_validation_plan.md`](2026-11-05-08_defect_remediation_and_gcode_validation_plan.md)
- **Pinned Baseline Commit SHA**: `6ca5ec5394ff20a76eb3d340172d928ec3031e11`
- **Completion Date**: `2026-11-05`

---

## 1. Summary of Remediations (`CNC-001` through `CNC-014`)

| ID | Severity | Defect Summary | Status | Implementation & Verification |
| :--- | :---: | :--- | :---: | :--- |
| **`CNC-001`** | **P0** | Compensated contour arcs leave endpoints un-offset; corners disconnected | **Fixed** | [`contouring.py`](../../../backend/app/generators/contouring.py) now computes compensated arc radii (`R_comp = R ± offset`), compensated `I/J` center offsets, line-line corner intersections, tangent corner arcs, and raises `ValueError` when an inside arc radius collapses (`R_comp <= 0`). |
| **`CNC-002`** | **P0** | Contour lead-in arc has non-existent/mismatched radius (`|I,J|` vs `|end-start|`) | **Fixed** | [`contouring.py`](../../../backend/app/generators/contouring.py) computes an exact quarter-circle (`90°`) entry arc tangent to the initial segment direction vector $\hat{t}_0$ with center $\vec{C}_{\text{in}} = \vec{P}_0 + \hat{n}_{\text{side}} R_L$ and start point $\vec{P}_{\text{in}} = \vec{C}_{\text{in}} - \hat{t}_0 R_L$. |
| **`CNC-003`** | **P0** | Contour lead-out arc uses wrong `I/J` sign & fixed `G3` direction | **Fixed** | [`contouring.py`](../../../backend/app/generators/contouring.py) computes exit arc center $\vec{C}_{\text{out}} = \vec{P}_{\text{end}} + \hat{n}_{\text{side}} R_L$, sets `I/J` as $\vec{C}_{\text{out}} - \vec{P}_{\text{end}}$, and selects `G2` or `G3` dynamically from $\hat{t}_{\text{end}} \times \hat{n}_{\text{side}}$. |
| **`CNC-004`** | **P0** | `strip_header_and_footer()` fails to strip `M2 (Program End)` & parks between sequenced ops | **Fixed** | [`base.py`](../../../backend/app/generators/base.py) strips inline comments before matching modal setup/termination codes (`M2`, `M30`, `M5`, `M9`, `%`, and `(Park)`), ensuring multi-operation sequences emit only a single final `M2`. |
| **`CNC-005`** | **P0** | Sequencer converts sub-generator exceptions into G-code comments and returns `200 OK` | **Fixed** | [`sequencer.py`](../../../backend/app/generators/sequencer.py) raises `SequenceGenerationError` and [`api/sequencer.py`](../../../backend/app/api/sequencer.py) returns HTTP `400 Bad Request` on any sub-operation failure or unknown operation type. |
| **`CNC-006`** | **P1** | Contouring silently flips positive depth and ignores finish-allowance without cutter compensation | **Fixed** | [`contouring_schema.py`](../../../backend/app/schemas/contouring_schema.py) and [`contouring.py`](../../../backend/app/generators/contouring.py) reject `target_depth_z >= top_z` and reject `side="center"` when `finish_allowance > 0` or `spring_pass=True`. |
| **`CNC-007`** | **P1** | Envelope check compares WCS directly to machine work volume & checks only single `z_val` | **Fixed** | [`base.py`](../../../backend/app/generators/base.py) checks both `z_min` and `z_max` against `max_z_mm`, supports optional `wcs_origin` (`x, y, z`) for machine-limit bounds checking, and returns `envelope_status` via `evaluate_envelope()`. |
| **`CNC-008`** | **P1** | Missing circular chamfer generator (blocks **20 mm Brass Trumpet Finger Button** workflow) | **Fixed** | Implemented [`generate_circular_chamfer()`](../../../backend/app/generators/chamfering.py), [`CircularChamferSchema`](../../../backend/app/schemas/chamfering_schema.py), `POST /api/generate/chamfering/circular` in [`api/generate.py`](../../../backend/app/api/generate.py), and `"circular_chamfer"` in [`sequencer.py`](../../../backend/app/generators/sequencer.py). |
| **`CNC-009`** | **P1** | Contouring accepts empty segments (`[]`) and impossible arc radii without error | **Fixed** | [`contouring_schema.py`](../../../backend/app/schemas/contouring_schema.py) and [`contouring.py`](../../../backend/app/generators/contouring.py) reject empty `segments` and validate every arc segment's endpoint distance against its center (`|R_start - R_end| <= 1e-3`). |
| **`CNC-010`** | **P2** | Sequencer global re-sort can move finishing/chamfering before roughing if tool ID matches | **Fixed** | Replaced naive sort in [`sequencer.py`](../../../backend/app/generators/sequencer.py) with `_order_operations_safely()`, preserving phase ordering across surfacing, roughing/pocketing, drilling/threading, chamfering/engraving, and cutoff. |
| **`CNC-011`** | **P2** | Sequencer silently swallows `apply_z_mesh_compensation` errors and falls back to un-leveled G-code | **Fixed** | [`sequencer.py`](../../../backend/app/generators/sequencer.py) validates `mesh_data` whenever `apply_mesh_leveling=True` and raises `SequenceGenerationError` instead of silently emitting uncompensated G-code. |
| **`CNC-012`** | **P2** | Sequencer stops spindle (`M5`) before retracting `Z` to clearance & lacks manual router pause | **Fixed** | [`sequencer.py`](../../../backend/app/generators/sequencer.py) retracts to `G0 Z<clearance>` **before** `M5`, and supports `manual_spindle=True` (`M0` operator prompt between tool changes). |
| **`CNC-013`** | **P1** | Tests mostly assert substring presence rather than geometric/modal validity | **Fixed** | Built [`backend/tests/gcode_validator.py`](../../../backend/tests/gcode_validator.py) (`validate_gcode_program()`) and [`backend/tests/test_defect_handoff_remediation.py`](../../../backend/tests/test_defect_handoff_remediation.py) (`20` tests). |
| **`CNC-014`** | **P3** | `README.md` truncates mid-file around line 78 | **Fixed** | Completed [`README.md`](../../../README.md) and documented `POST /api/generate/chamfering/circular` in [`docs/API_DOCUMENTATION.md`](../../API_DOCUMENTATION.md). |

---

## 2. Red-Green-Refactor & Coverage Scorecard

- **Phase 3.1 (RED)**: `20 failed in 0.16s` on unpatched baseline (`backend/tests/test_defect_handoff_remediation.py`).
- **Phase 3.2 (GREEN)**: `20 passed in 0.08s` after root-cause implementation.
- **Phase 3.3 (Full Suite Regression)**: `228 passed in 1.49s` (`100%` pass rate).

| Metric | Baseline (Pre-Plan 08) | Final (Post-Plan 08) | Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| **CNC Suite Tests Passed** | 208 | 228 | **+20** | 🟢 Ratchet Passed |
| **Statement Coverage (%)** | 87% | 87% | **0%** | 🟢 Ratchet Passed |
| **Branch Coverage (%)** | 82% | 82% | **0%** | 🟢 Ratchet Passed |
| **Domain Invariants Verified (%)** | 100.0% (5/5) | 100.0% (5/5) | **0%** | 🟢 Ratchet Passed |
| **Consolidated Workspace Tests** | 1,111 | 1,155 | **+44** | 🟢 Healthy |
