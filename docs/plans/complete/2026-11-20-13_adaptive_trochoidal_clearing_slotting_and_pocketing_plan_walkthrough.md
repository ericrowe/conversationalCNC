# Walkthrough: Plan 13 — Adaptive Trochoidal Clearing for Slotting & Pocketing

**Date**: 2026-11-20  
**Plan**: [`2026-11-20-13_adaptive_trochoidal_clearing_slotting_and_pocketing_plan.md`](./2026-11-20-13_adaptive_trochoidal_clearing_slotting_and_pocketing_plan.md)  
**Status**: `ARCHIVED` (Deployed to `voltron.local` & User-Validated)

---

## 1. Implemented Changes

1. **Trochoidal Slotting & Arc-Slot Support**:
   - [`backend/app/schemas/slotting_schema.py`](../../../backend/app/schemas/slotting_schema.py) & [`backend/app/schemas/__init__.py`](../../../backend/app/schemas/__init__.py): Added `cutting_strategy` (`"conventional" | "trochoidal"`) and `trochoidal_stepover_pct` (`5.0..40.0`) to `LinearSlotPayloadSchema`, and added `ArcSlotPayloadSchema`.
   - [`backend/app/generators/slotting.py`](../../../backend/app/generators/slotting.py) & [`backend/app/generators/__init__.py`](../../../backend/app/generators/__init__.py): Added shared `emit_linear_trochoidal_pass()`, updated `generate_linear_slot()` with trochoidal clearing (helical/linear Z-ramp entry, `G3` climb-milling loops with inward centerline retracts, 4-decimal `I/J` precision from rounded start, `< 0.001 mm` chord skip, CCW `G3` cleanup pass, and `WorkEnvelope.validate_bounds`), and implemented `generate_arc_slot()` with outer-wall angular pitch scaling.
   - [`backend/app/generators/sequencer.py`](../../../backend/app/generators/sequencer.py): Registered `"arc_slot": generate_arc_slot` in `GENERATOR_MAP`.
2. **Rectangular Pocket Trochoidal Core Entry**:
   - [`backend/app/schemas/pocket_schema.py`](../../../backend/app/schemas/pocket_schema.py): Added `trochoidal_entry` and `trochoidal_stepover_pct` (`5.0..40.0`) to `RectangularPocketPayloadSchema`.
   - [`backend/app/generators/rectangular_pocket.py`](../../../backend/app/generators/rectangular_pocket.py): Integrated `emit_linear_trochoidal_pass()` for central spine opening (supporting horizontal, vertical `width_y > length_x`, square, and narrow pockets) before concentric outward roughing rings.
3. **REST API & Pocketing Web UI**:
   - [`backend/app/api/generate.py`](../../../backend/app/api/generate.py): Forwarded trochoidal parameters in `generate_linear_slot_gcode()` and `generate_rectangular_pocket_gcode()`, and added `POST /api/generate/slotting/arc` (`generate_arc_slot_gcode()`).
   - [`backend/app/templates/operations/rectangular_pocket.html`](../../../backend/app/templates/operations/rectangular_pocket.html) & [`backend/app/static/js/rectangular_pocket.js`](../../../backend/app/static/js/rectangular_pocket.js): Added **Trochoidal Core Entry (Low-Chatter Mode)** and **Trochoidal Stepover (%)** controls for both direct generation and Job Builder queueing (hidden in `boss` mode).
4. **Independent Swept-Containment Oracle & Tests**:
   - [`backend/tests/gcode_validator.py`](../../../backend/tests/gcode_validator.py): Added `verify_swept_slot_containment()` and `verify_swept_pocket_containment()`.
   - [`backend/tests/test_generators/test_trochoidal_clearing.py`](../../../backend/tests/test_generators/test_trochoidal_clearing.py): Added 6 comprehensive tests covering linear/arc trochoidal slotting, API `tool_id` HTTP `400` validation, pocket orientations, `sequencer.py` composition, and conventional backward compatibility.
5. **Documentation**:
   - [`docs/MACHINE_INTEGRATION_TEST_PLAN.md`](../../MACHINE_INTEGRATION_TEST_PLAN.md): Added verification item `3.10` for brass/aluminum trochoidal slotting and pocket core entry.

---

## 2. Verification & Coverage Scorecard

- **CNC Test Suite (`./Conversational-CNC-Controller/run_tests.sh`)**: **295 passed** in `2.01s` (0 failed).
- **Statement Coverage (`./scripts/measure_coverage.sh`)**: **89%** across `Conversational-CNC-Controller` (295 tests passing; Workspace total: 1389 tests passing).
- **Behavioral Invariant Coverage (`python3 scripts/evaluate_behavior_coverage.py`)**: **5/5 invariants (100.0%)** across 43 test files in `Conversational-CNC-Controller` (Workspace total: 25/26, 96.2%).
- **Live Deployment & Manual Verification**: Deployed via `./deploy.sh` to `voltron.local` (`HTTP 200` on `/` and `trochoidalEntry` live on `/rectangular-pocket`); user confirmed UI and toolpath behavior.
