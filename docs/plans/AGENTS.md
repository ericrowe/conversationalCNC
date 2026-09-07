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
5. `## 4. Test Updates & Specifications`
6. `## 5. Documentation Updates`
7. `## 6. Verification Plan (Automated + Manual)`

---

## 3. Subsystem Plan Registry

| Plan ID | Title | Scope | Status |
| :---: | :--- | :--- | :---: |
| **01** | Standalone Barn Workshop Raspberry Pi Deployment & Offline Motion Host ([`docs/plans/01_barn_standalone_pi_deployment_plan.md`](01_barn_standalone_pi_deployment_plan.md)) | Provisioning, udev rules, Kiosk, Offline SQLite | `READY_FOR_PLANNING` |

---

## 4. Prioritized Active Execution Queue

| Priority | Plan ID | Title | Target Scope | Status |
| :---: | :---: | :--- | :--- | :---: |
| **P0** | **01** | Standalone Barn Workshop Raspberry Pi Deployment & Offline Motion Host ([`docs/plans/01_barn_standalone_pi_deployment_plan.md`](01_barn_standalone_pi_deployment_plan.md)) | Barn Host, udev, Offline Engine | `READY_FOR_PLANNING` |
