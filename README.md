# Conversational CNC Controller

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-142%20passed-brightgreen.svg)]()
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
- **📐 2.5D Arbitrary Profile & Contour Milling**: Mill open profiles and closed perimeter cutouts along chained lines and circular arcs. Features automatic tool radius compensation (Climb/Left, Conventional/Right, or Centerline), 90° tangential circular arc or 45° linear lead-ins and lead-outs, multi-depth stepdowns with wall finishing stock allowance, and spring passes.
- **📦 Step-and-Repeat Array Nesting & Soft Jaw Fixturing Wizard**: Array multi-part production jobs across $N_x \times N_y$ rectangular grids or staggered honeycomb patterns with serpentine zig-zag rapids. Generate precision negative clamping pockets for vise soft jaws to hold irregular parts for secondary Op 2 operations with 45° corner dogbone reliefs.
- **📐 DXF 2D Vector CAD Importer & Direct-to-GCode Wizard**: Drag-and-drop standard 2D AutoCAD `.dxf` CAD drawings. Automatically parses entity geometry (`LINE`, `ARC`, `CIRCLE`, `LWPOLYLINE`), chains perimeter loops, detects bolt circle drill points, and converts directly into profile contouring and drilling toolpaths.


### 2. 3D WebGL / Isometric Backplotter & Simulation
- **Interactive 3D Toolpath Simulation**: Real-time 3D orbital canvas with pitch/yaw mouse drag, camera presets (Isometric, Top XY, Front XZ, Right YZ), prominent WCS $(0,0,0)$ Part Datum crosshair target, and auto-fit bounding box.
- **Animated Cutter Playback**: Step-by-step cutter animation along toolpaths with Play/Pause, Step Forward/Backward, progress scrubber slider, speed multipliers ($0.5\times$ to $10\times$), and live coordinates HUD ($X, Y, Z$, Feed, Step count).
- **Bi-Directional Selection Sync**: Clicking any line in the interactive G-code editor jumps the 3D cutter tool directly to that position and highlights the active motion vector in glowing yellow.

### 3. G-Code "Hints" & Live Modal State Inspector
- **Plain English Explainer**: Decodes complex G-code blocks (arcs, canned cycles, spindle start, dwell, probe touches, jog commands) into clear conversational explanations with calculated travel distances, radius, and descent angles.
- **Live Modal State Dashboard**: Real-time modal registers (`WCS`, `Plane`, `Units`, `Distance Mode`, `Motion`, `Tool`, `Spindle`, `Feed`).

### 4. G-Code Transformations & Multi-Tool Program Splitter
- **Coordinate Shift & Offsets**: Translates coordinates by $(\Delta X, \Delta Y, \Delta Z)$ for multi-fixture work setups.
- **Rotation**: Rotates toolpaths in the $XY$ plane around arbitrary pivot centers $(X_c, Y_c)$ with arc center vector ($I, J$) rotation.
- **Mirroring with Automatic Arc Reversal**: Mirrors across $X$ or $Y$ axis and automatically flips arc directions ($G2 \leftrightarrow G3$).
- **Feed & Speed Override Adjuster**: Global percentage scaling for feed rates and spindle speeds.
- **Multi-Tool Program Splitter**: Extracts multi-tool jobs (`M6 T...`) into individual standalone `.nc` programs per tool with safe retracts and footers.

### 5. Physics-Based Feeds & Speeds Engine
- **Radial Chip Thinning Compensation**: Automatically boosts feed rate for shallow stepovers ($< 50\%$ tool diameter) to prevent cutter rubbing and premature tool wear.
- **Material Removal Rate (MRR) & Spindle Power**: Calculates volume removal rate ($\text{cm}^3/\text{min}$) and estimates required spindle cutting power (kW/HP) across woods, plastics, brass, and aluminum.
- **Deflection Warning Advisor**: Flags high tool stickout ratios ($> 4.5\times$ diameter) and power overloads for hobby trim routers (e.g. DeWalt DWP611).

### 6. Machine Probing & WCS Zeroing Assistant
- **Z-Touch Plate Probing Generator**: 2-stage (fast search + slow fine touch) probing macros (`G38.2` $\to$ `G10 L20 P1 Z...`) referencing the active machine's saved plate thickness.
- **Corner XYZ Touch Block Generator**: 3-axis corner probe calculating tool radius and block lip offsets to calibrate $(X0, Y0, Z0)$ simultaneously in `G54`.
- **Machine Homing (`$H`) & Safety Header `G54`**: Ensures work coordinates are locked to the workpiece datum on every program.

### 7. Manual Jog Controller & Live DRO Panel
- **Interactive Directional Jog Pad**: 8-way $XY$ directional jog buttons, $+Z/-Z$ column, discrete micro-step selectors (`0.01mm` to `100mm`), and feed rate slider.
- **Global Keyboard Hotkeys**: Arrow keys for $XY$, PageUp/PageDown for $Z$, `Shift` for rapid speed, and `J` key to summon pendant anywhere.
- **Quick-Zero & Origin Return**: 1-click zeroing for $X0, Y0, Z0$ or $XYZ$ all (`G10 L20 P1`), plus safe return to part origin (`G0 Z<retract>` $\to$ `G0 X0 Y0`).
- **Live Digital Readout (DRO)**: Real-time high-visibility coordinates display and manual spindle on/off toggle.

### 8. Multi-Operation Job Program Sequencer & Builder
- **Complete Part Machining Assembler**: Queue multiple conversational operations (facing $\to$ pocketing $\to$ drilling $\to$ contouring $\to$ chamfering $\to$ engraving $\to$ soft jaws) into a single cohesive `.nc` job file.
- **Intelligent Tool Change Optimization**: Tracks active tools and eliminates redundant tool changes when consecutive operations share the same tool.
- **Safe Inter-Op Retracts & Coordinate Continuity**: Enforces safe Z-retracts and G54 coordinate continuity throughout the entire job run.
- **Slide-Over Job Builder Drawer**: Reorder operations with up/down controls, group by tool, preview combined toolpaths, and export full `.nc` programs with 1-click.







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
│   └── tests/               # 142 automated pytest unit and integration tests
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
Verify that all 142 tests pass on your machine:
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

## 🧪 Physical Machine Integration & Commissioning Test Plan

A step-by-step progressive-risk commissioning guide and test reversion protocol for bringing up physical CNC machines is available in:
👉 [docs/MACHINE_INTEGRATION_TEST_PLAN.md](docs/MACHINE_INTEGRATION_TEST_PLAN.md)

---

## 🧪 Running Automated Tests


```bash
# Run all unit and integration tests
PYTHONPATH=backend pytest backend/tests

# Run with coverage report
PYTHONPATH=backend pytest backend/tests --cov=backend/app
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
