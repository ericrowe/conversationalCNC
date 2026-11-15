# Instructions for `Conversational-CNC-Controller/docs/plans`

## 1. Directory Structure Conventions
- **`docs/plans/`**: Active plans currently in planning or execution for Conversational-CNC-Controller.
- **`docs/plans/complete/`**: Archived completed plans and walkthroughs (`YYYY-MM-DD-<plan_name>.md`).
- **`docs/plans/IDEAS.md`**: Asynchronous idea, feature, and bug backlog.

---

## 2. Plan Lifecycle Standard

Every plan MUST adhere to the standardized 5-step lifecycle and include all 7 mandatory sections:
1. `# Plan NN: <Title>` (Two-digit zero-padded sequential number registered below).
2. `## 1. Goal Description`
3. `## 2. Architecture & Workflow Diagram (Mermaid)`
4. `## 3. Code Modifications ([NEW], [MODIFY], [DELETE])`
5. `## 4. Test Updates & Specifications` (Unit/integration test methods, baseline regression matrices, and Red-Green bug reproduction tests)
6. `## 5. Documentation Updates`
7. `## 6. Verification Plan (Automated + Manual)`

### Test-First & Red-Green Regression Gating Standard:
- **Phase 3.1: Pre-Code Test Harness (RED / Baseline)**: Establish automated baseline tests verifying that existing behaviors work before making changes. For bug fixes, write a failing reproduction test demonstrating the reported issue (RED). Run `./run_tests.sh` to confirm baseline passes and bug test fails.
- **Phase 3.2: Minimal Blast Radius Implementation (GREEN)**: Implement root-cause code modifications and documentation updates. Run `./run_tests.sh` to confirm the reproduction test passes cleanly (GREEN).
- **Phase 3.3: Full Regression Retest & Coverage Verification**: Run the entire hermetic test suite (`./run_tests.sh`). All tests must pass (100% pass rate) with zero regressions.

---

## 3. Subsystem Plan Registry

| Plan ID | Title | Scope | Status |
| :---: | :--- | :--- | :---: |
| **01** | Standalone Barn Workshop Raspberry Pi Deployment & Server Status Host ([`docs/plans/complete/2026-09-07-01_barn_standalone_pi_deployment_plan.md`](complete/2026-09-07-01_barn_standalone_pi_deployment_plan.md)) | Provisioning, Port 80, 7" Touchscreen Kiosk, Web Serial, System Telemetry | `ARCHIVED` |
| **02** | Status Page Missing UI Icons Bug Fix ([`docs/plans/complete/2026-09-08-02_status_page_missing_ui_icons_plan.md`](complete/2026-09-08-02_status_page_missing_ui_icons_plan.md)) | Frontend SVG/glyph bundle, kiosk HUD templates | `ARCHIVED` |
| **03** | Manual Spindle / Router Speed G-Code Commenting Mode ([`docs/plans/complete/2026-09-08-03_manual_spindle_speed_gcode_commenting_plan.md`](complete/2026-09-08-03_manual_spindle_speed_gcode_commenting_plan.md)) | Postprocessor, machine models, RPM dial comments | `ARCHIVED` |
| **04** | Plasma Cutter CNC Machine Support & Conversational Generator ([`docs/plans/04_plasma_cutter_cnc_conversational_support_plan.md`](04_plasma_cutter_cnc_conversational_support_plan.md)) | Torch on/off M3/M5, dwell delay, kerf compensation | `QUEUED` |
| **05** | XYZ Corner Touch Plate & Auto Edge-Finder Probing Routine ([`docs/plans/complete/2026-09-08-05_xyz_touch_plate_and_edge_finder_probing_plan.md`](complete/2026-09-08-05_xyz_touch_plate_and_edge_finder_probing_plan.md)) | G38.2 probing macros, corner offsets, kiosk UI | `ARCHIVED` |
| **06** | Tool Life & Wear Tracking Ledger ([`docs/plans/06_tool_life_and_wear_tracking_ledger_plan.md`](06_tool_life_and_wear_tracking_ledger_plan.md)) | Tool definitions, caddy slot tracking, wear alerts | `ON HOLD` |
| **07** | Hardened Host Power Operations & Localhost Touchscreen Access Control ([`docs/plans/complete/2026-09-14-07_hardened_host_power_operations_and_access_control_plan.md`](complete/2026-09-14-07_hardened_host_power_operations_and_access_control_plan.md)) | Localhost IP gating, scoped sudoers whitelist, error observability | `ARCHIVED` |
| **08** | Defect Remediation, Circular Chamfering & Independent G-Code Validation Suite (`CNC-001`–`CNC-014`) ([`docs/plans/complete/2026-11-05-08_defect_remediation_and_gcode_validation_plan.md`](complete/2026-11-05-08_defect_remediation_and_gcode_validation_plan.md)) | Contour/lead-in math, sequencer safety, circular chamfer, G-code validator | `ARCHIVED` |
| **09** | Remediation Handoff v2.0 — Dependency-Safe Sequencing, MachiningContext Propagation, Envelope Contract & Swept Geometry Verification (`R2-001`–`V2-006`) ([`docs/plans/complete/2026-11-05-09_remediation_handoff_v2_and_swept_geometry_verification_plan.md`](complete/2026-11-05-09_remediation_handoff_v2_and_swept_geometry_verification_plan.md)) | DAG sequencing, MachiningContext, tri-state WorkEnvelope, swept-tool contour & chamfer verification | `ARCHIVED` |
| **10** | Workshop CNC Software Feature Exerciser, Bit-Saver Checklist & Printable 2-Page PDF ([`docs/plans/complete/2026-11-05-10_workshop_commissioning_checklist_and_printable_pdf_plan.md`](complete/2026-11-05-10_workshop_commissioning_checklist_and_printable_pdf_plan.md)) | Updated feature/bit-saver checklist (`MACHINE_INTEGRATION_TEST_PLAN.md`) & printable 2-page PDF (`Workshop_CNC_Commissioning_Checklist.pdf`) | `ARCHIVED` |
| **11** | Standardized CNC Controller Box Interface, Pinout Specification & X-Carve Arduino Enclosure ([`docs/plans/11_standardized_cnc_controller_interface_and_xcarve_enclosure_plan.md`](11_standardized_cnc_controller_interface_and_xcarve_enclosure_plan.md)) | Universal GX16 pinout standard, dual-switched 24V/5V power architecture, requirements (`CNC_CONTROLLER_INTERFACE_REQUIREMENTS.md`), and X-Carve controller box CAD | `IN_PROGRESS` |
| **12** | Direct Universal Gcode Sender (UGS) Integration — 1-Click Auto-Load & Optional Auto-Send ([`docs/plans/12_direct_ugs_integration_autoload_and_autosend_plan.md`](12_direct_ugs_integration_autoload_and_autosend_plan.md)) | Direct UGS Pendant REST API / file bridge pushing generated G-code from web UI into UGS with auto-load and optional auto-send | `PROPOSED` |
| **13** | Adaptive Trochoidal Clearing for Slotting & Pocketing ([`docs/plans/13_adaptive_trochoidal_clearing_slotting_and_pocketing_plan.md`](13_adaptive_trochoidal_clearing_slotting_and_pocketing_plan.md)) | Deterministic `G2`/`G3` trochoidal peel-milling loop generator for low-chatter slotting/pocketing in brass, aluminum & hardwood | `PROPOSED` |

