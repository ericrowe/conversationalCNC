# 📖 Conversational CNC — Operator & User Manual
*Fast, Parametric, Zero-CAD 2.5D CAM Programming & Machine Control for Desktop and Industrial CNC Routers and Mills.*

---

## Table of Contents
1. [Introduction & Interface Architecture](#1-introduction--interface-architecture)
2. [Multi-Operation Job Builder & Dashboard](#2-multi-operation-job-builder--dashboard)
3. [Standard 2.5D Milling Operations](#3-standard-25d-milling-operations)
   - [3.1 Workpiece & Spoilboard Surfacing](#31-workpiece--spoilboard-surfacing)
   - [3.2 Circular & Rectangular Pocketing / Bosses](#32-circular--rectangular-pocketing--bosses)
   - [3.3 2.5D Contouring with Holding Tabs & Lead-Ins](#33-25d-contouring-with-holding-tabs--lead-ins)
   - [3.4 Straight & Peck Drilling Cycles](#34-straight--peck-drilling-cycles)
   - [3.5 Slotting & Edge Chamfering](#35-slotting--edge-chamfering)
   - [3.6 Single-Point Helical Thread Milling](#36-single-point-helical-thread-milling)
4. [Vector CAD Importers (DXF & SVG with Grayscale Depth)](#4-vector-cad-importers-dxf--svg)
5. [Single-Line Text Engraving & Hershey Typography](#5-single-line-text-engraving--hershey-typography)
6. [Nesting & Custom Soft Jaw Fixturing](#6-nesting--custom-soft-jaw-fixturing)
7. [Probing, Homing & Work Coordinate Systems (WCS)](#7-probing-homing--work-coordinate-systems-wcs)
8. [Feeds, Speeds & Machine Rigidity Guide](#8-feeds-speeds--machine-rigidity-guide)
9. [3D WebGL Toolpath Backplotter & Simulation Scrubber](#9-3d-webgl-toolpath-backplotter--simulation-scrubber)

---

## 1. Introduction & Interface Architecture

**Conversational CNC** is a shop-floor-ready, browser-based CAM system designed to eliminate the friction of launching heavy CAD/CAM suites for everyday machining tasks. Whether facing a spoilboard, cutting a pocket, engraving serialized text, profiling brackets with holding tabs, or importing vector artwork, Conversational CNC generates clean, dialect-optimized G-code in seconds.

### Unified 2-Column Interface
All operational windows in Conversational CNC adhere to a strictly unified, responsive 2-column layout:
- **Left Column (Parameters & Tooling)**: Numbered, self-explanatory card groups for workpiece dimensions, cut depths, tool selection, material presets, and router speed dial settings.
- **Right Column (Visualizer & Inspector)**: Interactive 3D WebGL backplotter with real-time toolpath simulation scrubber, DRO modal state bar, quick metrics (cutting time, bounding envelope, total path length), and an interactive G-code inspector.

---

## 2. Multi-Operation Job Builder & Dashboard

The **Dashboard** serves as the central command post for machine configuration, tool library management, and multi-operation job sequencing.

![Conversational CNC Multi-Operation Job Builder Drawer](images/real_dashboard_job_builder.png)

### Key Features:
1. **Machine Profile Switcher**: Select between Grbl, LinuxCNC, RepRap/Marlin, and Haas/Fanuc dialects. Automatically sets soft travel limits, rapid rates, and spindle start dwell timers.
2. **Multi-Op Job Queue**: Queue multiple distinct operations (e.g., *Surfacing $\to$ Pocketing $\to$ Contouring $\to$ Chamfering*). Reorder via drag-and-drop or one-click buttons.
3. **Automated Tool Change Management**: The sequencer analyzes tool transitions and automatically injects dialect-specific `M6` tool change routines, spindle stop/restart commands, and safe Z retracts between operations.
4. **Unified G-Code Export**: Export the entire sequenced project into a single production `.nc` file.

---

## 3. Standard 2.5D Milling Operations

### 3.1 Workpiece & Spoilboard Surfacing
- **Purpose**: Rapidly flatten uneven stock or resurface MDF spoilboards using wide flycutters or standard endmills.
- **Strategies**: 
  - **Zig-Zag (Bidirectional)**: Fastest removal rate with smooth continuous corner transitions.
  - **One-Way Climb**: Tool lifts and rapids back to cut solely in climb direction, providing superior surface finishes on figure-grained hardwoods and plastics.
- **Belt-Drive Optimization**: Default stepover is set to **50%** (12.7mm on a 1" flycutter) with shallow 0.35mm passes to prevent belt stretch and gantry shudder.

![Workpiece & Spoilboard Surfacing Toolpath View](images/real_surfacing.png)

---

### 3.2 Circular & Rectangular Pocketing / Bosses
Pocketing clears internal cavities while boss milling machines the exterior perimeter leaving raised islands.

![Rectangular Pocketing & 3D Backplotter Preview](images/real_rectangular_pocket.png)

#### Pocketing Parameters:
- **Helical Ramp Entry**: Eliminates high axial plunge forces by ramping down at a user-defined angle (default **2.5°**) in a smooth continuous spiral before initiating horizontal stepovers.
- **Continuous Spiral Clearing**: Constant overlap stepover prevents full-width slotting engagement during clearing.
- **Wall Finish Allowance & Spring Pass**: Leaves a thin stock layer (e.g., 0.2mm) during roughing, followed by a full-depth finish pass and optional spring pass to guarantee accurate, perpendicular walls.

---

### 3.3 2.5D Contouring with Holding Tabs & Lead-Ins
Perimeter cutouts require workholding strategies to prevent parts from shifting or binding when severed from sheet stock.

![2.5D Contouring with Holding Tabs & Tangential Lead-Ins](images/real_contouring_tabs.png)

#### Contouring Capabilities:
- **3D Triangular Holding Tabs**: Creates rigid bridges (customizable width, height, and count) that seamlessly ramp the Z-axis up and over tab locations on final cut passes.
- **90° Tangential Arc Lead-In / Lead-Out**: Smoothly eases the tool into the profile wall along a circular radius, preventing dwell marks or cutter gouging.
- **Climb / Conventional Milling Selection**: Generates G2/G3 arc toolpaths optimized for right-hand cut dynamics.

---

### 3.4 Straight & Peck Drilling Cycles
- **Straight Plunge Drilling**: Single plunge with programmed feed rate and dwell at the hole bottom.
- **Peck Drilling**:
  - **Grbl Expanded Cycles**: Automatically generates segmented `G0`/`G1` plunge-retract motion blocks with full chip-clearing retracts to safe Z.
  - **Canned Cycles (G83 / G73)**: Outputs standard industry canned cycle blocks for LinuxCNC, Haas, and Fanuc controllers.
  - **Bolt Hole Circle & Grid Array**: Automatically calculates polar and Cartesian hole matrices.

---

### 3.5 Slotting & Edge Chamfering
- **Linear Slots**: Cuts single-pass slots (tool diameter = slot width) or wider multi-pass slots with trochoidal stepovers.
- **Chamfer Milling**: Automatically calculates exact Z cut depth based on tool angle (e.g., 60°, 90°) and tip diameter to deburr or bevel internal and external edges.

---

### 3.6 Single-Point Helical Thread Milling
- **Thread Standards Catalog**: Built-in pitch and diameter catalog for **ISO Metric** (M2 through M30, standard & fine) and **Unified Inch** (UNC/UNF #4 through 1").
- **Climb Bottom-to-Top Helical Path**: Cuts internal and external threads with smooth helical arc interpolation (`G2/G3 X.. Y.. Z.. I.. J..`), minimizing cutting pressure and eliminating tap breakage.

![Helical Thread Milling Operation](images/real_thread_milling.png)

---

## 4. Vector CAD Importers (DXF & SVG)

Import complex geometries directly from 2D CAD drawings or graphic design tools without requiring external CAM software.

![SVG & 2D Vector CAD Importer with Grayscale Depth Mapping](images/real_svg_importer.png)

### Supported CAD Formats:
1. **DXF 2D Vector Importer**:
   - Parses `LINE`, `ARC`, `CIRCLE`, `LWPOLYLINE`, and `POLYLINE` entities.
   - Automatically chains contiguous segments into closed machining loops.
   - Layer selection: Selectively mill, drill, or ignore specific CAD drawing layers.

![DXF 2D CAD Importer & Automatic Toolpathing](images/real_dxf_importer.png)

2. **SVG Importer with Grayscale Depth Mapping**:
   - Extracts cubic and quadratic Bezier curves, lines, rects, circles, and polygons.
   - **Grayscale Shading to Cut Depth**: Maps fill/stroke luminance directly to cut depth (**100% Black = Max Cut Depth**, **50% Gray = 50% Depth**, **0% White = 0.0mm Surface**), allowing multi-level relief carving and stepped engraving from a single SVG file.

---

## 5. Single-Line Text Engraving & Hershey Typography

Engrave serial numbers, nameplates, dials, and artistic plaques using true single-line stroke fonts.

![Single-Line Text Engraving with Hershey Cursive Typography](images/real_text_engraving.png)

### Typography Features:
- **Hershey Vector Typography Catalog**:
  - `Hershey Cursive Script`: Beautiful flowing handwritten script with natural baseline joining and looped ascenders.
  - `Hershey Gothic German & English`: Medieval blackletter typography.
  - `Hershey Simplex & Complex Roman`: Crisp serifed technical lettering.
  - `Hershey Sans-Serif`: Clean, modern signage font.
- **Curved Text Alignment**: Wrap text along circular arcs with customizable radius, center point, and angular spread.
- **Live 3D Geometry Rendering**: Real-time backplot updates text rotation, letter spacing, and depth dynamically.

---

## 6. Nesting & Custom Soft Jaw Fixturing

Maximize sheet stock utilization and create rigid secondary operation workholding fixtures.

![Vise Soft Jaw Fixturing Generator & 3D Cavity Preview](images/real_nesting_soft_jaws.png)

### Features:
1. **Step-and-Repeat Nesting**:
   - **Grid Array**: Rectangular $M \times N$ matrix with configurable part margins.
   - **Staggered / Honeycomb Array**: Interlocking rows to pack circular and irregular components with maximum density.
2. **Custom Vise Soft Jaw Generator**:
   - Mills matching rectangular or circular cavities into aluminum or machinable plastic vise jaws.
   - **Dogbone Corner Reliefs**: Automatically drills or cuts 45° corner clearance fillets so square-cornered parts seat flat without corner interference.

---

## 7. Probing, Homing & Work Coordinate Systems (WCS)

Accurate zeroing and coordinate referencing are critical for crash-free machining.

![Touchplate Probing & Work Coordinate System Zeroing Modal](images/real_probing_wcs.png)

### Probing & Jogging Workflows:
1. **Z-Surface Touchplate**:
   - Executes standard probe cycle (`G38.2 Z-.. F..`), calculates touchplate thickness offset, and sets `Z=0` (`G10 L20 P1 Z<thickness>`).
2. **Corner XYZ Edge Finding**:
   - Probes Z top surface, steps over, and probes outside X and Y workpiece edges with automated tool radius and lip compensation.
3. **Machine Homing ($H) & WCS Select**:
   - Quick toggle and zeroing across **G54 through G59** coordinate fixtures.
4. **Manual Jog Controller & Live DRO**:
   - Interactive Jogging controls with 0.01mm to 100mm increments, keyboard hotkeys, and spindle speed toggling.

![Manual Jog Controller & Live DRO Modal](images/real_jog_dro.png)


---

## 8. Feeds, Speeds & Machine Rigidity Guide

Conversational CNC includes a built-in cutting physics engine calibrated specifically for both desktop belt-driven CNCs (such as the **Inventables X-Carve** and **Shapeoko**) and rigid ballscrew VMCs.

### DeWalt DWP611 / Makita Router Speed Dial Reference

| Dial Setting | DeWalt DWP611 Speed | Makita RT0701 Speed | Recommended Applications |
| :---: | :---: | :---: | :--- |
| **1** | **~16,000 RPM** | **~10,000 RPM** | Large Surfacing Bits (1"+), Acrylic/Plastics, Aluminum, Brass |
| **2** | **~18,200 RPM** | **~14,000 RPM** | Hardwoods (Oak, Maple, Walnut), 1/4" Endmills |
| **3** | **~20,400 RPM** | **~18,000 RPM** | Softwoods (Pine, Cedar), MDF, Baltic Birch Plywood |
| **4** | **~22,600 RPM** | **~22,000 RPM** | General Purpose 1/8" Endmills |
| **5** | **~24,800 RPM** | **~26,000 RPM** | Fine Detail 1/16" & 1/32" Micro Endmills |
| **6** | **~27,000 RPM** | **~30,000 RPM** | Maximum Speed (High-feed engraving with V-bits) |

### Conservative Easel-Calibrated Feeds & Speeds Table

| Material | Tool Size | RPM (Dial) | Feed Rate XY | Plunge Rate Z | Stepdown (DOC) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Softwood (Pine)** | 1/8" Upcut (3.175mm) | 16,000 (Dial 1) | 950 mm/min (37 ipm) | 230 mm/min (9 ipm) | 1.0 mm (0.04") |
| **Softwood (Pine)** | 1/4" Downcut (6.35mm) | 16,000 (Dial 1) | 1,250 mm/min (49 ipm) | 250 mm/min (10 ipm) | 1.8 mm (0.07") |
| **Hardwood (Oak)** | 1/8" Upcut (3.175mm) | 18,000 (Dial 2) | 750 mm/min (30 ipm) | 200 mm/min (8 ipm) | 0.8 mm (0.03") |
| **Hardwood (Oak)** | 1/4" Downcut (6.35mm) | 18,000 (Dial 2) | 950 mm/min (37 ipm) | 220 mm/min (9 ipm) | 1.2 mm (0.05") |
| **MDF / Plywood** | 1/8" Upcut (3.175mm) | 16,000 (Dial 1) | 900 mm/min (35 ipm) | 230 mm/min (9 ipm) | 1.0 mm (0.04") |
| **MDF / Plywood** | 1/4" Downcut (6.35mm) | 16,000 (Dial 1) | 1,200 mm/min (47 ipm) | 250 mm/min (10 ipm) | 1.5 mm (0.06") |
| **Cast Acrylic** | 1/8" 1-Flute (3.175mm) | 16,000 (Dial 1) | 650 mm/min (25 ipm) | 180 mm/min (7 ipm) | 0.5 mm (0.02") |
| **Cast Acrylic** | 1/4" 1-Flute (6.35mm) | 16,000 (Dial 1) | 850 mm/min (33 ipm) | 200 mm/min (8 ipm) | 0.8 mm (0.03") |
| **6061 Aluminum** | 1/8" 1-Flute / 2-Flute | 16,000 (Dial 1) | 250 mm/min (10 ipm) | 80 mm/min (3 ipm) | 0.15 mm (0.006") |
| **6061 Aluminum** | 1/4" 2-Flute (6.35mm) | 16,000 (Dial 1) | 350 mm/min (14 ipm) | 100 mm/min (4 ipm) | 0.25 mm (0.010") |
| **360 Brass** | 1/8" 2-Flute (3.175mm) | 16,000 (Dial 1) | 300 mm/min (12 ipm) | 100 mm/min (4 ipm) | 0.20 mm (0.008") |
| **360 Brass** | 1/4" 2-Flute (6.35mm) | 16,000 (Dial 1) | 420 mm/min (16 ipm) | 120 mm/min (5 ipm) | 0.30 mm (0.012") |
| **Spoilboard Surfacing** | 1" Flycutter (25.4mm) | 16,000 (Dial 1) | 1,400 mm/min (55 ipm) | 200 mm/min (8 ipm) | 0.35 mm (50% stepover) |

---

## 9. 3D WebGL Toolpath Backplotter & Simulation Scrubber

Every operational screen features a synchronized 3D backplotter powered by Three.js / WebGL.

### Backplotter Visual Legend:
- 🔴 **Red Lines (`G0`)**: Rapid repositioning moves at safe retract height.
- 🔵 **Cyan Lines (`G1`, `G2`, `G3`)**: Controlled feed rate cutting motions and arcs.
- 🟡 **Yellow Helices**: Helical ramp plunge entries and Z plunge strokes.
- 🟢 **Green Crosshairs**: Program WCS Origin (`X0 Y0 Z0`).
- 🔲 **Translucent Grey Box**: Workpiece bounding stock envelope.

### Interactive Controls:
- **Orbit**: Left-Click and drag.
- **Pan**: Right-Click (or Shift + Left-Click) and drag.
- **Zoom**: Mouse scroll wheel.
- **Preset Camera Angles**: `Top View`, `Front View`, `Isometric View`, and `Fit to Screen` buttons.
- **Simulation Scrubber Bar**: Drag timeline to animate tool head motion, review instantaneous feed/speed DRO state, and inspect plain-English explanations of each G-code block.

---

*Conversational CNC — Precision machining simplified.*
