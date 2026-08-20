# Conversational CNC Controller

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-80%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A web-based, locally executing **Conversational CNC Controller** designed for rapid, on-the-fly machining without launching heavyweight CAD/CAM software. Built with a zero-build-step architecture optimized for offline Raspberry Pi 4/5 setups and desktop workstations driving Grbl-based CNCs (such as the Inventables X-Carve, Shapeoko, PrintNC) and standard CNC controllers.

---

## 📸 Key Features & Supported Operations

### 1. Conversational Machining Operations
- **⚡ Straight Plunge Drilling**: Single holes, rectangular grids, pitch bolt circles (PCD), and custom coordinate lists with customizable retract planes, approach clearances, and bottom dwells.
- **🔩 Peck Drilling (Deep Hole)**: Chip clearing (`G83` full retract to safe Z) and chip breaking (`G73` lift) cycles, mathematically expanded into linear moves for Grbl controllers without native canned cycles.
- **🧵 Helical Thread Milling**: 3D helical interpolation for internal tapped holes and external threaded studs. Supports single-point thread mills, climb/conventional milling, 180° semi-circular tangential helical lead-in/lead-out arcs, and multi-pass radial stepovers (roughing passes + spring passes). Includes a built-in catalog of standard Metric ISO (M2–M20), Imperial UNC (#2-56 to 3/4-10), and Imperial UNF (#10-32 to 1/2-20) threads.
- **⭕ Circular Pocketing & Helical Boring**: Precision bearing bores, counterbores, and circular pockets with helical ramp entry, expanding concentric radial stepovers, and clean wall finishing passes.
- **🔲 Rectangular Pocket & Raised Boss / Island Machining**: Rectangular cavities with corner fillets, helical ramp entry, wall finishing passes, and outside clearing around raised rectangular island features.
- **📐 Linear Slotting & Keyways**: Centerline and wide slot cutting with multiple depth passes, safe stepdowns, and side profile passes.
- **✨ 2D Chamfering & Edge Breaking**: Outer and inner perimeter chamfering and deburring with conical V-bits and chamfer mills, calculating exact tip-offset and Z-depth.
- **🪚 Workpiece & Spoilboard Surfacing / Facing**: Flatten rough stock or resurface spoilboards with bidirectional Zig-Zag or unidirectional Climb One-Way raster passes, customizable cutter overtravel past edges, and corner/center datum origins.
- **✍️ Single-Line Vector Text Engraving**: High-speed CNC text engraving supporting multi-line rotated linear layouts and curved circular arc layouts (clockwise/counter-clockwise). Features 5 single-line stroke font styles (*Simplex Sans, Duplex Bold Sans, Roman Serif, Cursive Script, Industrial Block*), configurable cubic Catmull-Rom spline curve interpolation smoothing ($1\times$ to $12\times$ sampling) with sharp-corner preservation, and live tool tip flat cut width calculation.


### 2. Machine & Tool Management
- **Router Speed Dial Mapping**: Automatic mapping of spindle speeds to discrete speed dial numbers for manual trim routers (e.g. DeWalt DWP611 Dial 1=16k, Dial 2=18.2k, Dial 3=20.4k, Dial 4=22.6k, Dial 5=24.8k, Dial 6=27k) with operator setup alerts and minimum RPM clamping. Supports continuous VFD / PWM spindles as well.
- **Tool Library & Material Presets**: SQLite-backed database storing tool dimensions, flutes, and material feeds/speeds presets across woods, plastics, brass, and aluminum.
- **Dynamic Machine Profiles**: Switch between active machine profiles with distinct work envelopes, max feed limits, touch probe plate thicknesses, and controller dialects (`grbl`, `standard`).
- **Interactive 2D Canvas & Vector Toolpath Visualizer**: Real-time toolpath rendering with pan, mouse-wheel zoom, fit-to-view, machine soft limit boundaries, true single-line cutting feeds (`G1` in solid cyan with stroke width scaling), rapid traverse paths (`G0` in dashed pink/red), plunge entry points (green), retract lift points (amber), and direct G-code program backplot simulation.
- **Instant Export**: Live G-code syntax viewer with one-click clipboard copy and `.nc` file download.


---

## 🏗️ Architecture & Philosophy

```
┌───────────────────────────────────────────────────────────┐
│       Zero-Build Frontend (HTML5 Canvas + Vanilla JS)      │
│  - Instant offline loading on Raspberry Pi touchscreen    │
│  - Live 2D interactive preview & conversational inputs    │
└─────────────────────────────▲─────────────────────────────┘
                              │ JSON REST API
┌─────────────────────────────▼─────────────────────────────┐
│                 Flask Application Backend                 │
│  - Stateless G-code generation orchestration              │
│  - SQLite storage (Machines, Tools, Material Presets)     │
└─────────────────────────────▲─────────────────────────────┘
                              │
       ┌──────────────────────┴──────────────────────┐
       ▼                                             ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│   Pure Python Generators    │       │   Post-Processor Dialects   │
│  - Pure math & geometry     │       │  - Grbl (Linear expansions) │
│  - Runtime estimation       │       │  - LinuxCNC / Standard      │
│  - Soft limit verification  │       │  - Helical 3D Arc (G2/G3)   │
└─────────────────────────────┘       └─────────────────────────────┘
```

1. **Stateless Generator Functions** (`backend/app/generators/`): Pure Python functions with zero database or web framework dependencies, ensuring deterministic, 100% testable G-code output.
2. **Modular Post-Processor Layer** (`backend/app/postprocessors/`): Abstract base class adapting code generation to target controller dialects (expanding cycles to linear moves on Grbl, using native canned cycles on LinuxCNC).
3. **Zero-Build Frontend**: Built with server-rendered Jinja2 templates, semantic HTML5, CSS variables, and modern vanilla JavaScript. No Node.js, Webpack, or npm build steps required on the Raspberry Pi.

---

## 📁 Repository Structure

```
conversationalCNC/
├── ARCHITECTURE.md          # System architecture and design specification
├── LICENSE                  # MIT License
├── README.md                # Project overview and deployment guide
├── run.py                   # Root application entrypoint
├── backend/
│   ├── run.py               # Backend direct entrypoint
│   ├── requirements.txt     # Python package dependencies
│   ├── seed.py              # Database seeding script (tools, machines, presets)
│   ├── app/
│   │   ├── __init__.py      # Flask application factory
│   │   ├── config.py        # Configuration classes
│   │   ├── api/             # REST API blueprints (generate, machines, tools, materials)
│   │   ├── generators/      # Pure mathematical G-code generators
│   │   ├── models/          # SQLAlchemy SQLite database models
│   │   ├── postprocessors/  # Motion controller dialect post-processors
│   │   ├── schemas/         # Pydantic request validation schemas
│   │   ├── static/          # CSS stylesheets and client JavaScript modules
│   │   ├── templates/       # Jinja2 HTML templates
│   │   └── web/             # Web frontend routing blueprint
│   └── tests/               # 80 automated pytest unit and integration tests
└── docs/
    └── API_DOCUMENTATION.md # Comprehensive REST API reference
```

---

## 🚀 Clean Machine Installation Guide

### Prerequisites
- **Operating System**: Linux (Raspberry Pi OS, Ubuntu, Debian), macOS, or Windows
- **Python**: Python 3.10 or higher
- **Git**: Installed and configured

### Step 1: Clone the Repository
```bash
git clone https://github.com/ericrowe/conversationalCNC.git
cd conversationalCNC
```

### Step 2: Create and Activate a Virtual Environment
```bash
python3 -m venv backend/venv

# On Linux / macOS:
source backend/venv/bin/activate

# On Windows (Command Prompt):
backend\venv\Scripts\activate.bat

# On Windows (PowerShell):
backend\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Step 4: Seed the Database
Populate the local SQLite database with default machine profiles (X-Carve, Shapeoko), tool libraries (endmills, drills, V-bits, thread mills, surfacing flycutters), and material feeds/speeds presets:
```bash
PYTHONPATH=backend python backend/seed.py
```

### Step 5: Run Automated Tests
Verify that all 80 tests pass on your machine:
```bash
PYTHONPATH=backend pytest backend/tests -v
```



### Step 6: Start the Development Server
```bash
python run.py
```
Open your browser and navigate to:
👉 **`http://localhost:5001`** (or `http://<your-pi-ip>:5001`)

---

## 🖥️ Production Deployment (Raspberry Pi / Linux)

To run the Conversational CNC Controller continuously on a dedicated Raspberry Pi machine controller that boots on startup:

### 1. Install Production WSGI Server (Gunicorn)
Activate your virtual environment and install `gunicorn`:
```bash
source backend/venv/bin/activate
pip install gunicorn
```

### 2. Configure Systemd Service
Create a systemd service file:
```bash
sudo nano /etc/systemd/system/conversational-cnc.service
```

Paste the following configuration (adjust paths and user as appropriate):
```ini
[Unit]
Description=Conversational CNC Controller Web Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/conversationalCNC
Environment="PATH=/home/pi/conversationalCNC/backend/venv/bin"
Environment="PYTHONPATH=/home/pi/conversationalCNC/backend"
ExecStart=/home/pi/conversationalCNC/backend/venv/bin/gunicorn --bind 0.0.0.0:5001 --workers 2 "run:app"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable conversational-cnc
sudo systemctl start conversational-cnc
sudo systemctl status conversational-cnc
```

### 4. (Optional) Auto-Launch Touchscreen Kiosk on Raspberry Pi
If using the official Raspberry Pi Touchscreen or HDMI monitor in the workshop:
1. Edit Wayland/X11 autostart:
   ```bash
   mkdir -p ~/.config/autostart
   nano ~/.config/autostart/cnc-kiosk.desktop
   ```
2. Paste the kiosk launcher:
   ```ini
   [Desktop Entry]
   Type=Application
   Name=CNC Controller Kiosk
   Exec=chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:5001
   X-GNOME-Autostart-enabled=true
   ```

---

## 📡 CNC Machine & Sender Integration

The Conversational CNC Controller outputs dialect-standard `.nc` / `.gcode` files. You can execute jobs on your machine via:

1. **Universal Gcode Sender (UGS) / Watched Folder**:
   - Set the UGS Watched Folder directory to your browser's default download folder. Downloaded `.nc` files are automatically queued for execution.
2. **CNCjs API / Web UI**:
   - CNCjs can run alongside this controller on the same Raspberry Pi. Upload generated G-code directly via the CNCjs REST API or web interface.
3. **Physical Controller Setup**:
   - **X-Carve / Grbl**: Enable soft limits (`$20=1`) after homing (`$H`). The controller automatically verifies all generated toolpaths against your configured envelope.

---

## 📚 REST API Reference

Comprehensive documentation for all generation, machine profile, tool library, and material preset endpoints is available in:
👉 [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

---

## 🧪 Running Tests

```bash
# Run all unit and integration tests
PYTHONPATH=backend pytest backend/tests

# Run with coverage report
PYTHONPATH=backend pytest backend/tests --cov=backend/app
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
