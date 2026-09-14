# Walkthrough: Plan 07 — Hardened Host Power Operations & Localhost Touchscreen Access Control

## 1. Overview & Objectives
Plan 07 resolved the silent failure of the "Shutdown Pi" button on `voltron.local` (Node 12) and eliminated the unauthenticated LAN Denial of Service attack surface by gating power endpoints to localhost, implementing robust error logging, provisioning a least-privilege scoped sudoers drop-in, and configuring Chromium with `--password-store=basic` to prevent GNOME Keyring modal blocks on boot.

---

## 2. Changes Made

### A. Access Control & Observability in Backend API
- **File**: `Conversational-CNC-Controller/backend/app/api/system.py`
- Implemented `verify_power_access(req)` to restrict `/api/system/shutdown`, `/api/system/reboot`, and `/api/system/restart` to requests from `127.0.0.1` / `::1` (the 7" screen kiosk).
- Added support for an optional `X-Admin-Pin` header matching `ADMIN_PIN` for authorized remote administration.
- Refactored asynchronous background threads to log subprocess return codes, stdout, and stderr with `current_app.logger.error()`, eliminating silent failure swallowing.

### B. Turnkey Sudoers Drop-In & Kiosk Autostart
- **Files**: `Conversational-CNC-Controller/quick_install.sh`, `Conversational-CNC-Controller/scripts/install_sudoers.sh`
- Added configuration of `/etc/sudoers.d/020_conversational_cnc` with `0440` permissions, whitelisting exclusively `/sbin/poweroff`, `/sbin/reboot`, and `systemctl restart conversational-cnc.service` without a password.
- Added `--password-store=basic --ozone-platform=wayland` to `cnc-kiosk.desktop` autostart template to prevent locked GNOME Keyring prompts on boot.

### C. Documentation & Security Architecture
- **File**: `Conversational-CNC-Controller/docs/BARN_PI_SETUP_GUIDE.md`
- Added Section 6 documenting the defense-in-depth access model for host power controls.

---

## 3. Test Verification & Coverage Scorecard

### Test Results
- **Pre-Code (RED)**: Verified 4 test failures when unauthenticated remote requests were made to power endpoints.
- **Post-Code (GREEN)**: All 208 unit and integration tests passed cleanly in `1.70s`.

| Metric | Target | Final Value | Status |
| :--- | :---: | :---: | :---: |
| **Test Pass Rate** | 100% | 100% (208/208 passed) | ✅ PASSED |
| **Remote 403 Rejection** | 100% | 100% verified via curl | ✅ PASSED |
| **Localhost Kiosk Access** | Allowed | Verified (HTTP 200) | ✅ PASSED |
| **Security & Hygiene Audit** | 0 violations | 0 violations (1088 files scanned) | ✅ PASSED |

---

## 4. Live Environment Verification
1. **Remote Ingress Verification**:
   ```bash
   curl -i -X POST http://voltron.local/api/system/shutdown
   # Returned HTTP/1.1 403 Forbidden ("Host power operations are restricted to the local touchscreen console.")
   ```
2. **Kiosk Session Clean Startup**:
   - Re-launched Chromium on `voltron` with `--password-store=basic --ozone-platform=wayland`.
   - Verified that the locked keyring prompt was dismissed and the 7" display renders the Conversational CNC Status HUD cleanly.
