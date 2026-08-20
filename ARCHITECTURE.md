Conversational CNC Controller: Architecture & Plan
1. System Overview
- Objective: A web-based, locally executing Conversational CNC Controller.
- Core Philosophy: Bridge the gap between complex CAM software and quick, on-the-fly machining.
- Host Hardware: Raspberry Pi 4 or 5.
- Target Machine: Inventables X-Carve (Arduino/gShield running Grbl).

2. Software Stack & Responsibilities
- Frontend (Flask Templates + Interactive HTML5 Canvas/JS): Acts as the UI and the "Job Coordinator". Runs directly in the unified Flask server for a zero-build-step, offline-ready Raspberry Pi setup. Provides real-time 2D toolpath visualization, conversational pattern builders (single hole, grid, bolt circle), machine profile switcher, and tool library management.
- Backend (Python + Flask): Acts as a pure, stateless generator and configuration API. It receives configuration payloads from the UI, runs deterministic calculations via pure functions, and outputs dialect-compliant raw G-Code.
- Machine & Controller Dialect Layer: Modular post-processors (Grbl, GrblHAL, FluidNC, LinuxCNC, Standard) supporting dynamic machine profile switching, soft limit boundaries, and linear motion expansions for controllers without canned cycles.
- Database (SQLite): A serverless local file handling tool libraries, material feeds/speeds presets, and MachineProfiles (e.g., configurable Z-probe thickness, soft limit boundaries).
- G-Code Sender: A decoupled local sender (e.g., CNCjs API, Watched Folder with UGS, or CLI Spooler) handles the physical streaming to the Grbl controller, ensuring the Flask backend remains unblocked.

3. Machine Configuration & Tool Drive
- Limits: The machine uses XYZ homing. Due to a lack of high-side limit switches, max travel dimensions will be saved to Grbl's EEPROM and managed via Soft Limits ($20=1).
- Tool Drive Options (Router vs Spindle): Supports manual trim routers (such as the DeWalt DWP611 with 16,000–27,000 RPM 6-speed dial) and VFD/PWM spindles. For routers, feeds and speeds automatically map to discrete dial positions (Dial 1=16k, Dial 2=18.2k, Dial 3=20.4k, Dial 4=22.6k, Dial 5=24.8k, Dial 6=27k) with minimum RPM clamping and operator setup instructions.
- G-Code Dialect: Grbl does not support canned cycles (like G83); all operations must be mathematically expanded into linear (G0, G1) or arc (G2, G3) commands by the Flask backend.
- File Strategy: The system will generate separate files for each unique tool to safely accommodate machines without automatic tool changes.

4. Development Roadmap
- Phase 1: Core Architecture & Simple Operations (Completed)
  - Unified Flask server with zero-build-step frontend for Raspberry Pi.
  - SQLite database for machine profiles, tool libraries, and material presets.
  - Straight-plunge drilling generator with single hole, grid, and bolt circle patterns.
  - Grbl & Standard controller dialect post-processors.
  - DeWalt DWP611 6-position router speed dial mapping and RPM clamping.
- Phase 2: Advanced Operations (Completed)
  - Helical Thread Milling: Internal tapped holes and external threaded studs, single-point thread mill support, climb/conventional milling, 180° semi-circular tangential helical lead-in/out, multi-pass radial roughing + spring cuts, and built-in Metric ISO & Imperial UNC/UNF standard thread catalog.
  - Peck Drilling: Deep hole chip clearing (G83 full retract) and chip breaking (G73), Grbl linear motion expansion and Standard native canned cycles.
  - Circular Pocketing & Helical Boring: Concentric expanding radial stepovers, helical ramping entry, and finish perimeter contour pass.
  - Workpiece & Spoilboard Surfacing: Bidirectional Zig-Zag and unidirectional Climb One-Way raster passes with edge overtravel clearance and corner/center datums.
  - 2D Canvas Visualizer upgraded with real-time interactive previews of circles, helical paths, concentric pocket rings, and facing rasters.
- Phase 3: Hardware integration, sender streaming, and physical validation on the X-Carve CNC.