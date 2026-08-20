# 🧪 Machine Integration & Physical Commissioning Test Plan

A systematic, progressive-risk commissioning framework for bringing up a new or modified CNC machine (Grbl, Smoothieboard, FluidNC, LinuxCNC) with the **Conversational CNC Controller**.

---

## 🎯 Objectives & Philosophy

1. **Progressive Risk Escalation (Envelope Expansion)**:
   $$\text{Static Electrical/Safety} \longrightarrow \text{Dry Air (Spindle OFF)} \longrightarrow \text{Air Run (Spindle ON / EMI Check)} \longrightarrow \text{Soft Foam/MDF Test} \longrightarrow \text{Target Material}$$
2. **Time-Efficient Validation**: Targeted verification steps designed to achieve 100% operational confidence in under 90 minutes.
3. **Deterministic Reversion & Regression Protocol**: A formal impact-matrix detailing exactly which test tiers must be re-run when software or firmware patches are applied.

---

## 📋 Commissioning Matrix Overview

| Phase | Description | Machine State | Risk Level | Target Time |
|---|---|---|---|---|
| **Phase 0** | Static Safety & Electrical Lockout | Motors OFF / Spindle UNPLUGGED | Zero Risk | 10 min |
| **Phase 1** | Axis Polarities, Motion Scale & Homing | Motors ON / Spindle UNPLUGGED | Very Low | 15 min |
| **Phase 2** | Probing, Tool Setting & WCS (`G54`) | Motors ON / Spindle UNPLUGGED | Low | 15 min |
| **Phase 3** | Full Conversational Air Verification | Motors ON / Spindle UNPLUGGED | Low | 20 min |
| **Phase 4** | Spindle Control & EMI Immunity | Motors ON / Spindle ON (No Cut) | Medium | 10 min |
| **Phase 5** | Soft Medium First Cuts (Foam/MDF) | Cutting Test Workpiece | Medium | 15 min |
| **Phase 6** | Production Hard Material Validation | Full Load Machining | Standard | 10 min |

---

## 🛡️ Phase 0: Static Safety & Electrical Lockout

> **Safety Rule:** Disconnect physical mains power from the spindle/router. Wear eye protection.

### Steps:
- [ ] **0.1 Physical E-Stop Trip Test**: Press the Emergency Stop button. Verify all motor power drops instantly and the controller enters alarm mode (`[MSG:Reset to continue]` or alarm code).
- [ ] **0.2 Controller Communication**: Connect via USB / Web. Send `?` or `$G`. Verify instant bidirectional telemetry and response.
- [ ] **0.3 Multimeter Continuity on Touch Plate**:
  - Connect probe clip to collet and touch plate to multimeter (continuity mode).
  - Tap plate to endmill: Multimeter must beep cleanly without intermittent resistance.
- [ ] **0.4 Mechanical Clearances**: Hand-jog carriage (steppers disabled) across the full travel envelope ($X_{\max}, Y_{\max}, Z_{\max}$). Verify cable chains, vacuum hoses, and wiring do not bind or snag.

---

## 🧭 Phase 1: Axis Polarities, Motion Scale & Homing

### Steps:
- [ ] **1.1 Axis Motion Directions (Right-Hand Rule)**:
  - Command `G91 G0 X+10 F500`: Spindle carriage MUST move **Right**.
  - Command `G91 G0 Y+10 F500`: Gantry MUST move **Back / Away from operator**.
  - Command `G91 G0 Z+10 F300`: Z-axis MUST move **Up (away from bed)**.
  - *If any axis moves inverted: Invert direction pins in controller (`$3` in Grbl, `direction_pin` in Smoothieware).*
- [ ] **1.2 Limit Switch State Verification**:
  - Manually trigger $X, Y, Z$ limit switches by hand while observing status (`?` in Grbl).
  - Verify switches report `Pn:XYZ` when depressed and clear when released.
- [ ] **1.3 Homing Cycle (`$H` / `G28`)**:
  - Jog tool to center table at safe height.
  - Run **🎯 Probe & Zero $\rightarrow$ Homing Sequence (`$H`)**.
  - Verify Z lifts first to hit $Z_{\max}$ switch, retracts, then $X$ and $Y$ seek limits simultaneously.
  - Verify pull-off distance ($1\text{mm}$–$3\text{mm}$) leaves switches untriggered.
- [ ] **1.4 Distance Calibration (100mm Test)**:
  - Mount dial indicator or position precision ruler along X-axis.
  - Command `G91 G0 X100 F1000`.
  - Measure actual travel: Must equal $100.00\text{mm} \pm 0.1\text{mm}$.
  - Repeat for Y-axis and Z-axis ($50.00\text{mm}$ on Z).

---

## 🎯 Phase 2: Probing, Tool Setting & Work Coordinate Systems (`G54`)

### Steps:
- [ ] **2.1 Dry Touch Plate Trigger (Air Test)**:
  - Attach alligator clip to tool collet. Hold touch plate in hand $10\text{mm}$ below tool bit.
  - Run **🎯 Probe & Zero $\rightarrow$ Z-Touch Plate Macro**.
  - While tool is feeding downward at $150\text{mm/min}$, tap plate against tool bit in mid-air.
  - Verify tool halts instantly, lifts $1.5\text{mm}$, executes slow $25\text{mm/min}$ fine touch, sets `G10 L20 P1 Z<thickness>`, and lifts to safe clearance ($20\text{mm}$).
