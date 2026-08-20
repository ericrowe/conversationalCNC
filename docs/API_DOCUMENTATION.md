# Conversational CNC Controller — REST API Documentation

**Base URL**: `http://localhost:5001/api` (or configured host/port)  
**Content-Type**: `application/json`

---

## Table of Contents
1. [Overview & Conventions](#1-overview--conventions)
2. [Health & System Info](#2-health--system-info)
3. [G-Code Generation (Phase 1 & Phase 2 Operations)](#3-g-code-generation)
   - [GET /api/generate/dialects](#get-apigeneratedialects)
   - [GET /api/generate/thread-standards](#get-apigeneratethread-standards)
   - [POST /api/generate/drilling/straight-plunge](#post-apigeneratedrillingstraight-plunge)
   - [POST /api/generate/drilling/peck](#post-apigeneratedrillingpeck)
   - [POST /api/generate/thread-milling](#post-apigeneratethread-milling)
   - [POST /api/generate/pocket/circular](#post-apigeneratepocketcircular)
   - [POST /api/generate/surfacing](#post-apigeneratesurfacing)
   - [GET /api/generate/engraving/fonts](#get-apigenerateengravingfonts)
   - [POST /api/generate/engraving/text](#post-apigenerateengravingtext)
4. [Machine Profiles](#4-machine-profiles)


   - [GET /api/machines](#get-apimachines)
   - [GET /api/machines/active](#get-apimachinesactive)
   - [POST /api/machines/:id/activate](#post-apimachinesidactivate)
   - [POST /api/machines](#post-apimachines)
   - [GET /api/machines/:id](#get-apimachinesid)
   - [PUT /api/machines/:id](#put-apimachinesid)
   - [DELETE /api/machines/:id](#delete-apimachinesid)
5. [Tool Library](#5-tool-library)
   - [GET /api/tools](#get-apitools)
   - [GET /api/tools/:id](#get-apitoolsid)
   - [POST /api/tools](#post-apitools)
   - [PUT /api/tools/:id](#put-apitoolsid)
   - [DELETE /api/tools/:id](#delete-apitoolsid)
6. [Material Presets](#6-material-presets)
   - [GET /api/materials](#get-apimaterials)
   - [GET /api/materials/:id](#get-apimaterialsid)
   - [POST /api/materials/tool/:tool_id](#post-apimaterialstooltool_id)
   - [PUT /api/materials/:id](#put-apimaterialsid)
   - [DELETE /api/materials/:id](#delete-apimaterialsid)
7. [Error Handling Format](#7-error-handling-format)

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



## 4. Machine Profiles

- `GET /api/machines`: List all machine profiles.
- `GET /api/machines/active`: Get active machine profile.
- `POST /api/machines/:id/activate`: Set active machine profile.
- `POST /api/machines`: Create a machine profile.
- `GET /api/machines/:id`: Retrieve profile by ID.
- `PUT /api/machines/:id`: Update profile fields.
- `DELETE /api/machines/:id`: Delete profile.

---

## 5. Tool Library
- `GET /api/tools`: List all tools with material presets.
- `GET /api/tools/:id`: Retrieve tool by ID.
- `POST /api/tools`: Add a new tool.
- `PUT /api/tools/:id`: Update tool properties.
- `DELETE /api/tools/:id`: Delete a tool and its presets.

---

## 6. Material Presets
- `GET /api/materials`: List all presets (optionally filtered with `?tool_id=1`).
- `GET /api/materials/:id`: Retrieve preset by ID.
- `POST /api/materials/tool/:tool_id`: Create preset attached to a tool.
- `PUT /api/materials/:id`: Update preset.
- `DELETE /api/materials/:id`: Delete preset.

---

## 7. Error Handling Format

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
