# Conversational CNC Controller — REST API Documentation

**Base URL**: `http://localhost:5001/api` (or configured host/port)  
**Content-Type**: `application/json`

---

## Table of Contents
1. [Overview & Conventions](#1-overview--conventions)
2. [Health & System Info](#2-health--system-info)
3. [Conversational G-Code Generation](#3-g-code-generation)
   - [GET /api/generate/dialects](#get-apigeneratedialects)
   - [GET /api/generate/thread-standards](#get-apigeneratethread-standards)
   - [POST /api/generate/drilling/straight-plunge](#post-apigeneratedrillingstraight-plunge)
   - [POST /api/generate/drilling/peck](#post-apigeneratedrillingpeck)
   - [POST /api/generate/thread-milling](#post-apigeneratethread-milling)
   - [POST /api/generate/pocket/circular](#post-apigeneratepocketcircular)
   - [POST /api/generate/pocket/circular-boss](#post-apigeneratepocketcircular-boss)
   - [POST /api/generate/pocket/rectangular](#post-apigeneratepocketrectangular)
   - [POST /api/generate/boss/rectangular](#post-apigeneratebossrectangular)
   - [POST /api/generate/slotting/linear](#post-apigenerateslottinglinear)
   - [POST /api/generate/chamfering/rectangular](#post-apigeneratechamferingrectangular)
   - [POST /api/generate/milling/contour](#post-apigeneratemillingcontour)
   - [POST /api/generate/surfacing](#post-apigeneratesurfacing)
   - [GET /api/generate/engraving/fonts](#get-apigenerateengravingfonts)
   - [GET /api/generate/engraving/glyphs](#get-apigenerateengravingglyphs)
   - [POST /api/generate/engraving/text](#post-apigenerateengravingtext)
4. [G-Code Transformations & Multi-Tool Splitter](#4-g-code-transformations--program-splitter)
   - [POST /api/transform/shift](#post-apitransformshift)
   - [POST /api/transform/rotate](#post-apitransformrotate)
   - [POST /api/transform/mirror](#post-apitransformmirror)
   - [POST /api/transform/feed-speed-override](#post-apitransformfeed-speed-override)
   - [POST /api/transform/split-tools](#post-apitransformsplit-tools)
5. [Step-and-Repeat Array Nesting & Soft Jaw Fixturing](#5-step-and-repeat-array-nesting--soft-jaw-fixturing)
   - [POST /api/generate/nesting/grid](#post-apigeneratenestinggrid)
   - [POST /api/generate/nesting/soft-jaw](#post-apigeneratenestingsoft-jaw)
6. [DXF 2D Vector CAD Importer](#6-dxf-2d-vector-cad-importer)
   - [POST /api/generate/dxf/parse](#post-apigeneratedxfparse)
   - [POST /api/generate/dxf/toolpath](#post-apigeneratedxftoolpath)
7. [SVG 2D Vector CAD Importer with Grayscale Depth Mapping](#7-svg-2d-vector-cad-importer-with-grayscale-depth-mapping)
   - [POST /api/generate/svg/parse](#post-apigeneratesvgparse)
   - [POST /api/generate/svg/toolpath](#post-apigeneratesvgtoolpath)
8. [Feeds & Speeds Physics Engine](#8-feeds--speeds-physics-engine)
   - [GET /api/calculator/materials-catalog](#get-apicalculatormaterials-catalog)
   - [POST /api/calculator/feeds-speeds](#post-apicalculatorfeeds-speeds)
9. [Machine Probing & Setup Macros](#9-machine-probing--setup-macros)
   - [POST /api/probing/z-touch-plate](#post-apiprobingz-touch-plate)
   - [POST /api/probing/corner-xyz](#post-apiprobingcorner-xyz)
   - [GET /api/probing/homing](#get-apiprobinghoming)
10. [Workpiece Surface Mesh Leveling & G-Code Warper](#10-workpiece-surface-mesh-leveling--g-code-warper)
    - [POST /api/mesh/generate-points](#post-apimeshgenerate-points)
    - [POST /api/mesh/probe-macro](#post-apimeshprobe-macro)
    - [POST /api/mesh/parse-log](#post-apimeshparse-log)
    - [POST /api/mesh/warp-gcode](#post-apimeshwarp-gcode)
11. [Manual Jog Controller & Machine Control](#11-manual-jog-controller--machine-control)
    - [POST /api/jog/step](#post-apijogstep)
    - [POST /api/jog/zero](#post-apijogzero)
    - [POST /api/jog/goto-origin](#post-apijoggoto-origin)
    - [POST /api/jog/spindle](#post-apijogspindle)
12. [Multi-Operation Job Program Sequencer](#12-multi-operation-job-program-sequencer)
    - [POST /api/generate/job-sequence](#post-apigeneratejob-sequence)
13. [Machine Profiles](#13-machine-profiles)
14. [Tool Library](#14-tool-library)
15. [Material Presets](#15-material-presets)
16. [Error Handling Format](#16-error-handling-format)




---


## 1. Overview & Conventions

- **Stateless & Deterministic**: Generation endpoints compute G-code mathematically from input payloads without storing job state.
- **Dynamic Machine Resolution**: If no `machine_profile_id` is specified in a request, the API automatically applies the currently active machine profile.
- **Automatic Presets Resolution**: Providing a `tool_id` or `material_preset_id` allows the generator to automatically resolve spindle RPM, feed rates, plunge rates, and tool metadata.
- **Grbl & Standard Controller Support**: Linear expansion of peck cycles and canned cycles for Grbl (which lacks native canned cycles), and native RS274/NGC `G81`/`G83` for LinuxCNC/Standard controllers. Native 3D helical interpolation arcs (`G2`/`G3` with `I`, `J`, `Z`) are formatted for both dialects.

---

## 2. Health & System Info

### `GET /api/health`
Checks backend service availability.

#### Response `200 OK`
```json
{
  "service": "Conversational CNC Controller Backend",
  "status": "online",
  "version": "0.2.0"
}
```

---

### `GET /api/generate/dialects`
Lists supported CNC motion controller dialects.

#### Response `200 OK`
```json
{
  "available_dialects": ["grbl", "grblhal", "fluidnc", "linuxcnc", "standard"],
  "default": "grbl"
}
```

---

### `GET /api/generate/thread-standards`
Returns the built-in database of standard thread sizes (Metric ISO Coarse, Imperial UNC, and Imperial UNF) with nominal diameters, pitches, and tap drill recommendations.

#### Response `200 OK`
```json
{
  "categories": {
    "metric": ["M2x0.4", "M3x0.5", "M4x0.7", "M5x0.8", "M6x1.0", "M8x1.25", "M10x1.5", "M12x1.75", "M16x2.0", "M20x2.5"],
    "imperial_unc": ["#4-40 UNC", "#6-32 UNC", "#8-32 UNC", "#10-24 UNC", "1/4-20 UNC", "5/16-18 UNC", "3/8-16 UNC", "1/2-13 UNC"],
    "imperial_unf": ["#10-32 UNF", "1/4-28 UNF", "5/16-24 UNF", "3/8-24 UNF", "1/2-20 UNF"]
  },
  "standards": {
    "M6x1.0": {
      "nominal_dia": 6.0,
      "pitch": 1.0,
      "tap_drill_dia": 5.0,
      "type": "metric"
    }
  }
}
```

---

## 3. G-Code Generation

### `POST /api/generate/drilling/straight-plunge`
Generates deterministic G-code for straight-plunge hole drilling.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `holes` | `Array<[number, number]>` | Optional* | `null` | Array of `[X, Y]` hole coordinates. |
| `x`, `y` | `number` | Optional* | `null` | Single hole coordinate. |
| `target_depth_z` | `number` | **Yes** | — | Target depth (e.g. `-6.0`). |
| `start_z` | `number` | No | `0.0` | Top surface Z coordinate. |
| `retract_z` | `number` | No | Machine safe Z (`5.0`) | Clearance retract height. |
| `plunge_feed` | `number` | No | Preset / `200.0` | Plunge feed rate (mm/min). |
| `dwell_seconds` | `number` | No | `0.0` | Dwell time at hole bottom. |

---

### `POST /api/generate/drilling/peck`
Generates deep hole peck drilling G-code with chip clearing (full retract) or chip breaking.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `holes` | `Array<[number, number]>` | Optional* | `null` | Hole coordinates `[[X, Y], ...]`. |
| `target_depth_z` | `number` | **Yes** | — | Total target drill depth Z (e.g. `-15.0`). |
| `peck_depth` | `number` | **Yes** | — | Incremental peck depth Q (mm/peck). |
| `peck_retract_type` | `string` | No | `"full_retract"` | `"full_retract"` (G83 chip clearing) or `"chip_break"` (G73). |
| `start_z` | `number` | No | `0.0` | Stock top surface Z. |
| `retract_z` | `number` | No | Machine safe Z (`5.0`) | Retract clearance Z. |
| `plunge_feed` | `number` | No | Preset / `200.0` | Plunge feed rate. |
| `dwell_seconds` | `number` | No | `0.0` | Dwell time at final depth. |

---

### `POST /api/generate/thread-milling`
Generates 3D helical toolpaths for internal tapped holes or external threaded studs.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `holes` | `Array<[number, number]>` | Optional* | `null` | Array of thread center coordinates. |
| `thread_standard` | `string` | No | `null` | Preset standard e.g. `"M6x1.0"` or `"1/4-20 UNC"`. |
| `nominal_diameter` | `number` | Optional** | — | Major thread diameter (mm). |
| `pitch` | `number` | Optional** | — | Thread pitch (mm). |
| `thread_length` | `number` | **Yes** | — | Total thread axial depth/length (mm). |
| `tool_diameter` | `number` | No | Tool preset / `4.5` | Thread mill cutting diameter (mm). |
| `thread_type` | `string` | No | `"internal"` | `"internal"` (tapped hole) or `"external"` (stud/rod). |
| `thread_hand` | `string` | No | `"right_hand"` | `"right_hand"` or `"left_hand"`. |
| `milling_direction` | `string` | No | `"bottom_to_top"` | `"bottom_to_top"` (climb milling) or `"top_to_bottom"`. |
| `radial_passes` | `integer` | No | `1` | Number of radial passes (1 to 4). |
| `spring_passes` | `integer` | No | `0` | Clean-up spring passes at final radius. |
| `feed_rate_xy` | `number` | No | Preset / `300.0` | Helical cutting feed rate. |

*\*Must provide `holes` or `(x, y)`. \*\*Must provide `thread_standard` OR both `nominal_diameter` and `pitch`.*

---

### `POST /api/generate/pocket/circular`
Generates circular pocketing and helical bore milling G-code.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `pockets` | `Array<[number, number]>` | Optional* | `null` | Pocket center coordinates `[[X, Y], ...]`. |
| `pocket_diameter` | `number` | **Yes** | — | Target pocket diameter (mm). |
| `target_depth_z` | `number` | **Yes** | — | Total pocket depth Z (e.g. `-6.0`). |
| `tool_diameter` | `number` | No | Tool preset / `3.175` | Endmill diameter (mm). |
| `stepdown_z` | `number` | No | `1.5` | Z depth per pass (mm). |
| `stepover_percent` | `number` | No | `50.0` | Radial stepover % (10-90%). |
| `finish_allowance` | `number` | No | `0.2` | Wall stock allowance for finish pass (mm). |
| `feed_rate_xy` | `number` | No | Preset / `1000.0` | Cutting feed rate (mm/min). |

---

### `POST /api/generate/pocket/circular-boss`
Generates G-code for raised cylindrical bosses, studs, spigots, and custom bolt shafts machined from round bar stock or rectangular billets using outside-in concentric climb clearing loops.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `boss_center_x`, `boss_center_y` | `number` | No | `0.0` | Center of finished shaft (mm). |
| `boss_diameter` | `number` | **Yes** | — | Finished shaft diameter (mm). |
| `stock_shape` | `string` | No | `"circle"` | `"circle"` (round bar) or `"rectangle"`. |
| `stock_diameter` | `number` | No | `25.0` | Outer diameter of raw round stock (mm). |
| `stock_length_x`, `stock_width_y` | `number` | No | `30.0` | Stock dimensions if rectangular billet (mm). |
| `target_depth_z` | `number` | **Yes** | — | Shaft length / cut depth Z (e.g. `-15.0`). |
| `tool_diameter` | `number` | No | Tool preset / `6.35` | Flat endmill diameter (mm). |
| `stepdown_z` | `number` | No | `1.0` | Z depth per pass (mm). |
| `stepover_percent` | `number` | No | `50.0` | Radial stepover % (10-90%). |
| `finish_allowance` | `number` | No | `0.2` | Wall stock allowance for finish pass (mm). |
| `feed_rate_xy` | `number` | No | Preset / `800.0` | Cutting feed rate (mm/min). |
| `plunge_feed` | `number` | No | Preset / `250.0` | Plunge feed in open air (mm/min). |

---

### `POST /api/generate/surfacing`
Generates workpiece and spoilboard surfacing/facing G-code.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `length_x` | `number` | **Yes** | — | Stock length along X (mm). |
| `width_y` | `number` | **Yes** | — | Stock width along Y (mm). |
| `origin_x`, `origin_y` | `number` | No | `0.0` | Datum reference position. |
| `origin_mode` | `string` | No | `"corner"` | `"corner"` (lower-left 0,0) or `"center"`. |
| `total_depth_z` | `number` | No | `1.0` | Total depth to remove (mm). |
| `stepdown_z` | `number` | No | `0.5` | Z depth per pass (mm). |
| `tool_diameter` | `number` | No | Tool preset / `25.4` | Flycutter / bit diameter (mm). |
| `stepover_percent` | `number` | No | `70.0` | Tool stepover % (10-90%). |
| `cut_direction` | `string` | No | `"zigzag"` | `"zigzag"` (bidirectional) or `"climb_oneway"`. |
| `overtravel` | `number` | No | `2.0` | Distance cutter clears past edge (mm). |
| `feed_rate_xy` | `number` | No | Preset / `2000.0` | Cutting feed rate. |

### `GET /api/generate/engraving/fonts`
Returns the available single-line vector fonts catalog for CNC text engraving.

#### Response `200 OK`
```json
{
  "fonts": {
    "simplex_sans": "Simplex Sans (Clean Single-Stroke)",
    "duplex_sans": "Duplex Bold Sans (Double-Stroke)",
    "roman_serif": "Roman Serif (Classic Formal)",
    "cursive_script": "Cursive Script (Flowing Elegance)",
    "block_stencil": "Industrial Block (Technical / Chamfered)"
  },
  "default": "simplex_sans"
}
```

### `GET /api/generate/engraving/glyphs`
Returns the complete vector stroke polylines database for all single-line engraving fonts.

---

### `POST /api/generate/engraving/text`
Generates vector stroke G-code for text engraving along linear paths or wrapped around circular arcs.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `text` | `string` | **Yes** | — | The text string to engrave (supports multi-line `\n`). |
| `layout_mode` | `string` | No | `"linear"` | `"linear"` or `"arc"`. |
| `start_x`, `start_y` | `number` | No | `0.0` | Linear text start/origin coordinate (mm). |
| `rotation_deg` | `number` | No | `0.0` | Linear text rotation angle in degrees. |
| `align` | `string` | No | `"left"` | `"left"`, `"center"`, or `"right"`. |
| `center_x`, `center_y` | `number` | No | `0.0` | Arc center coordinate (mm) (arc mode). |
| `arc_radius` | `number` | No | `30.0` | Pitch arc radius in mm (arc mode). |
| `start_angle_deg` | `number` | No | `90.0` | Center/start angle on circle in degrees (arc mode). |
| `arc_direction` | `string` | No | `"clockwise"` | `"clockwise"` or `"counter_clockwise"`. |
| `font_name` | `string` | No | `"simplex_sans"` | Font style: `"simplex_sans"`, `"duplex_sans"`, `"roman_serif"`, `"cursive_script"`, `"block_stencil"`. |
| `font_size` | `number` | No | `10.0` | Nominal font cap height in mm. |
| `letter_spacing` | `number` | No | `1.0` | Extra spacing between characters in mm. |
| `curve_subdivisions` | `integer` | No | `4` | Curve interpolation sampling steps (1=coarse/fast, 4=smooth, 8=ultra-fine). |
| `target_depth_z` | `number` | No | `-0.5` | Target engraving depth Z (mm). |
| `stepdown_z` | `number` | No | `0.5` | Maximum depth per pass (mm). |
| `retract_z` | `number` | No | Machine safe Z (`2.0`) | Retract clearance Z between strokes. |
| `feed_rate_xy` | `number` | No | Preset / `800.0` | Engraving feed rate (mm/min). |

---

### `POST /api/generate/pocket/rectangular`
Generates G-code for rectangular pockets with corner radii, concentric clearing loops, and finishing passes.

#### Request Payload
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `length_x` | `number` | **Yes** | — | Pocket length along X (mm). |
| `width_y` | `number` | **Yes** | — | Pocket width along Y (mm). |
| `target_depth_z` | `number` | **Yes** | — | Target pocket depth Z (mm). |
| `origin_x` | `number` | No | `0.0` | Origin X coordinate. |
| `origin_y` | `number` | No | `0.0` | Origin Y coordinate. |
| `corner_radius` | `number` | No | `0.0` | Corner fillet radius (mm). |
| `origin_mode` | `string` | No | `"center"` | `"center"` or `"corner"`. |
| `stepdown_z` | `number` | No | `1.5` | Depth per pass (mm). |
| `stepover_percent`| `number` | No | `60.0` | Stepover percentage of tool diameter. |
| `finish_pass_allowance` | `number` | No | `0.3` | Wall finish allowance (mm). |
| `entry_strategy` | `string` | No | `"helical_ramp"` | `"helical_ramp"` or `"plunge"`. |

---

### `POST /api/generate/boss/rectangular`
Generates G-code for raised rectangular islands / bosses within stock boundaries.

#### Request Payload
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `boss_length_x` | `number` | **Yes** | — | Boss length along X (mm). |
| `boss_width_y` | `number` | **Yes** | — | Boss width along Y (mm). |
| `stock_length_x` | `number` | **Yes** | — | Stock boundary length along X (mm). |
| `stock_width_y` | `number` | **Yes** | — | Stock boundary width along Y (mm). |
| `target_depth_z` | `number` | **Yes** | — | Target machining depth Z (mm). |
| `boss_origin_x` | `number` | No | `0.0` | Boss island center X (mm). |
| `boss_origin_y` | `number` | No | `0.0` | Boss island center Y (mm). |
| `boss_corner_radius` | `number` | No | `0.0` | Boss corner fillet radius (mm). |

---

### `POST /api/generate/slotting/linear`
Generates G-code for straight linear slots with depth stepdowns.

#### Request Payload
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `start_x` | `number` | **Yes** | — | Slot start X coordinate (mm). |
| `start_y` | `number` | **Yes** | — | Slot start Y coordinate (mm). |
| `end_x` | `number` | **Yes** | — | Slot end X coordinate (mm). |
| `end_y` | `number` | **Yes** | — | Slot end Y coordinate (mm). |
| `slot_width` | `number` | **Yes** | — | Slot width in mm ($\ge D_{\text{tool}}$). |
| `target_depth_z` | `number` | **Yes** | — | Target slot depth Z (mm). |
| `stepdown_z` | `number` | No | `1.0` | Max depth per pass (mm). |

---

### `POST /api/generate/chamfering/rectangular`
Generates G-code for 2D perimeter edge deburring and chamfering with conical V-bits.

#### Request Payload
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `length_x` | `number` | **Yes** | — | Feature length along X (mm). |
| `width_y` | `number` | **Yes** | — | Feature width along Y (mm). |
| `chamfer_width` | `number` | No | `0.5` | Desired chamfer cut width (mm). |
| `vbit_angle_deg` | `number` | No | `90.0` | V-bit included angle (degrees). |
| `feature_type` | `string` | No | `"outside"` | `"outside"` or `"inside"`. |
| `origin_mode` | `string` | No | `"center"` | `"center"` or `"corner"`. |

---

### `POST /api/generate/milling/contour`
Generates 2.5D arbitrary profile and contour milling G-code from chained line and arc segments with cutter compensation (climb/conventional) and smooth lead-ins/outs.

#### Request Payload
```json
{
  "segments": [
    {"type": "line", "x": 40.0, "y": 0.0},
    {"type": "line", "x": 40.0, "y": 30.0},
    {"type": "line", "x": 0.0, "y": 30.0},
    {"type": "line", "x": 0.0, "y": 0.0}
  ],
  "start_point": [0.0, 0.0],
  "is_closed": true,
  "side": "left",
  "lead_in_type": "tangential_arc",
  "lead_in_radius": 5.0,
  "target_depth_z": -5.0,
  "stepdown_z": 1.5,
  "finish_allowance": 0.2,
  "spring_pass": true,
  "tool_diameter": 3.175,
  "feed_rate_xy": 800.0,
  "plunge_feed": 250.0,
  "spindle_speed": 16000
}
```

---

## 4. G-Code Transformations & Program Splitter


### `POST /api/transform/shift`
Translates all coordinates by $(\Delta X, \Delta Y, \Delta Z)$.

#### Request Payload
```json
{
  "gcode": "G0 X10 Y20 Z5\nG1 X50 Y50 Z-2 F800",
  "delta_x": 10.0,
  "delta_y": -5.0,
  "delta_z": 0.0
}
```

---

### `POST /api/transform/rotate`
Rotates $X, Y$ coordinates and $I, J$ arc vectors around a pivot center $(X_c, Y_c)$ by an angle in degrees.

#### Request Payload
```json
{
  "gcode": "G1 X10 Y0 F500",
  "angle_deg": 45.0,
  "center_x": 0.0,
  "center_y": 0.0
}
```

---

### `POST /api/transform/mirror`
Mirrors coordinates across an axis (`x` or `y`) and automatically reverses arc directions ($G2 \leftrightarrow G3$).

#### Request Payload
```json
{
  "gcode": "G2 X10 Y20 I5 J0",
  "mirror_axis": "x",
  "origin_x": 0.0,
  "origin_y": 0.0
}
```

---

### `POST /api/transform/feed-speed-override`
Scales feed rates ($F$) and spindle speeds ($S$) across the entire program by percentage multipliers.

#### Request Payload
```json
{
  "gcode": "G1 X10 Y20 F1000\nS16000 M3",
  "feed_percent": 80.0,
  "speed_percent": 100.0
}
```

---

### `POST /api/transform/split-tools`
Splits a multi-tool program (`M6 T...`) into standalone `.nc` files for each tool with safe headers and footers.

#### Request Payload
```json
{
  "gcode": "T1 M6\nG1 X0 Y0 Z-5\nT2 M6\nG1 X10 Y10 Z-2",
  "safe_retract_z": 5.0
}
```

---

## 5. Step-and-Repeat Array Nesting & Soft Jaw Fixturing

### `POST /api/generate/nesting/grid`
Arrays any base single-part G-code snippet across an $N_x \times N_y$ matrix grid or staggered honeycomb layout with serpentine rapid traversal.

#### Request Payload
```json
{
  "gcode": "G0 X0 Y0\nG1 Z-3.0 F200\nG1 X20 Y0 F800\nG1 X20 Y20\nG1 X0 Y20\nG1 X0 Y0\nG0 Z5.0",
  "cols_x": 3,
  "rows_y": 2,
  "spacing_x": 50.0,
  "spacing_y": 40.0,
  "layout_pattern": "grid",
  "order_strategy": "zigzag",
  "safe_z_retract": 5.0
}
```

---

### `POST /api/generate/nesting/soft-jaw`
Generates negative clamping cavities into vise soft jaws for secondary machining operations (Op 2), with optional 45° dogbone corner relief overcuts.

#### Request Payload
```json
{
  "jaw_type": "rectangular",
  "part_length_x": 60.0,
  "part_width_y": 40.0,
  "step_depth_z": 3.0,
  "jaw_gap": 10.0,
  "dogbone_relief": true,
  "tool_diameter": 6.35,
  "stepdown_z": 1.5,
  "stepover_percent": 50.0,
  "feed_rate_xy": 1000.0,
  "plunge_feed": 250.0,
  "spindle_speed": 16000
}
```

---

## 6. DXF 2D Vector CAD Importer & Direct-to-GCode

### `POST /api/generate/dxf/parse`
Parses raw 2D ASCII DXF files (AutoCAD R12 to 2018), extracting entity primitives (`LINE`, `ARC`, `CIRCLE`, `LWPOLYLINE`), chaining matching vertices into continuous loops/paths, and detecting circle drill points and bounding boxes.

#### Request Payload
```json
{
  "dxf_text": "0\nSECTION\n2\nENTITIES\n0\nLINE\n8\n0\n10\n0.0\n20\n0.0\n11\n50.0\n21\n0.0\n0\nCIRCLE\n8\nHOLES\n10\n25.0\n20\n15.0\n40\n3.0\n0\nENDSEC\n0\nEOF"
}
```

#### Response Payload
```json
{
  "success": true,
  "data": {
    "entity_count": 2,
    "layers": ["0", "HOLES"],
    "circles": [
      {
        "x": 25.0,
        "y": 15.0,
        "radius": 3.0,
        "diameter": 6.0,
        "layer": "HOLES"
      }
    ],
    "chains": [
      {
        "id": 1,
        "layer": "0",
        "is_closed": false,
        "start_point": [0.0, 0.0],
        "segments": [
          { "type": "line", "x": 50.0, "y": 0.0, "i": 0.0, "j": 0.0, "cw": false }
        ],
        "segment_count": 1
      }
    ],
    "bounding_box": {
      "min_x": 0.0,
      "max_x": 50.0,
      "min_y": 0.0,
      "max_y": 15.0,
      "width": 50.0,
      "height": 15.0
    }
  }
}
```

---

### `POST /api/generate/dxf/toolpath`
Converts parsed DXF chains or circle centers directly into CNC G-code toolpaths (contouring or drilling) with full dialect compliance and cutter compensation.

#### Request Payload
```json
{
  "chains": [ ... ],
  "circles": [ ... ],
  "operation_type": "contour",
  "side": "left",
  "target_depth_z": -6.0,
  "stepdown_z": 1.5,
  "finish_allowance": 0.2,
  "spring_pass": true,
  "tool_diameter": 3.175,
  "feed_rate_xy": 800.0,
  "plunge_feed": 250.0,
  "spindle_speed": 16000,
  "safe_z_retract": 5.0
}
```

---

## 7. SVG 2D Vector CAD Importer with Grayscale Depth Mapping

### `POST /api/generate/svg/parse`
Parses raw SVG XML files, extracting vector paths (`<path>`, `<rect>`, `<circle>`, `<ellipse>`, `<line>`, `<polyline>`, `<polygon>`), transforms, and evaluates fill/stroke color into normalized ITU-R BT.601 luminance ($L = 0.299R + 0.587G + 0.114B$), mapping grayscale percentage into proportional Z cut depths ($Z_{\text{cut}} = Z_{\text{max}} \times \text{shading}\%$).

#### Request Payload
```json
{
  "svg_text": "<svg width='100mm' height='60mm' viewBox='0 0 100 60'><rect x='10' y='10' width='80' height='40' fill='#000000'/><circle cx='30' cy='30' r='10' fill='#808080'/></svg>",
  "max_cut_depth": -6.0,
  "default_dpi": 96.0,
  "flip_y": true,
  "invert_shading": false,
  "shading_mode": "fill"
}
```

#### Response Payload
```json
{
  "success": true,
  "data": {
    "entity_count": 2,
    "chains": [
      {
        "id": 1,
        "tag": "rect",
        "fill": "#000000",
        "luminance": 0.0,
        "shading_percent": 100.0,
        "target_depth_z": -6.0,
        "is_closed": true,
        "start_point": [10.0, 50.0],
        "segments": [ ... ]
      }
    ],
    "circles": [
      {
        "x": 30.0,
        "y": 30.0,
        "radius": 10.0,
        "diameter": 20.0,
        "fill": "#808080",
        "luminance": 0.5,
        "shading_percent": 50.0,
        "target_depth_z": -3.0
      }
    ],
    "bounding_box": {
      "min_x": 10.0,
      "max_x": 90.0,
      "min_y": 10.0,
      "max_y": 50.0,
      "width": 80.0,
      "height": 40.0
    }
  }
}
```

---

### `POST /api/generate/svg/toolpath`
Generates CNC G-code toolpaths from parsed SVG chains and circles, automatically applying multi-pass depth stepdowns down to each path's individual grayscale-calculated target depth.

#### Request Payload
```json
{
  "chains": [ ... ],
  "circles": [ ... ],
  "operation_type": "auto",
  "side": "left",
  "use_grayscale_depths": true,
  "stepdown_z": 1.5,
  "tool_diameter": 3.175,
  "feed_rate_xy": 800.0,
  "plunge_feed": 250.0,
  "spindle_speed": 16000,
  "safe_z_retract": 5.0
}
```

---

## 8. Feeds & Speeds Physics Engine




### `GET /api/calculator/materials-catalog`
Returns the material cutting constants, recommended surface speed ranges (SMM), baseline chip loads, and specific cutting energy ($K_p$).

---

### `POST /api/calculator/feeds-speeds`
Calculates optimal spindle RPM, feed rate XY, plunge feed, Radial Chip Thinning Factor (RCTF) compensation, Material Removal Rate (MRR), and spindle cutting power (kW/HP).

#### Request Payload
```json
{
  "material_key": "aluminum_6061",
  "tool_diameter_mm": 6.35,
  "num_flutes": 2,
  "stepover_mm": 1.5,
  "stepdown_mm": 1.0,
  "tool_stickout_mm": 20.0,
  "max_spindle_rpm": 27000,
  "min_spindle_rpm": 10000
}
```

---

## 9. Machine Probing & Setup Macros

### `POST /api/probing/z-touch-plate`
Generates a 2-stage (fast search + fine precision touch) Z-touch plate probing macro with `G38.2`, sets `G10 L20 P1 Z<plate_thickness>`, and lifts to safe clearance.

#### Request Payload
```json
{
  "plate_thickness": 14.85,
  "search_dist": 30.0,
  "fast_feed": 150.0,
  "slow_feed": 25.0,
  "retract_height": 20.0
}
```

---

### `POST /api/probing/corner-xyz`
Generates a 3-axis corner touch block probing macro (Z surface, X edge with tool radius offset, Y edge with tool radius offset) to set $(X0, Y0, Z0)$ in `G54`.

#### Request Payload
```json
{
  "tool_diameter": 6.35,
  "plate_thickness": 14.85,
  "block_x_lip": 10.0,
  "block_y_lip": 10.0,
  "search_dist": 25.0,
  "fast_feed": 150.0,
  "slow_feed": 25.0,
  "retract_z": 15.0
}
```

---

### `GET /api/probing/homing`
Generates the standard machine homing sequence (`$H`) and coordinate verification commands.

---

## 10. Workpiece Surface Mesh Leveling & G-Code Warper

### `POST /api/mesh/generate-points`
Generates an array of candidate touch probe sampling points across arbitrary workpiece geometries (Rectangles, Circular Discs, Concentric Donut Rings, or Polygons) with perimeter inset margins.

#### Request Payload
```json
{
  "shape_type": "disc",
  "disc_center_x": 50.0,
  "disc_center_y": 50.0,
  "disc_diameter": 100.0,
  "inset_margin": 3.0,
  "grid_spacing": 15.0
}
```

---

### `POST /api/mesh/probe-macro`
Generates a complete multi-point touch probe routine (`G38.2`) with snake traversal, skipping excluded obstacles/clamps, with dual-stage touch feeds.

---

### `POST /api/mesh/parse-log`
Parses probe console logs (`[PRB:X,Y,Z:1]` or CSV format) and calibrates surface heights $\Delta Z$ by subtracting touch plate thickness.

---

### `POST /api/mesh/warp-gcode`
Applies pure-Python Delaunay triangulation and Barycentric surface interpolation to dynamically warp any external G-code program to match workpiece surface topography.

---

## 11. Manual Jog Controller & Machine Control

### `POST /api/jog/step`
Generates an incremental jog move command ($J=G91 for Grbl/Smoothie, G91 G1 for Standard).

#### Request Payload
```json
{
  "axis": "X",
  "distance": 10.0,
  "feed_rate": 1200.0,
  "units": "mm",
  "dialect": "grbl"
}
```

---

### `POST /api/jog/zero`
Generates coordinate zeroing command (`G10 L20 P1`) for specified axes.

#### Request Payload
```json
{
  "axes": ["X", "Y", "Z"],
  "wcs_slot": 1
}
```

---

### `POST /api/jog/goto-origin`
Generates a safe 2-stage rapid return to Work Coordinate Origin (lifts Z to safe clearance then rapids XY to X0 Y0).

#### Request Payload
```json
{
  "safe_z_retract": 5.0,
  "units": "mm"
}
```

---

### `POST /api/jog/spindle`
Generates manual spindle toggle commands (`M3 S<rpm>` / `M5`).

#### Request Payload
```json
{
  "rpm": 16000,
  "state": true,
  "clockwise": true
}
```

---

## 12. Multi-Operation Job Program Sequencer

### `POST /api/generate/job-sequence`
Assembles multiple conversational machining operations into a single cohesive, production-ready `.nc` job file with unified safety headers, intelligent tool change optimization, safe retracts, and program footers.

#### Request Payload
```json
{
  "job_name": "Bracket_Machining_Job",
  "operations": [
    {
      "op_name": "Surface Top Face",
      "op_type": "surfacing",
      "tool_number": 1,
      "tool_name": "Flycutter 25mm",
      "tool_diameter": 25.0,
      "spindle_speed": 14000,
      "params": {
        "length_x": 100.0,
        "width_y": 80.0,
        "total_depth_z": 1.0,
        "stepdown_z": 1.0,
        "stepover_percent": 60.0
      }
    },
    {
      "op_name": "Center Bearing Bore",
      "op_type": "circular_pocket",
      "tool_number": 2,
      "tool_name": "1/4 Endmill",
      "tool_diameter": 6.35,
      "spindle_speed": 16000,
      "params": {
        "pockets": [[50.0, 40.0]],
        "pocket_diameter": 30.0,
        "target_depth_z": -5.0,
        "stepdown_z": 2.5
      }
    }
  ],
  "safe_z_retract": 5.0,
  "units": "mm",
  "dialect": "grbl",
  "optimize_tool_order": false,
  "park_x": 0.0,
  "park_y": 0.0,
  "park_z": 5.0
}
```

---

## 13. Machine Profiles

- `GET /api/machines`: List all machine profiles.
- `GET /api/machines/active`: Get active machine profile.
- `POST /api/machines/:id/activate`: Set active machine profile.
- `POST /api/machines`: Create a machine profile.
- `GET /api/machines/:id`: Retrieve profile by ID.
- `PUT /api/machines/:id`: Update profile fields.
- `DELETE /api/machines/:id`: Delete profile.

---

## 14. Tool Library
- `GET /api/tools`: List all tools with material presets.
- `GET /api/tools/:id`: Retrieve tool by ID.
- `POST /api/tools`: Add a new tool.
- `PUT /api/tools/:id`: Update tool properties.
- `DELETE /api/tools/:id`: Delete a tool and its presets.

---

## 15. Material Presets
- `GET /api/materials`: List all presets (optionally filtered with `?tool_id=1`).
- `GET /api/materials/:id`: Retrieve preset by ID.
- `POST /api/materials/tool/:tool_id`: Create preset attached to a tool.
- `PUT /api/materials/:id`: Update preset.
- `DELETE /api/materials/:id`: Delete preset.

---

## 16. Error Handling Format

Standard JSON error payload for validation failures (`400 Bad Request`):
```json
{
  "error": "Validation error",
  "details": [
    {
      "loc": ["target_depth_z"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