- [ ] **2.2 Workpiece Z-Zero Calibration**:
  - Place touch plate on top of scrap MDF stock.
  - Run **Z-Touch Plate Macro**.
  - Upon completion, command `G90 G0 Z0.000` (slowly at $F100$).
  - Perform paper/feeler gauge test: A sheet of paper ($0.1\text{mm}$) should slide with slight friction between the tool tip and stock surface.
- [ ] **2.3 Corner XYZ Block Calibration**:
  - Position touch block on bottom-left corner of stock.
  - Run **Corner XYZ Macro**.
  - Verify 3-axis probing sequence (Z top $\rightarrow$ X outside edge with cutter radius compensation $\rightarrow$ Y outside edge).
  - Command `G90 G0 X0.000 Y0.000 Z5.000`. Verify tool tip centers directly over the physical stock corner.
- [ ] **2.4 Coordinate Persistence Across Soft Reset**:
  - Issue soft reset (`Ctrl-X` / `$X`). Re-query coordinate system (`$#` or `$G`).
  - Verify `G54` non-volatile memory retained calibrated offsets.

---

## ⚡ Phase 3: Conversational CNC Motion Verification (Air Cuts, Spindle OFF)

Generate test programs from Conversational CNC UI with workpiece origin set to $Z=0$ ($20\text{mm}$ above bed):

### Test 3.1: Straight Plunge & Deep Peck Drilling
- **Parameters**: 4-hole grid, $5.0\text{mm}$ retract, $1.0\text{mm}$ clearance, $10.0\text{mm}$ depth, $2.0\text{s}$ bottom dwell.
- **Verification**:
  - Visualizer and tool match exact hole coordinates.
  - Peck cycle lifts to retract plane (full retract) or chip break lift without axis binding.
  - Spindle dwells at hole bottom for exactly $2.0\text{s}$.

### Test 3.2: Helical Thread Milling & Circular Pocketing
- **Parameters**: Internal M10 thread and 30mm bearing pocket with helical ramp entry.
- **Verification**:
  - Smooth $G2/G3$ helical interpolation with continuous Z descent.
  - No stuttering, jerky motor steps, or buffer underrun pauses during continuous arc moves.
  - Tangential 180° semi-circular lead-in and lead-out arcs execute cleanly.

### Test 3.3: Workpiece Surfacing (Facing)
- **Parameters**: $100\text{mm} \times 100\text{mm}$, Zig-Zag raster, $10.0\text{mm}$ stepover, $10.0\text{mm}$ cutter overtravel.
- **Verification**:
  - Toolpath passes over stock boundaries by exactly the overtravel distance without exceeding table limits.
  - Reversal arc / stepover rapid moves clear stock edges cleanly.

### Test 3.4: Single-Line Vector Text Engraving
- **Parameters**: Multi-line text `"CNC 2026"` with Catmull-Rom spline smoothing ($4\times$).
- **Verification**:
  - Tool lifts rapidly to safe Z between distinct character strokes.
  - Spline curve moves stream with smooth motion velocity profile.

---

## 🌪️ Phase 4: Spindle Integration & EMI Noise Baseline

> **Objective**: Verify that high-frequency electromagnetic interference (EMI) from the router/spindle motor brushes or VFD inverter does not corrupt USB serial communication or trigger false limit switch interrupts.

### Steps:
- [ ] **4.1 Spindle Start/Stop Verification**:
  - Reconnect spindle power.
  - Issue `M3 S16000` (or turn on router dial). Verify spindle spins clockwise smoothly.
  - Issue `M5`. Verify spindle comes to a full stop.
- [ ] **4.2 EMI Loaded Dry Run**:
  - Mount cutter bit. Keep $Z$ origin elevated $30\text{mm}$ in the air above stock.
  - Turn on spindle and dust collection vacuum.
  - Run a 10-minute surfacing or pocketing toolpath.
  - **Pass Criteria**: Zero USB disconnects, zero false limit switch interrupts (`Hard limit triggered`), zero lost steps.

---

## 🪵 Phase 5: Soft Medium First Cuts (Dimensional & Geometry Certification)

Mount a piece of high-density foam, machinable wax, or scrap MDF.

```
+-------------------------------------------------------------+
|                      50.0 mm                                |
|          +-----------------------------+                    |
|          |                             |                    |
|          |    +-------------------+    |                    |
|          |    |   30.0 mm Bore    |    |  50.0 mm           |
|          |    |      (Pocket)     |    |                    |
|          |    +-------------------+    |                    |
|          |                             |                    |
|          +-----------------------------+                    |
|                                                             |
|   (Hole 1)                                      (Hole 2)    |
|      (O)---------------- 80.0 mm ----------------(O)        |
+-------------------------------------------------------------+
```