---

## 4. Prioritized Active Execution Queue

| Priority | Plan ID | Title | Target Scope | Status |
| :---: | :---: | :--- | :--- | :---: |
| **P0** | **12** | Direct Universal Gcode Sender (UGS) Integration — 1-Click Auto-Load & Optional Auto-Send ([`docs/plans/12_direct_ugs_integration_autoload_and_autosend_plan.md`](12_direct_ugs_integration_autoload_and_autosend_plan.md)) | Direct G-code push to UGS with auto-load & optional auto-send | `PROPOSED` |
| **P0** | **13** | Adaptive Trochoidal Clearing for Slotting & Pocketing ([`docs/plans/13_adaptive_trochoidal_clearing_slotting_and_pocketing_plan.md`](13_adaptive_trochoidal_clearing_slotting_and_pocketing_plan.md)) | Deterministic `G2`/`G3` trochoidal slotting & pocketing | `PROPOSED` |
| **P1** | **11** | Standardized CNC Controller Box Interface, Pinout Specification & X-Carve Arduino Enclosure ([`docs/plans/11_standardized_cnc_controller_interface_and_xcarve_enclosure_plan.md`](11_standardized_cnc_controller_interface_and_xcarve_enclosure_plan.md)) | Phase 1 Requirements & Shop Part Intake Complete; awaiting shop part measurements for Phase 2 Enclosure CAD | `IN_PROGRESS` |
| **P2** | **04** | Plasma Cutter CNC Machine Support & Conversational Generator ([`docs/plans/04_plasma_cutter_cnc_conversational_support_plan.md`](04_plasma_cutter_cnc_conversational_support_plan.md)) | Torch control, dwell & kerf offset | `QUEUED` |

### On-Hold Queue:
1. **`06`**: **Tool Life & Wear Tracking Ledger** ([`docs/plans/06_tool_life_and_wear_tracking_ledger_plan.md`](06_tool_life_and_wear_tracking_ledger_plan.md)) *(On Hold pending future revisit)*

