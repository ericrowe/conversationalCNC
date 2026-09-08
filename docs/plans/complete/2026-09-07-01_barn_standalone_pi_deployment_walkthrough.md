# Plan 01 Walkthrough: Standalone Barn Workshop Raspberry Pi Deployment & Server Status Host

**Plan ID**: Plan 01 (Child Sub-Plan of Macro Plan M12)  
**Completion Date**: 2026-09-07  
**Subproject**: `Conversational-CNC-Controller`  
**Target Hardware**: Raspberry Pi 4 (`voltron.local`, IP `192.168.0.72`, user `detour`) + 7" Official DSI Touchscreen (800×480)

---

## 1. Overview of Delivered Scope

Plan 01 implemented a standalone, turnkey deployment of the **Conversational CNC Controller** on `voltron.local`:
1. **Port 80 Default Ingress & Kiosk Mode**: Configured systemd service unit `conversational-cnc.service` with Linux capability `AmbientCapabilities=CAP_NET_BIND_SERVICE` and labwc Wayland kiosk autostarting Chromium at `http://127.0.0.1/status`.
2. **Voltron 1980s Retro-Futuristic HUD**: Custom dark retro-futuristic theme with beveled metallic chrome-to-gold `VOLTRON` logo, 5-Lion speed stripe, color-coded Lion telemetry gauges (Red, Blue, Yellow, Green Lions), Blazing Sword Studio action launcher, and compact header typography preventing horizontal overflow on 800px displays.
3. **Multi-CNC Machine Catalog & Live Activity Stream**: Verified machine work dimensions (X-Carve: 750×750×65 mm, Shapeoko Pro: 838×838×95 mm) and top-justified real-time streaming feed displaying client IP, machine profile badge, and machining operation.
4. **Consolidated System Menu & Hardware Controls**: Consolidated `[ ☰ Menu ]` drawer providing navigation to Studio, Fullscreen toggle, Snapshot backup trigger, Service restart (`/api/system/restart`), Hardware reboot (`/api/system/reboot`), and Hardware shutdown (`/api/system/shutdown`).
5. **Decoupled Multi-CNC Web Serial Streaming**: Browser-native Web Serial API module (`web_serial.js`) allowing workshop client laptops/tablets to stream G-code directly to physical CNC machinery via USB without cabling the Pi 4 host.
6. **Turnkey Open-Source Tooling**: Single-command `quick_install.sh`, bare-metal `scripts/bootstrap_node.sh`, and modular `scripts/backup_cnc.sh` with local snapshot rotation and opportunistic Node 04 (`pi-backup.local`) sync.

---

## 2. Test Verification & Invariants

```
🧪 Running Conversational-CNC-Controller tests with: .../.venv/bin/python
============================= test session starts ==============================
collected 183 items

backend/tests/test_api/test_calculator_api.py ..                         [  1%]
backend/tests/test_api/test_circular_boss_api.py ..                      [  2%]
backend/tests/test_api/test_contouring_api.py ..                         [  3%]
backend/tests/test_api/test_dxf_api.py ...                               [  4%]
backend/tests/test_api/test_generate_api.py .......                      [  8%]
backend/tests/test_api/test_jog_api.py ....                              [ 10%]
backend/tests/test_api/test_machines_api.py .....                        [ 13%]
backend/tests/test_api/test_mesh_api.py .....                            [ 16%]
backend/tests/test_api/test_nesting_api.py ...                           [ 18%]
backend/tests/test_api/test_phase2_generate_api.py ............          [ 24%]
backend/tests/test_api/test_probing_api.py ...                           [ 26%]
backend/tests/test_api/test_sequencer_api.py .                           [ 26%]
backend/tests/test_api/test_svg_api.py ....                              [ 28%]
backend/tests/test_api/test_system_api.py .......                        [ 32%]
backend/tests/test_api/test_tools_materials_api.py ...                   [ 34%]
backend/tests/test_api/test_transform_api.py .....                       [ 37%]
backend/tests/test_generators/test_circular_pocket.py ......             [ 40%]
backend/tests/test_generators/test_contouring.py .....                   [ 43%]
backend/tests/test_generators/test_drilling.py .........                 [ 48%]
backend/tests/test_generators/test_dxf_importer.py ...                   [ 49%]
backend/tests/test_generators/test_engraving.py ........                 [ 54%]
backend/tests/test_generators/test_feeds_speeds.py .....                 [ 56%]
backend/tests/test_generators/test_jog.py .......                        [ 60%]
backend/tests/test_generators/test_mesh_leveling.py .........            [ 65%]
backend/tests/test_generators/test_nesting.py ....                       [ 67%]
backend/tests/test_generators/test_peck_drilling.py ...                  [ 69%]
backend/tests/test_generators/test_probing.py ....                       [ 71%]
backend/tests/test_generators/test_rectangular_pocket.py .....           [ 74%]
backend/tests/test_generators/test_sequencer.py ...                      [ 75%]
backend/tests/test_generators/test_slotting_chamfering.py .....          [ 78%]
backend/tests/test_generators/test_surfacing.py ..                       [ 79%]
backend/tests/test_generators/test_svg_importer.py .....                 [ 82%]
backend/tests/test_generators/test_thread_milling.py .....               [ 85%]
backend/tests/test_generators/test_transformations.py .....              [ 87%]
backend/tests/test_postprocessors/test_grbl.py .....                     [ 90%]
backend/tests/test_web/test_status_routes.py ..                          [ 91%]
backend/tests/test_web/test_web_routes.py ...............                [100%]

============================= 183 passed in 1.63s ==============================
```

- **Pass Rate**: 183 / 183 tests passing (100%).
- **Statement Coverage**: 87% (Total statements covered: 4,498 / 5,379).
- **Hermetic Mocks**: Socket network probes and system shutdown/reboot execution mocked in unit testing mode.