### Steps & Measurements:
- [ ] **5.1 50mm Square Boss (Diagonal Squareness Check)**:
  - Cut $50.0\text{mm} \times 50.0\text{mm}$ outer square.
  - Measure side $X$: Must equal $50.00\text{mm} \pm 0.08\text{mm}$.
  - Measure side $Y$: Must equal $50.00\text{mm} \pm 0.08\text{mm}$.
  - Measure diagonals $D_1, D_2$: Must equal $70.71\text{mm}$ and $|D_1 - D_2| \le 0.05\text{mm}$ (Gantry orthogonality check).
- [ ] **5.2 30mm Circular Bearing Bore (Circularity & Backlash)**:
  - Machine 30.0mm circular pocket.
  - Measure diameter at 0°, 45°, 90°, 135° with bore gauge/calipers.
  - Out-of-round error must be $< 0.04\text{mm}$.
- [ ] **5.3 2-Hole Center-to-Center Pitch**:
  - Drill 2 holes spaced 80.0mm apart along X.
  - Measure center distance: Must equal $80.00\text{mm} \pm 0.05\text{mm}$.
- [ ] **5.4 Surface Flatness (Spindle Tram Check)**:
  - Surface a $60\text{mm} \times 60\text{mm}$ patch with $12\text{mm}$ stepover.
  - Run fingernail across raster ridges: Surface must feel smooth with no ridging steps ($< 0.02\text{mm}$ scallop indicating nod/tilt).

---

## 🔄 Test Reversion & Regression Protocol

When a test fails and a software patch, post-processor fix, or firmware update is applied, follow this **Impact-Radius Reversion Matrix** to determine which test tiers must be invalidated and re-executed.

```mermaid
flowchart TD
    Bug[Bug Detected & Software Patch Applied] --> Impact{Determine Patch Impact Level}
    
    Impact -->|Level 1: UI / Visualizer Only| L1[Tier 1: Browser Refresh & Pytest]
    Impact -->|Level 2: Generator Math / Operations| L2[Tier 2: Phase 3 Air Cut + Phase 5 Soft Cut]
    Impact -->|Level 3: Probing / Coordinates / WCS| L3[Tier 3: Phase 2 Probing + Phase 5 Alignment]
    Impact -->|Level 4: Post-Processor / Safety Header| L4[Tier 4: Phase 1 Motion + Phase 3 Air Cut]
    Impact -->|Level 5: Hardware / Stepper / Wiring| L5[Tier 5: Full Re-Commissioning Phase 0 -> 6]

    L1 --> ReCert[Issue Re-Certification Sign-off]
    L2 --> ReCert
    L3 --> ReCert
    L4 --> ReCert
    L5 --> ReCert
```

### Impact-Radius Reversion Matrix

| Patch Category | Code Components Affected | Invalidation Scope | Mandatory Re-Execution Steps |
|---|---|---|---|
| **Level 1: UI / Display Only** | `visualizer.js`, `gcode_inspector.js`, CSS, templates | Zero machine risk | 1. Run automated test suite (`pytest`)<br>2. Hard-refresh browser (`Ctrl-F5`). |
| **Level 2: Specific Operation Math** | `app/generators/<op>.py` (e.g. `thread_milling.py`, `engraving.py`) | Affected operation only | 1. Run `pytest`<br>2. Run **Phase 3 Air Cut** for that specific operation<br>3. Run **Phase 5 Soft Cut** for that specific operation. |
| **Level 3: Probing & Coordinate Systems** | `probing.py`, `probing.js`, `G10 L20`, `G38.2` | Work coordinate offsets & Z-zero | 1. Run `pytest`<br>2. Re-run **Phase 2 (All probing steps 2.1–2.4)**<br>3. Re-verify touch plate thickness & gauge clearance. |
| **Level 4: Post-Processor & Safety Headers** | `postprocessors/grbl.py`, `registry.py`, headers/footers | All machine operations | 1. Run `pytest`<br>2. Re-run **Phase 3 (Air verification 3.1–3.4)** across drilling, milling, surfacing. |
| **Level 5: Physical Hardware / Microstepping / Firmware** | Stepper drivers, belts, lead screws, `config.txt`, Grbl `$$` | Full machine calibration | 1. **Complete Re-Commissioning**: Execute **Phase 0 through Phase 6** in sequence. |

---

## 📝 Commissioning Sign-Off Record

```
Machine Name: ___________________________________
Controller Model: [  ] Grbl v1.1   [  ] Smoothieboard v1   [  ] Other: ___________
Operator / Lead: ________________________________
Date Commissioned: ______________________________

Phase 0: Safety & Lockout Checked:       [  ] PASS  Initials: _____
Phase 1: Motion Scale & Homing:          [  ] PASS  Initials: _____
Phase 2: Probing & WCS Calibration:      [  ] PASS  Initials: _____
Phase 3: Conversational Air Cuts:        [  ] PASS  Initials: _____
Phase 4: Spindle & EMI Noise Immunity:   [  ] PASS  Initials: _____
Phase 5: Dimensional Cut Certification:  [  ] PASS  Initials: _____
Phase 6: Production Material Validated:  [  ] PASS  Initials: _____

Final Controller/Machine Certification:  [  ] 100% FLIGHT READY
```
