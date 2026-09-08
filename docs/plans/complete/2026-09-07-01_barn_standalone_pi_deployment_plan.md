# Plan 01: Standalone Barn Workshop Raspberry Pi Deployment & Server Status Host

## 1. Goal Description
Establish a **100% self-contained, open-source-ready standalone deployment** of the **Conversational CNC Controller** on a dedicated Raspberry Pi 4 (`voltron.local`, user `detour`) running on standard default HTTP **port 80** (`http://voltron.local/` / `http://<ip>/`), with an optional attached **7" touchscreen** providing real-time server status telemetry as a value-add, while enabling a **decoupled multi-CNC client streaming architecture** (via browser Web Serial API) and modular auto-detecting backup sync to Node 04 (`pi-backup.lan`).

### Core Objectives:
1. **Self-Contained Open-Source Standalone Application (`quick_install.sh`)**:
   - Deliver a single-step standalone installer script (`quick_install.sh`) for any Linux/Raspberry Pi environment.
   - Binds to standard default HTTP **port 80** (`http://voltron.local/`), eliminating port suffix requirements.
   - Zero hardcoded dependencies on external server rack infrastructure.
2. **Headless Baseline with Optional 7" Touchscreen Server Status Kiosk**:
   - Backend functions 100% headlessly over the network.
   - When a 7" display is connected, an optional kiosk service launches Chromium in fullscreen displaying `/status` with live hardware gauges (CPU %, Temp °C, RAM, Disk), active machine profiles, live client job feed, and touch management controls.
3. **Decoupled Multi-CNC Client Streaming (Web Serial API)**:
   - The Pi 4 server is **not** cabled to CNCs; it serves as the centralized G-code math, tool/material library, and profile hub.
   - Workshop client devices (tablets/laptops) connect to their respective CNC machines and stream G-code via browser **Web Serial API** (`web_serial.js`) or external senders.
4. **Modular Rack Infrastructure Auto-Detection (`scripts/backup_cnc.sh`)**:
   - Creates atomic SQLite `VACUUM INTO` snapshots locally.
   - Auto-detects if Node 04 (`pi-backup.lan`) is reachable and syncs snapshots via Restic; falls back to local snapshot rotation if offline.

---

## 2. Architecture & Workflow Diagram

```mermaid
flowchart TD
    subgraph StandaloneServer["Open-Source Standalone CNC Server (voltron: Pi 4B 64-bit)"]
        subgraph CoreEngine["Core Application Layer (Port 80 / 5000)"]
            FlaskEngine["Flask Backend Engine & REST APIs<br/>(/api/generate, /api/machines, /api/system)"]
            LocalDB[("Local SQLite Database<br/>(Multi-Machine Profiles, Tools, Materials)")]
            Generators["Stateless Deterministic G-Code Generators<br/>(Drilling, Pockets, Surfacing, Engraving, DXF, SVG)"]
            SystemAPI["System Telemetry & Health API<br/>(/api/system/status)"]
        end

        subgraph BackupLayer["Modular Backup Subsystem (scripts/backup_cnc.sh)"]
            LocalSnap["Local Atomic SQLite Snapshot<br/>(/var/backups/conversational_cnc/)"]
            AutoDetect{"Probe Rack Host<br/>(pi-backup.lan)?"}
        end

        subgraph OptionalKiosk["Optional 7\" Touchscreen Display (Value-Add)"]
            KioskUI["Full-Screen Server Status Dashboard<br/>• CPU/Temp/RAM/Disk HUD<br/>• Host IP / Network Status<br/>• Live Client Job Feed<br/>• Multi-CNC Catalog Summary<br/>• Touch Power/Restart Controls"]
        end

        FlaskEngine <--> LocalDB
        FlaskEngine <--> Generators
        FlaskEngine <--> SystemAPI
        SystemAPI -.->|"Optional Local Display"| KioskUI
        BackupLayer -.-> LocalDB
        LocalDB --> LocalSnap
        LocalSnap --> AutoDetect
    end

    subgraph OptionalRack["Optional Server Rack Infrastructure (When Present)"]
        Node04["Node 04: pi-backup.lan<br/>Central Restic Backup Vault"]
        Node02["Node 02: tasker-pi.lan<br/>Daily Executive Briefing Health Rollup"]
    end

    subgraph WorkshopClients["Workshop Web Client Hosts (Multi-CNC Control)"]
        Client1["Client A: Laptop / Tablet<br/>Browser @ http://voltron.local<br/>Profile: WorkBee 1510 Router"]
        Client2["Client B: Shop PC / Tablet<br/>Browser @ http://voltron.local<br/>Profile: Shapeoko Pro Mill"]
        Client3["Client C: Mobile / Tablet<br/>Browser @ http://voltron.local<br/>Profile: Barn Laser Engraver"]
    end

    subgraph PhysicalCNCs["Physical Workshop CNC Machinery (Connected to Clients)"]
        CNC1["CNC Router (Grbl / FluidNC)<br/>[Connected to Client A via USB / WebSerial]"]
        CNC2["CNC Mill (Grbl / LinuxCNC)<br/>[Connected to Client B via USB / WebSerial]"]
        CNC3["Laser Cutter (GRBL-Laser)<br/>[Connected to Client C via USB / WebSerial]"]
    end

    %% Web Client interactions
    StandaloneServer <== "Local Network (HTTP :80 / :5000)" ==> Client1
    StandaloneServer <== "Local Network (HTTP :80 / :5000)" ==> Client2
    StandaloneServer <== "Local Network (HTTP :80 / :5000)" ==> Client3

    %% Client direct streaming to physical machines
    Client1 <== "Web Serial API / USB Cable" ==> CNC1
    Client2 <== "Web Serial API / USB Cable" ==> CNC2
    Client3 <== "Web Serial API / USB Cable" ==> CNC3

    %% Modular Rack Synchronization (Auto-Detected)
    AutoDetect -.->|"Yes (Rack Available)"| Node04
    AutoDetect -.->|"No (Standalone Mode)"| LocalSnap
    Node02 -.->|"Optional Health Poll"| SystemAPI
```

