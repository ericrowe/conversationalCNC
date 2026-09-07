# Conversational-CNC-Controller: Ideas & Backlog Intake

This document serves as the asynchronous repository for raw thoughts, feature requests, hardware ideas, and bug reports. Items here are reviewed during triage turns and converted into numbered formal plans.

---

## 💡 Architecture & Host Optimization Ideas
- [ ] **FluidNC / GRBL Serial Bridge Daemon**: Lightweight serial streaming edge agent that decouples real-time USB/UART machine communication from the web UI and heavy computational planners.
- [ ] **Local AI Intent Parser (Workstation Bridge Integration)**: Route conversational machine commands through Workstation `agy_bridge` or Node 02 for natural-language G-code parameter extraction.
- [ ] **Touchscreen Kiosk Mode for Workshop**: Fullscreen web interface optimized for 7" to 10" touchscreen displays with large jog and zeroing buttons.

---

## 🔧 Generator & Toolpath Enhancements
- [ ] **Adaptive Trochoidal Clearing**: Add trochoidal milling generator for deep slotting and pocketing in tough materials with high feeds and low radial engagement.
- [ ] **3D Surface Rastering (STL to Toolpath)**: Lightweight parallel finishing toolpath generation for 3D contoured reliefs.
- [ ] **Touch Probe / Auto Z-Zeroing Assistant**: Guided conversational routine for XYZ touch plate zeroing and tool length offset calibration.

---

## 🐛 Bug Reports & Edge Cases
- *(None currently open)*
