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

---

## 4. Prioritized Active Execution Queue

| Priority | Target Plan ID | Title | Target Scope | Status |
| :---: | :---: | :--- | :--- | :---: |
| **P1** | **02** | Status Page Missing UI Icons Bug Fix | Frontend SVG/glyph bundle, kiosk HUD templates | `READY_FOR_PLANNING` (from `IDEAS.md`) |
| **P2** | **03** | Manual Spindle / Router Speed G-Code Commenting Mode | Postprocessor, machine models, RPM dial comments | `READY_FOR_PLANNING` (from `IDEAS.md`) |
| **P3** | **04** | Plasma Cutter CNC Machine Support & Conversational Generator | Torch on/off M3/M5, dwell delay, kerf compensation | `READY_FOR_PLANNING` (from `IDEAS.md`) |
| **P4** | **05** | Touch Probe & Auto Z-Zeroing Routine | Conversational touch plate routine & offsets | `BACKLOG` (from `IDEAS.md`) |
