# Conversational CNC Controller: Standalone Quickstart Guide

The **Conversational CNC Controller** is a lightweight, zero-build-step, open-source workshop machining platform designed to run 100% locally on any Raspberry Pi, mini-PC, or Linux workstation.

---

## 1. Quick Install (1-Step Setup)

On any Debian, Ubuntu, or Raspberry Pi OS host:

```bash
# Clone the repository
git clone https://github.com/<your-org>/Conversational-CNC-Controller.git
cd Conversational-CNC-Controller

# Run turnkey installer (binds to default port 80)
sudo ./quick_install.sh
```

### Installation Options
- **Default Headless Install (Port 80)**:
  ```bash
  sudo ./quick_install.sh
  ```
- **With 7" Touchscreen Kiosk Autostart**:
  ```bash
  sudo ./quick_install.sh --kiosk
  ```
- **Custom Non-Privileged Port (e.g. 5000)**:
  ```bash
  ./quick_install.sh --port 5000 --no-service
  ```
- **Preview Install (Dry-Run)**:
  ```bash
  ./quick_install.sh --dry-run
  ```

---

## 2. Accessing the Application

Once installed, the application is available to all devices on your local network:
- **Machining Studio**: `http://<server-ip>/` or `http://voltron.local/`
- **Real-Time Server Status HUD**: `http://<server-ip>/status`
- **Machine Profile Manager**: `http://<server-ip>/machines`
- **Tool Library & Presets**: `http://<server-ip>/tools`

---

## 3. Multi-CNC Client Streaming Architecture

The Conversational CNC Controller uses a **decoupled streaming architecture**:
1. **Pi Server**: Central hub generating mathematically verified G-code toolpaths, hosting the tool library, and storing machine profiles.
2. **Client Browser (Web Serial API)**: The workshop operator opens the web UI on a laptop, tablet, or PC connected to their physical CNC machine.
3. **1-Click Streaming**: Clicking "Connect Machine" in Chrome/Edge/Opera connects the browser directly to the CNC via USB serial (115200 / 250000 baud) with real-time DRO, jog buttons, and streaming progress.

---

## 4. Automated Daily Backups

The installer configures an automated daily atomic SQLite snapshot (`VACUUM INTO`):
- **Local Storage**: Retained in `/var/backups/conversational_cnc/` (7-day rolling retention).
- **Server Rack Integration (Optional)**: If a home lab server rack vault (`pi-backup.lan`) is present on the network, snapshots are automatically synchronized to Node 04.

To trigger a manual snapshot at any time:
```bash
./scripts/backup_cnc.sh
```
Or click **Backup Snapshot** directly on the `/status` dashboard.
