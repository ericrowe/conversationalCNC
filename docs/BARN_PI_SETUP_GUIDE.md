# Barn Workshop Server Setup Guide (Raspberry Pi 4 + 7" Touchscreen)

This runbook guides the physical setup, operating system provisioning, and operational configuration of the **Barn Workshop Server (`voltron.local`)** running the Conversational CNC Controller.

---

## 1. Hardware Bill of Materials (BOM)

| Component | Specification | Notes |
| :--- | :--- | :--- |
| **SBC Host** | Raspberry Pi 4 Model B (4 GB RAM) | 64-bit quad-core ARM Cortex-A72 @ 1.5 GHz. |
| **Touchscreen Display** | Official Raspberry Pi 7" DSI Touchscreen | Native 800×480 resolution, `ft5x06` capacitive multi-touch controller. |
| **Storage** | 64 GB SanDisk Extreme MicroSD | High-endurance Class 10 A2 card. |
| **Power Supply** | Official 15W USB-C Power Adapter (5.1V / 3.0A) | Clean power isolation for workshop environments. |
| **Enclosure** | 7" Touchscreen Enclosure Case | Mountable near workbench or rack mounting plate. |

---

## 2. Operating System & Initial Setup

1. **Flash MicroSD with Raspberry Pi Imager**:
   - **Device**: `Raspberry Pi 4`
   - **Operating System**: `Raspberry Pi OS (64-bit) with Desktop` (Debian Bookworm)
   - **Customization (Gear Icon)**:
     - Hostname: `voltron` (resolves as `voltron.local` and `voltron.lan`)
     - Username: `detour`
     - Password: Set secure password
     - Wi-Fi: Configure workshop 2.4/5GHz SSID & Password
     - Services: Check **Enable SSH** (load public SSH key)
2. **First Boot & Verification**:
   - Connect DSI ribbon cable to Raspberry Pi DSI connector.
   - Insert MicroSD and connect USB-C power.
   - Test SSH reachability from your workstation:
     ```bash
     ssh detour@voltron.local
     ```

---

## 3. Application Deployment & Service Provisioning

Run the turnkey deployment script from your workstation:

```bash
cd Conversational-CNC-Controller

# Preview deployment
./deploy.sh --dry-run

# Live deployment to voltron.local
./deploy.sh
```

The deployment script automatically:
1. Synchronizes application files to `/opt/conversational-cnc`.
2. Creates the Python 3 virtual environment (`.venv/`) and installs dependencies.
3. Grants `cap_net_bind_service` to allow non-root execution on standard default HTTP **port 80**.
4. Installs and enables `conversational-cnc.service`.
5. Configures 7" touchscreen kiosk display at `http://127.0.0.1/status`.

---

## 4. 7" Touchscreen Status Dashboard

Once booted, the 7" touchscreen displays the real-time server telemetry HUD:
- **Core Temp**: Live SoC temperature with color safety alerts (<60°C Normal, 60–75°C Warm, >75°C Hot).
- **CPU & Memory**: Real-time load and RAM consumption bars.
- **MicroSD Disk**: Free storage space and utilization.
- **Multi-CNC Hub**: Summary of all configured machine profiles in the workshop.
- **Live Activity Feed**: Real-time event log showing whenever workshop tablets/laptops generate toolpaths.
- **Touch Controls**: 1-touch buttons for manual snapshot backup, service restart, and profile navigation.

---

## 5. Client Machine Connection (Web Serial)

To control physical CNC machines in the barn:
1. Power on your workshop laptop or tablet.
2. Open Chrome, Edge, or Opera and navigate to `http://voltron.local/` (or `http://<pi-ip>/`).
3. Connect your CNC machine's USB cable directly to the **client laptop/tablet**.
4. Select the active machine profile from the header.
5. Generate conversational operations (Pockets, Surfacing, Drilling, Engraving, DXF).
6. Click **Connect Machine** to stream directly via Web Serial, or download the `.nc` file for external sender software.
