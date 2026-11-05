# 🧪 Conversational CNC Software Feature Exerciser & Bit-Saver Checklist

A practical, feature-by-feature workshop walkthrough for exercising every function of the **Conversational CNC Controller (`voltron.local`)** and verifying safe toolpaths before putting expensive carbide bits into stock.

> **Printable 2-Page (Single-Sheet Front/Back) Workshop Checklist**: [`docs/Workshop_CNC_Commissioning_Checklist.pdf`](Workshop_CNC_Commissioning_Checklist.pdf)

---

## 🛡️ Top 5 "Bit-Saver" Rules in Conversational CNC

1. **Always Re-Zero $Z_0$ After Swapping Collet Bits**: On a manual trim router (DeWalt DWP611) without a tool-length sensor, every bit sticks out a different length. Use **Split Tools** (`/api/transform/split-tools`) for multi-tool jobs and re-probe $Z_0$ with the touch plate after every bit change.
2. **Air-Cut New Toolpaths at $Z_0 = +20\text{ mm}$ First**: Jog $Z$ up `20 mm` in the air and click `Zero XYZ` before running unfamiliar operations. Watch the first plunge and final retract.
3. **Never Plunge Flat Endmills Straight into Metal**: Always use **Helical Ramp** entry on pockets and **90° Tangential Arc** lead-in/lead-out on contours and circular chamfers so small bits (`1/8"`, `1/16"`, thread mills) never take a 100% radial shock load on entry.
4. **Verify Retract-Before-Stop & Clamp Clearance**: Every generated footer retracts to `safe_z_retract` (`G0 Z5.0000`) *before* `M5`. If using tall step clamps, increase `safe_z_retract` / `retract_z` (e.g. `15.0 mm`) so rapids clear the clamps.
5. **Mid-Air Touch Plate Tap Before Every Probe**: Always tap the touch plate to the bit in mid-air during the start of a probe descent to confirm the ground clip has continuity before the bit reaches the brass plate.

---

## 1. Host, Machine Profile, Tool Library & Web Serial Jog (`voltron.local`)

- [ ] **1.1 7" Touchscreen Status HUD (`http://voltron.local/status`)**:
  - Verify status shows `ONLINE`, normal Pi temperature, and active profile. Test **Backup Snapshot** button.
- [ ] **1.2 Machine Profile & Tool Library (`http://voltron.local/machines` & `/tools`)**:
  - Confirm active profile: `units = mm` (`G21`), `dialect = grbl`, `spindle_control_type = manual_switch` (`dewalt_dwp611`, `require_pause = true`), `safe_z_retract = 5.0 mm`, and calibrated touch plate thickness (`14.85 mm`).
  - Confirm your carbide bits (`3.175 mm` 1/8" endmill, `6.35 mm` 1/4" endmill, `90°` V-bit, thread mill) have accurate diameters and conservative stepdown/plunge presets in the Tool Library.
