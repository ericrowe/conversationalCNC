# Conversational-CNC-Controller: Ideas & Backlog Intake

This document serves as the asynchronous repository for raw thoughts, feature requests, hardware ideas, and bug reports. Items here are reviewed during triage turns and converted into numbered formal plans.

---

## 💡 Architecture & Host Optimization Ideas

- [ ] **FluidNC / GRBL Serial Bridge Daemon**: Lightweight serial streaming edge agent that decouples real-time USB/UART machine communication from the web UI and heavy computational planners.
- [ ] **Local AI Intent Parser (Workstation Bridge Integration)**: Route conversational machine commands through Workstation `agy_bridge` or Node 02 for natural-language G-code parameter extraction.
- [ ] **Touchscreen Kiosk Mode for Workshop**: Fullscreen web interface optimized for 7" to 10" touchscreen displays with large jog and zeroing buttons.

---

## 🔧 Generator & Toolpath Enhancements

### [FEATURE] Plasma Cutter CNC Machine Support & Conversational Generator
- **Context**: Workshop operations require plasma cutting capabilities for sheet metal fabrication alongside traditional CNC routing/milling.
- **Proposed Solution**:
  - Add `plasma` machine type profile in machine configuration (nozzle size, kerf width, pierce height, pierce delay, cut height, cut feed rate, arc voltage THC parameters).
  - Implement plasma conversational generator and postprocessor emitting:
    - Torch Ignition (`M3` / `M4` / spindle or relay pin activation) with dwell (`G4 P<pierce_delay>`).
    - Torch Extinguish (`M5`) at end of cut contours.
    - Automatic lead-in (arc or straight) and lead-out paths to avoid edge divots/dross gouging on finished parts.
    - Kerf width compensation offsetting toolpaths by half nozzle kerf width.
- **Target Component**: `backend/app/generators/`, `backend/app/postprocessors/`, `backend/app/models/machine.py`, `frontend/`.
- **Priority**: High (Feature)

### [FEATURE] Manual Router Spindle Speed G-Code Commenting Mode
- **Context**: For CNC machines equipped with a manually controlled trim router (e.g. Makita RT0701C, DeWalt DWP611 with physical dial 1–6) rather than a software-controlled VFD/PWM spindle, outputting programmatic spindle speed commands (`S18000 M3`) can trigger controller warnings, invalid state errors, or operator confusion.
- **Proposed Solution**:
  - Introduce `manual_spindle` boolean or `spindle_control_type: "manual" | "vfd_analog" | "pwm_grbl"` setting in machine profiles.
  - When `manual` is selected, suppress programmatic `S<rpm>` speed words and `M3`/`M5` spindle start/stop commands in generated G-code.
  - Prominently output operator instructions in G-code header and tool-change comments (e.g. `(--- MANUAL ROUTER SETUP: Set speed dial to 3.5 / ~18,000 RPM for 1/4" Endmill in Hardwood ---)` and `(Ensure router power switch is turned ON before cycle start)`).
- **Target Component**: `backend/app/postprocessors/grbl.py`, `backend/app/models/machine.py`, `backend/app/generators/base.py`.
- **Priority**: High (Quality of Life & Machine Safety)

- [ ] **Adaptive Trochoidal Clearing**: Add trochoidal milling generator for deep slotting and pocketing in tough materials with high feeds and low radial engagement.
- [ ] **3D Surface Rastering (STL to Toolpath)**: Lightweight parallel finishing toolpath generation for 3D contoured reliefs.
- [ ] **Touch Probe / Auto Z-Zeroing Assistant**: Guided conversational routine for XYZ touch plate zeroing and tool length offset calibration.

---

## 🐛 Bug Reports & Edge Cases

### [BUG] Status Page Missing Web & Kiosk UI Icons
- **Context**: In the status page on the standalone Raspberry Pi (`voltron.local` / `:80`), several UI icons fail to render properly:
  1. The **Reload / Refresh** action icon.
  2. The icons next to the system load/telemetry parameters (the three load averages / "Lion" system metrics).
  3. The icon displayed next to the active machine selector / machine status banner.
- **Proposed Solution**:
  - Audit static asset paths in `frontend/` and `backend/app/web/templates/`.
  - Ensure all icon font files (FontAwesome / SVG glyphs) are bundled locally for 100% offline standalone kiosk operation without external CDN dependencies.
  - Verify CSS classes and markup in status page templates to ensure matching glyph references.
- **Target Component**: `frontend/`, `backend/app/web/templates/status.html`, `backend/app/web/static/`.
- **Priority**: Immediate (Quick Fix Bug)

---

## 📋 Recommended Plan Formulation Order (Queue Prioritization)

| Triage Rank | Item ID / Title | Type | Target Plan | Rationale |
| :---: | :--- | :---: | :---: | :--- |
| **1** | **Status Page Missing UI Icons Bug Fix** | Bug | **Plan 02** | Immediate UI defect fix on the newly deployed standalone kiosk with minimal blast radius. |
| **2** | **Manual Router Spindle Speed Commenting Mode** | Feature | **Plan 03** | High-leverage safety & post-processing refinement for workshop machines with manual dial routers. |
| **3** | **Plasma Cutter CNC Machine Support & Conversational Generator** | Feature | **Plan 04** | Core capability expansion establishing plasma G-code generation, kerf offsets, and pierce delay sequences. |
| **4** | **Touch Probe & Auto Z-Zeroing Routine** | Feature | **Plan 05** | Essential workflow automation for tool touch-off plates and work zero alignment. |