---

## 3. Code Modifications

### 1. Provisioning & Operational Scripts (`Conversational-CNC-Controller/`)
- **`[NEW]`** `quick_install.sh`: Standalone turnkey installer script with default port 80 and optional `--kiosk`.
- **`[NEW]`** `scripts/bootstrap_node.sh`: Turnkey provisioning script for `voltron.local` (`detour`).
- **`[NEW]`** `scripts/backup_cnc.sh`: Atomic SQLite backup script with local rotation and opportunistic Restic sync to Node 04.

### 2. Subsystem Application & UI Updates
- **`[NEW]`** `backend/app/api/system.py`: System telemetry API (`GET /api/system/status`, `POST /api/system/backup`, `POST /api/system/restart`).
- **`[NEW]`** `backend/app/templates/status.html`: Touch-optimized 7" real-time status dashboard.
- **`[NEW]`** `backend/app/static/js/status.js`: Real-time client polling script for `/status`.
- **`[NEW]`** `backend/app/static/js/web_serial.js`: Client-side Web Serial API streaming module.
- **`[MODIFY]`** [`backend/app/__init__.py`](../../backend/app/__init__.py): Register `system_bp`.
- **`[MODIFY]`** [`backend/app/web/routes.py`](../../backend/app/web/routes.py): Add `/status` and `/kiosk` routes.
- **`[MODIFY]`** [`backend/app/templates/base.html`](../../backend/app/templates/base.html): Add navigation link to `/status` and Web Serial indicator.
- **`[MODIFY]`** [`run.py`](../../run.py): Support default port 80.
- **`[MODIFY]`** [`deploy.sh`](../../deploy.sh): Update default target host to `detour@voltron.local`.

### 3. Documentation (`Conversational-CNC-Controller/docs/`)
- **`[NEW]`** [`docs/QUICKSTART_GUIDE.md`](../../docs/QUICKSTART_GUIDE.md): Open-source quickstart guide.
- **`[NEW]`** [`docs/BARN_PI_SETUP_GUIDE.md`](../../docs/BARN_PI_SETUP_GUIDE.md): Hardware setup and 7" touchscreen mounting runbook.

---

## 4. Test Updates & Specifications

### 1. Subsystem Hermetic Tests
- **`[NEW]`** `backend/tests/test_api/test_system_api.py`:
  - `test_system_status_endpoint()`: Validate `/api/system/status` JSON response structure.
  - `test_system_activity_recording()`: Verify job generation updates live activity log.
  - `test_system_backup_endpoint()`: Verify atomic snapshot and offline handling.
- **`[NEW]`** `backend/tests/test_web/test_status_routes.py`:
  - `test_status_page_renders()`: Validate `/status` and `/kiosk` templates return HTTP 200.

---

## 5. Documentation Updates

- [`docs/QUICKSTART_GUIDE.md`](../../docs/QUICKSTART_GUIDE.md): Standalone setup runbook.
- [`docs/BARN_PI_SETUP_GUIDE.md`](../../docs/BARN_PI_SETUP_GUIDE.md): Hardware mounting and touchscreen guide.
- [`docs/plans/AGENTS.md`](../AGENTS.md): Update Plan 01 status to `ARCHIVED`.

---

## 6. Verification Plan

### Automated Tests
1. Run local subsystem tests:
   ```bash
   cd Conversational-CNC-Controller && ./run_tests.sh
   ```
2. Verify deployment script in dry-run mode:
   ```bash
   ./deploy.sh --dry-run
   ```
3. Run master workspace test suite:
   ```bash
   ./scripts/run_all_tests.sh
   ```

### Manual Verification
1. Review `/status` dashboard in browser.
2. Deploy to `detour@voltron.local` and verify live operation on port 80 and 7" touchscreen.