- [ ] **1.3 Feeds & Speeds Physics Calculator (`⚡ Feeds & Speeds`)**:
  - Select **C360 Brass** or **6061 Aluminum** with a `3.175 mm` (1/8") 2-flute endmill, `0.3 mm` stepdown, and `0.5 mm` stepover.
  - Confirm radial chip-thinning compensation, spindle power estimate, stickout deflection check, and DeWalt DWP611 dial recommendation (`Dial 1–2` = `16,000–18,200 RPM`).
- [ ] **1.4 Web Serial Connection, Jog Pendant (`J`) & `Go To Origin`**:
  - Click **Connect Machine** (`115200` baud). Press `J` to open the Jog & DRO drawer.
  - Test `1 mm` and `10 mm` jog steps (`+X` Right, `+Y` Back, `+Z` Up) and keyboard arrow/PageUp/PageDown keys.
  - Click **Zero XYZ** (`G10 L20 P1 X0 Y0 Z0`), jog to `X20 Y20 Z-5` (in air), and click **Go To Origin**:
    - **Bit-Saver Check**: Confirm the software **lifts $Z$ to `Z5.0` first** before moving $XY$ to `(0, 0)`.

---

## 2. Probing Macros & Surface Mesh Leveling (`🎯 Probe & Zero` & `🗺️ Mesh Level`)

- [ ] **2.1 Z-Touch Plate Macro (Mid-Air Tap Test $\to$ Surface Zero)**:
  - Clip ground lead to collet. Start **Z-Touch Plate Macro** and tap plate to bit in mid-air during the `150 mm/min` search: confirm instant stop, `1.5 mm` lift, `25 mm/min` slow touch, `G10 L20 P1 Z<thickness>`, and `20 mm` retract.
  - Place plate on stock, run macro, remove plate, and jog slowly to `Z0.000` (`F100`): confirm paper drag (`~0.10 mm`).
- [ ] **2.2 4-Quadrant Corner XYZ & Bore/Boss Center Probing (Plan 05)**:
  - Test **Corner XYZ** (`front_left`) with your bit diameter entered; jog to `X0 Y0 Z5` and confirm bit center sits directly over the stock corner.
  - Test **Inside Bore Center** or **Outside Boss Center** 4-point probe inside a test ring/cylinder; confirm it rapids to the exact center at safe $Z$.
- [ ] **2.3 Surface Mesh Leveling & G-Code Warper (`🗺️ Mesh Level`)**:
  - Generate a `3 × 3` probe point grid over a `40 × 40 mm` area (`POST /api/mesh/generate-points` & `/probe-macro`).
  - Load sample probe log data and warp a flat engraving toolpath (`/api/mesh/warp-gcode`).
  - **Bit-Saver Check**: Inspect warped G-code in the 3D backplotter to confirm smooth interpolated $Z$ adjustments with no sudden negative $Z$ spikes.

---

## 3. Conversational Operations Walk-Through (Preview + Air-Cut at $Z_0 = +20\text{ mm}$)

Set $Z_0$ at **$+20\text{ mm}$ in the air** (`Zero XYZ`). For each conversational tab below, generate the toolpath, inspect it in the **3D Backplotter** + **G-Code Hints Inspector**, and stream in air:

| # | Conversational Operation | Test Parameters to Exercise | Bit-Saver Verification Check |
|---|---|---|---|
| **3.1** | **Straight Plunge & Peck Drilling** | 4-hole grid, `target_depth_z = -6.0 mm`, `peck_depth = 1.5 mm`, `retract_z = 5.0 mm`, `dwell = 0.5 s` | `[  ]` Grbl expands `G83` into linear `G1`/`G0` moves (no `error:20`). Tool fully retracts to `Z5.0` before every $XY$ move between holes. |
| **3.2** | **Helical Thread Milling** | Internal `M6×1.0` (or external stud), `bottom_to_top` climb, `radial_passes = 2`, `spring_passes = 1` | `[  ]` Enters and exits hole center via `180°` tangential helical arc (`G2`/`G3 I J Z`) so thread mill teeth never clip the thread crest on retract. |
| **3.3** | **Circular Pocket & Cylindrical Boss** | `25 mm` pocket (helical entry) & `20 mm` cylindrical boss from `25 mm` bar stock (`stepdown = 0.4 mm`) | `[  ]` Pocket ramps in helically (no straight flat-endmill plunge). Boss clears outside-in from `25 mm` stock boundary down to `20 mm` OD + finish pass. |
| **3.4** | **Rectangular Pocket & Raised Boss** | `40 × 30 mm` pocket with `3 mm` corner fillet, `helical_ramp`, `0.2 mm` wall finish allowance | `[  ]` Concentric clearing loops respect `stepover_percent`, leave `0.2 mm` wall stock during roughing, and run a clean full-depth finish pass. |
| **3.5** | **Linear Slotting & Surfacing** | `10 mm` wide slot (`6.35 mm` bit, `stepdown = 1.0 mm`) & `60 × 60 mm` zig-zag surfacing (`overtravel = 3 mm`) | `[  ]` Slot cuts centerline then bilateral walls at each stepdown depth. Surfacing turnaround happens outside stock edge by `overtravel`. |
| **3.6** | **2.5D Profile / Contour Milling (`V2-005`)** | Closed profile with lines + arcs, `side = "left"` (outside), `90°` tangential arc lead-in/out (`R = 2.0 mm`) | `[  ]` Smooth quarter-circle tangent lead-in/out. Non-tangent convex corners use **constant-radius `G2`/`G3` corner-roll arcs** (zero corner gouging or load spikes). |
| **3.7** | **Rectangular & Circular V-Bit Chamfering (`V2-004`)** | `20.0 mm` OD Circular Chamfer, `W = 0.50 mm`, `90°` V-bit (`6.35 mm`), `tip_offset = 0.40 mm` | `[  ]` Programmed path is `R_path = 9.9000 mm` at `Z_cut = -0.9000 mm`. Dead tip of V-bit stays `0.40 mm` clear of the cylinder wall while cutting on the `45°` flute. |
| **3.8** | **Single-Line Vector Text Engraving** | Linear + curved arc text (`"VOLTRON"`), `Simplex Sans`, `4×` spline smoothing, `target_depth_z = -0.3 mm` | `[  ]` Tool lifts to `retract_z` (`Z5.0`) between every disconnected letter stroke; sharp corners ($\ge 65^\circ$) remain crisp. |
| **3.9** | **DXF & SVG Vector CAD Importers** | Upload sample `.dxf` part outline + holes and grayscale `.svg` artwork (`max_cut_depth = -3.0 mm`) | `[  ]` DXF chains closed loops and drills `CIRCLE` entities. SVG maps grayscale luminance % to proportional stepdown depths cleanly. |

---

## 4. Transformations, Array Nesting, Soft Jaws & Job Sequencer

- [ ] **4.1 G-Code Transformations (`Shift`, `Rotate`, `Mirror`, `Feed/Speed Override`, `Split Tools`)**:
  - Test `Shift` (`+10, +10`), `Rotate` (`45°`), and `Mirror` (`X` axis): confirm `Mirror` automatically swaps `G2` $\leftrightarrow$ `G3` so climb milling doesn't invert.
  - Test **Feed/Speed Override** (`75%` feed scaling for a cautious first pass in metal).
  - Test **Multi-Tool Program Splitter** (`/api/transform/split-tools`): confirm a 2-tool program splits into two standalone `.nc` files, each with its own complete header, safe retract, and `M2` footer.
- [ ] **4.2 Step-and-Repeat Grid Nesting & Vise Soft Jaws (`📦 Nesting & Jaws`)**:
  - Array a single-part program across a `2 × 2` grid: confirm a full `G0 Z5.0` retract occurs between every part instance.
  - Generate a **Soft Jaw** clamping cavity with `45°` dogbone corner reliefs: confirm the dogbone overcuts clear the inner corners so rectangular stock seats flush.
- [ ] **4.3 Multi-Operation Job Sequencer (`📋 Job Builder` — `R2-001`–`V2-006`)**:
  - Queue a 3-step job (`Op 1: T1 rough`, `Op 2: T2 drill`, `Op 3: T1 finish/chamfer`) with `optimize_tool_order = true`.
  - [ ] Confirm authored sequence `[Op 1, Op 2, Op 3]` is preserved (never runs finish/chamfer before intermediate ops unless marked `independent: true`).
  - [ ] Confirm manual router mode emits `(MANUAL ROUTER: Set DeWalt DWP611 dial to ...)` + `M0` pause before plunging, strips inner sub-op `M2`/`M30`/`M6` lines, and **retracts `G0 Z5.0000` BEFORE `M5`** at every tool change and program end.

---

## 5. Soft Proof & 20 mm Brass Trumpet Finger Button Checklist (Wax / Foam $\to$ Brass)

Before cutting C360 brass, run a quick caliper check in **machinable wax, rigid foam, or scrap MDF** to confirm cutter-radius and V-bit chamfer offsets on your specific collet/bit setup:

| Proof Cut | Operation & Tool Setup | Target Caliper Spec | Measured Value | Diagnostic Fix If Off |
|---|---|---|---|---|
| **5.1 Inside / Outside Offset Check** | `40.00 mm` Boss (Outside) & `40.00 mm` Pocket (Inside) with `6.35 mm` endmill | **$40.00 \pm 0.05\text{ mm}$** (sliding fit) | Boss: `________ mm`<br>Bore: `________ mm` | Off by `±6.35 mm`: wrong `side` selected.<br>Off by `±0.15 mm`: adjust `finish_allowance` or bit diameter in Tool Library. |
| **5.2a Trumpet Button Outer OD** | **Op 2**: `20.00 mm` OD Boss/Contour with `3.175 mm` (1/8") flat endmill (`90°` arc lead-in/out) | **$20.00 \pm 0.05\text{ mm}$** | OD: `________ mm` | Witness mark on wall: increase `lead_in_radius` (`2.0 mm`) or add `spring_pass = true`. |
| **5.2b Trumpet Button Top Chamfer** | **Op 3**: Swap to `90°` V-bit (`6.35 mm`), **re-probe $Z_0$ on top face**, run `0.50 mm` Circular Chamfer (`tip_offset = 0.40 mm`, `R_path = 9.90 mm`, `Z_cut = -0.90 mm`) | Top Land: **$19.00 \pm 0.05\text{ mm}$**<br>Bevel: **$0.50\text{ mm} \times 45^\circ$** | Top: `________ mm`<br>Bevel: `________ mm` | Top land $< 18.90\text{ mm}$: V-bit $Z_0$ was probed too low (or not re-zeroed after Tool 1). Step ridge on wall: check `vbit_angle_deg = 90`. |
| **5.3 C360 Brass Cut** | DeWalt Dial `1–2` (`16k–18k RPM`), `0.25–0.35 mm` stepdown, `0.10 mm` finish pass + spring pass | **$20.00\text{ mm}$ OD / $19.00\text{ mm}$ Top** | OD: `________ mm`<br>Top: `________ mm` | Chatter on brass chamfer: lower feed to `250–350 mm/min` and run a zero-offset spring pass. |
