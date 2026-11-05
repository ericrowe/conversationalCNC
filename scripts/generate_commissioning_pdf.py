#!/usr/bin/env python3
"""Generate the printable 2-page Conversational CNC Software Feature Exerciser & Bit-Saver Checklist PDF."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

TYPST_SOURCE = r"""
#set page(
  paper: "us-letter",
  margin: (top: 0.40in, bottom: 0.40in, left: 0.45in, right: 0.45in),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 7.6pt, fill: rgb("#475569"), font: "Helvetica")
      #grid(
        columns: (1fr, auto),
        align(left)[*Conversational CNC — Software Feature Exerciser & Bit-Saver Checklist* (`voltron.local`)],
        align(right)[Build: `49a679e` (Plan 09)]
      )
      #v(-4pt)
      #line(length: 100%, stroke: 0.5pt + rgb("#cbd5e1"))
    ]
  },
  footer: context [
    #line(length: 100%, stroke: 0.5pt + rgb("#cbd5e1"))
    #v(2pt)
    #set text(size: 7.6pt, fill: rgb("#475569"), font: "Helvetica")
    #grid(
      columns: (1fr, auto),
      align(left)[BIT-SAVER RULE: Always Use Split Tools & Re-Probe Z0 After Swapping Collet Bits!],
      align(right)[Page #counter(page).display("1 of 1", both: true)]
    )
  ]
)

#set text(font: "Helvetica", size: 8.1pt, fill: rgb("#0f172a"))
#set par(leading: 0.40em, spacing: 0.46em)
#set list(spacing: 0.42em, body-indent: 4pt)

#let cb = box(width: 7.8pt, height: 7.8pt, stroke: 1pt + rgb("#0f172a"), radius: 1.5pt, baseline: 1.1pt)

#let section_banner(title, subtitle, bg: rgb("#0f172a"), fg: white) = block(
  width: 100%,
  fill: bg,
  inset: (x: 8pt, y: 4pt),
  radius: 3pt,
  below: 4pt,
  above: 5pt,
)[
  #grid(
    columns: (1fr, auto),
    align(left + horizon)[#text(fill: fg, weight: "bold", size: 8.9pt)[#title]],
    align(right + horizon)[#text(fill: rgb("#cbd5e1"), size: 7.4pt, weight: "bold")[#subtitle]]
  )
]

// ==================== PAGE 1 ====================
#block(
  width: 100%,
  fill: rgb("#0f172a"),
  inset: (x: 12pt, y: 8.5pt),
  radius: 4pt,
  below: 5pt,
)[
  #grid(
    columns: (1fr, auto),
    [
      #text(fill: white, size: 14pt, weight: "bold")[CONVERSATIONAL CNC — SOFTWARE FEATURE & BIT-SAVER CHECKLIST] \
      #v(2pt)
      #text(fill: rgb("#94a3b8"), size: 8.2pt)[Barn Host (`http://voltron.local/`)  •  Walkthrough of Every Software Generator, Probing Macro & Offset Calculation]
    ],
    align(right + horizon)[
      #box(fill: rgb("#1e293b"), stroke: 0.8pt + rgb("#475569"), inset: 5pt, radius: 3pt)[
        #text(fill: rgb("#38bdf8"), size: 7.8pt, weight: "bold")[SW Build: `49a679e`] \
        #text(fill: rgb("#e2e8f0"), size: 7.3pt)[289/289 Tests Passed]
      ]
    ]
  )
]

#block(
  width: 100%,
  fill: rgb("#fffbeb"),
  stroke: 1pt + rgb("#d97706"),
  inset: 6pt,
  radius: 3pt,
  below: 5pt,
)[
  #text(fill: rgb("#92400e"), weight: "bold", size: 8.4pt)[TOP 5 CARBIDE BIT-SAVER RULES WHEN TESTING SOFTWARE PATHS:]
  #v(1.5pt)
  #text(fill: rgb("#78350f"), size: 7.9pt)[
    *1. Re-Probe $Z_0$ After Every Collet Swap*: On the DeWalt DWP611, every bit sticks out a different length. Always split multi-tool jobs (*Split Tools*) and re-probe $Z_0$ after changing bits. \
    *2. Air-Cut at $Z_0 = +20 "mm"$ First*: Jog $Z$ up $20 "mm"$ in the air and click *Zero XYZ* to watch the first plunge, lead-in arc, and final retract before cutting stock. \
    *3. Never Straight-Plunge Flat Endmills in Brass/Alu*: Always select *Helical Ramp* on pockets and *90° Tangential Arc* lead-in/out on contours & chamfers. \
    *4. Check Clamp Clearance*: Default `safe_z_retract` is `5.0 mm`. If using tall step clamps, raise `retract_z` / `safe_z_retract` to `15.0 mm` so rapids don't clip a clamp. \
    *5. Tap Touch Plate in Mid-Air First*: Always tap the plate to the bit during the start of a `G38.2` probe descent to verify the alligator clip has continuity before the bit reaches the plate.
  ]
]

#grid(
  columns: (1.15fr, 0.85fr),
  gutter: 8pt,
  block(
    width: 100%,
    fill: rgb("#f8fafc"),
    stroke: 0.7pt + rgb("#cbd5e1"),
    inset: 5pt,
    radius: 3pt,
  )[
    #text(weight: "bold", size: 8.1pt, fill: rgb("#1e3a8a"))[VOLTRON ENDPOINTS & ACTIVE PROFILE DEFAULTS]
    #v(2pt)
    #table(
      columns: (auto, 1fr),
      stroke: 0.4pt + rgb("#cbd5e1"),
      inset: 3pt,
      fill: (x, y) => if x == 0 { rgb("#f1f5f9") } else { white },
      [*Machining Studio UI*], [`http://voltron.local/` (Chrome / Edge Web Serial)],
      [*7" Kiosk Status HUD*], [`http://voltron.local/status` (Snapshot & Power)],
      [*Machine Profile*], [`units: mm` (`G21`)  •  `dialect: grbl`  •  `safe_z: 5.0 mm`],
      [*Spindle Policy*], [`manual_switch` (`dewalt_dwp611`, `require_pause: true`)],
      [*Multi-Tool Jobs*], [Use *Split Tools* (`/api/transform/split-tools`) + Re-Zero $Z_0$],
    )
  ],
  block(
    width: 100%,
    fill: rgb("#f8fafc"),
    stroke: 0.7pt + rgb("#cbd5e1"),
    inset: 5pt,
    radius: 3pt,
  )[
    #text(weight: "bold", size: 8.1pt, fill: rgb("#1e3a8a"))[DEWALT DWP611 ROUTER DIAL TABLE (PLAN 03)]
    #v(2pt)
    #table(
      columns: (auto, auto, 1fr),
      stroke: 0.4pt + rgb("#cbd5e1"),
      inset: 3pt,
      fill: (x, y) => if y == 0 { rgb("#e2e8f0") } else { white },
      [*Dial*], [*RPM*], [*Material & Bit Target*],
      [`1.0`], [`16,000`], [C360 Brass Roughing, Aluminum, Plastics],
      [`2.0`], [`18,200`], [C360 Brass Chamfering (`90°` V-Bit), Hardwood],
      [`3.0`], [`20,400`], [MDF, Plywood, General `1/4"` Endmill],
      [`4.0`], [`22,600`], [`1/8"` Endmill Finishing, V-Bit Engraving],
      [`5–6`], [`24.8k–27k`], [Fine Single-Line Engraving Only],
    )
  ]
)

#section_banner("1. HOST, PROFILES, TOOL LIBRARY, FEEDS/SPEEDS & JOG/DRO", "UI & Web Serial Check")

- #cb *1.1 7" Touchscreen Status HUD (`/status`)*: Confirm `ONLINE` badge, CPU temp, and click *Backup Snapshot* to verify SQLite backup.
- #cb *1.2 Machine Profile & Tool Library (`/machines` & `/tools`)*: Confirm active X-Carve profile (`mm`, `grbl`, `manual_switch`, `safe_z_retract = 5.0 mm`, plate thickness `14.85 mm`). Check that your `3.175 mm` (`1/8"`), `6.35 mm` (`1/4"`), `90°` V-bit, and thread mill diameters/flutes match your physical bits.
- #cb *1.3 Feeds & Speeds Calculator (`Feeds & Speeds` Tab)*: Test *C360 Brass* with a `3.175 mm` 2-flute bit (`0.3 mm` stepdown, `0.5 mm` stepover). Verify radial chip-thinning boost, stickout deflection warning ($> 4.5 times D$), and DeWalt dial setting (`Dial 1–2`).
- #cb *1.4 Web Serial Connect, Jog (`J`) & `Go To Origin` Bit-Saver Check*:
  - Connect USB Web Serial (`115200` baud). Press `J` to open Jog & DRO. Test `+X` (Right), `+Y` (Back), `+Z` (Up) buttons and keyboard arrow keys.
  - #cb Click *Zero XYZ* (`G10 L20 P1 X0 Y0 Z0`), jog down to `X20 Y20 Z-5` (in air), and click *Go To Origin*: confirm the software *lifts $Z$ to `Z5.0` first* before moving $X Y$ (so it never drags a bit across the stock!).

#section_banner("2. PROBING MACROS & SURFACE MESH LEVELING", "Touch Plate & Warper Check")

- #cb *2.1 Z-Touch Plate Macro (Mid-Air Tap → Surface Paper Check)*:
  - Clip ground lead to collet. Start *Z-Touch Plate Macro* and tap plate to bit in mid-air during the `150 mm/min` descent: confirm instant stop, `1.5 mm` retract, `25 mm/min` slow touch, `G10 L20 P1 Z<thickness>`, and `20 mm` lift.
  - Place plate on stock, run macro, remove plate, and jog slowly to `Z0.000` (`F100`): confirm paper drag (`~0.10 mm`) under bit tip.
- #cb *2.2 4-Quadrant Corner XYZ & Bore/Boss Center Probing (Plan 05)*:
  - Run *Corner XYZ* (`front_left`) with bit diameter entered; jog to `X0 Y0 Z5` and confirm bit center sits directly over the physical corner.
  - Test *Inside Bore Center* or *Outside Boss Center* 4-point probe inside a scrap ring/cylinder; confirm it rapids to the exact center at safe $Z$.
- #cb *2.3 Surface Mesh Leveling & G-Code Warper (`Mesh Level` Tab)*:
  - Generate a `3 × 3` probe point grid (`40 × 40 mm`), parse sample probe log heights, and warp an engraving program. Inspect in the 3D backplotter to confirm smooth $Z$ interpolation with zero sudden downward spikes.

#section_banner("3. CONVERSATIONAL GENERATORS WALK-THROUGH (PREVIEW + AIR-CUT AT Z0 = +20 MM)", "Exercise Every Generator Tab")

#table(
  columns: (auto, 1.15fr, 1.35fr, 1.6fr),
  stroke: 0.45pt + rgb("#94a3b8"),
  inset: 3.6pt,
  fill: (x, y) => if y == 0 { rgb("#f1f5f9") } else { white },
  [*Step*], [*Generator Tab*], [*Test Inputs to Exercise*], [*Bit-Saver Check (3D Backplotter / G-Code / Air Cut)*],
  [#cb *3.1*], [*Plunge & Peck Drill*], [4-hole grid, `depth = -6 mm`, `peck = 1.5 mm`, `retract_z = 5 mm`], [Grbl expands `G83` to linear `G1`/`G0` (no `error:20`). Lifts to `Z5.0` before every $X Y$ rapid between holes.],
  [#cb *3.2*], [*Helical Thread Mill*], [Internal `M6×1.0`, `bottom_to_top` climb, `2` radial passes + spring pass], [Enters/exits center via `180°` tangential helical arc (`G2`/`G3 I J Z`) so thread teeth never clip the crest on retract.],
  [#cb *3.3*], [*Circular Pocket & Boss*], [`25 mm` pocket (helical entry) & `20 mm` boss from `25 mm` bar stock], [Pocket ramps helically (no flat-endmill plunge). Boss clears outside-in from `25 mm` OD to `20 mm` + finish pass.],
  [#cb *3.4*], [*Rect Pocket & Boss*], [`40 × 30 mm` pocket, `3 mm` corner fillet, `helical_ramp`, `0.2 mm` finish], [Concentric loops respect stepover %, leave `0.2 mm` wall allowance during roughing, then run full-depth finish pass.],
)

#pagebreak()

// ==================== PAGE 2 ====================
#section_banner("3 (CONT.). CONVERSATIONAL GENERATORS WALK-THROUGH", "Exercise Every Generator Tab")

#table(
  columns: (auto, 1.15fr, 1.35fr, 1.6fr),
  stroke: 0.45pt + rgb("#94a3b8"),
  inset: 3.8pt,
  fill: (x, y) => if y == 0 { rgb("#f1f5f9") } else { white },
  [*Step*], [*Generator Tab*], [*Test Inputs to Exercise*], [*Bit-Saver Check (3D Backplotter / G-Code / Air Cut)*],
  [#cb *3.5*], [*Linear Slot & Surfacing*], [`10 mm` wide slot (`6.35 mm` bit) & `60 × 60 mm` zig-zag surfacing (`overtravel = 3 mm`)], [Slot cuts centerline then bilateral walls at each stepdown. Surfacing reversals occur `3 mm` clear outside stock edges.],
  [#cb *3.6*], [*2.5D Profile Contour (`V2-005`)*], [Closed profile (lines + arcs), `side = "left"` (outside), `90°` tangent arc lead-in/out (`R = 2 mm`)], [Quarter-circle tangent entry/exit. Non-tangent convex corners use *constant-radius `G2`/`G3` corner-roll arcs* (no straight-chord gouge).],
  [#cb *3.7*], [*Rect & Circular Chamfer (`V2-004`)*], [`20.0 mm` OD Circular Chamfer, `W = 0.50 mm`, `90°` V-bit (`6.35 mm`), `tip_offset = 0.40 mm`], [Emits `R_path = 9.9000 mm` at `Z_cut = -0.9000 mm`. V-bit dead tip stays `0.40 mm` outside cylinder wall while cutting on `45°` flute.],
  [#cb *3.8*], [*Single-Line Text Engraving*], [Linear + curved arc text (`"VOLTRON"`), `Simplex Sans`, `4×` spline smoothing, `Z = -0.3 mm`], [Tool retracts to `Z5.0` between every disconnected letter stroke; sharp corners ($>= 65 degree$) stay crisp.],
  [#cb *3.9*], [*DXF & SVG CAD Importers*], [Upload `.dxf` bracket + holes and grayscale `.svg` badge (`max_cut_depth = -3.0 mm`)], [DXF chains closed perimeters and drills `CIRCLE` entities. SVG maps grayscale luminance % to proportional stepdowns.],
)

#section_banner("4. TRANSFORMATIONS, ARRAY NESTING, SOFT JAWS & MULTI-OP SEQUENCER", "Program Manipulation & Job Builder")

- #cb *4.1 G-Code Transformations (`Shift`, `Rotate`, `Mirror`, `Feed/Speed Override`, `Split Tools`)*:
  - Test `Shift` (`+10, +10`), `Rotate` (`45°`), and `Mirror` (`X` axis): confirm `Mirror` automatically swaps `G2` ↔ `G3` so climb milling doesn't invert into conventional milling.
  - Test *Feed/Speed Override* (`75%` feed scaling) and *Split Tools* (`/api/transform/split-tools`): confirm a multi-tool job splits into separate per-tool `.nc` files, each with its own header, safe retract, and `M2` footer.
- #cb *4.2 Step-and-Repeat Grid Nesting & Vise Soft Jaws (`Nesting & Jaws` Tab)*:
  - Array a part across a `2 × 2` grid: confirm a full `G0 Z5.0` retract occurs between every part instance so rapids clear fixtures.
  - Generate a *Soft Jaw* clamping cavity with `45°` dogbone corner reliefs: confirm the dogbone overcuts clear the inner corners.
- #cb *4.3 Multi-Operation Job Sequencer (`Job Builder` Drawer — `R2-001`–`V2-006`)*:
  - Queue a 3-step job (`Op 1: T1 rough`, `Op 2: T2 drill`, `Op 3: T1 finish/chamfer`) with `optimize_tool_order = true`.
  - #cb Confirm authored sequence `[Op 1, Op 2, Op 3]` is preserved (never runs finish/chamfer ahead of Op 2 unless marked `independent: true`).
  - #cb Confirm manual router mode emits `(MANUAL ROUTER: Set DeWalt DWP611 dial to ...)` + `M0` pause before plunging, strips inner sub-op `M2`/`M30`/`M6` lines, and *always retracts `G0 Z5.0000` BEFORE `M5`* at every tool change and footer.

#section_banner("5. SOFT PROOF & 20 MM BRASS TRUMPET FINGER BUTTON CHECKLIST (WAX / FOAM → BRASS)", "Caliper Offset Proof Before Brass")

#block(
  width: 100%,
  fill: rgb("#eff6ff"),
  stroke: 1pt + rgb("#2563eb"),
  inset: 6pt,
  radius: 3pt,
  below: 5pt,
)[
  #text(weight: "bold", size: 8.6pt, fill: rgb("#1e3a8a"))[20 MM BRASS TRUMPET FINGER BUTTON — WORKFLOW & BIT-PROTECTION REMINDER]
  #v(1.5pt)
  #text(size: 8pt, fill: rgb("#1e293b"))[
    Run the Finger Button in *machinable wax or rigid foam* first to confirm your collet runout and V-bit $Z_0$ offset before chucking C360 brass: \
    • *File 1 (Tool 1 — `3.175 mm` 1/8" Flat Endmill, DeWalt Dial `1–2`)*: Op 1 Center Bore/Thread Prep + Op 2 Outer `20.00 mm` OD Boss/Contour (`R_nom = 10.0 mm`, `stepdown = 0.30 mm`, `finish_allowance = 0.15 mm` + spring pass, `90°` tangential arc lead-in/out `R = 2.0 mm`). \
    • *Swap Collet to Tool 2 (`90°` `6.35 mm` V-Bit) & RE-PROBE $Z_0$ ON TOP SURFACE WITH TOUCH PLATE!* \
    • *File 2 (Tool 2 — `90°` V-Bit, DeWalt Dial `2`)*: Op 3 Outer Circular Chamfer (`diameter = 20.0 mm`, `chamfer_width = 0.50 mm`, `vbit_angle_deg = 90.0`, `tip_offset = 0.40 mm`, CW climb → `R_path = 9.9000 mm`, `Z_cut = -0.9000 mm`).
  ]
]

#table(
  columns: (auto, 1.25fr, auto, 1.05fr, 1.55fr),
  stroke: 0.45pt + rgb("#94a3b8"),
  inset: 4pt,
  fill: (x, y) => if y == 0 { rgb("#f1f5f9") } else { white },
  [*Check*], [*Test Cut & Feature*], [*Target Caliper Spec*], [*Measured Value*], [*If Off: Quick Adjustment*],
  [#cb *5.1a*], [*Outside Boss Offset Check* (`40.00 mm` Boss, `6.35 mm` bit)], [$40.00 plus.minus 0.05 "mm"$], [`OD: ___________ mm`], [Reads `33.65 mm`: wrong `side` (`right` vs `left`). Reads `40.15 mm`: adjust bit dia in Tool Library.],
  [#cb *5.1b*], [*Inside Pocket Offset Check* (`40.00 mm` Bore, `6.35 mm` bit)], [$40.00 plus.minus 0.05 "mm"$], [`ID: ___________ mm`], [Reads `46.35 mm`: wrong `side`. Tight fit: reduce `finish_allowance` or add spring pass.],
  [#cb *5.2a*], [*Trumpet Button Outer OD* (Wax/Foam, `3.175 mm` bit)], [$20.00 plus.minus 0.05 "mm"$], [`OD: ___________ mm`], [Witness mark on wall: use `tangential_arc` lead-in (`R = 2.0 mm`) + `spring_pass = true`.],
  [#cb *5.2b*], [*Trumpet Button Top Land Dia* (Inner rim of `0.50 mm` chamfer)], [$19.00 plus.minus 0.05 "mm"$], [`Top: __________ mm`], [Top land $< 18.90 "mm"$: V-bit $Z_0$ probed too low (or forgot to re-zero $Z_0$ after Tool 1).],
  [#cb *5.2c*], [*Trumpet Button `45°` Chamfer* (`R_path = 9.90`, `Z = -0.90`)], [$0.50 plus.minus 0.05 "mm"$], [`Bevel: ________ mm`], [Step ridge on outer wall: check `vbit_angle_deg = 90` and `tip_offset = 0.40 mm`.],
  [#cb *5.3*], [*C360 Brass Trumpet Button* (`0.25–0.35 mm` stepdown)], [$20.00 "mm"$ OD / $19.00 "mm"$ Top], [`OD: _____ Top: _____`], [Chatter on chamfer: lower feed to `250–350 mm/min` and run a zero-offset spring pass.],
)

#v(4pt)
#block(
  width: 100%,
  fill: rgb("#f8fafc"),
  stroke: 0.7pt + rgb("#cbd5e1"),
  inset: 7pt,
  radius: 3pt,
)[
  #text(weight: "bold", size: 8.3pt, fill: rgb("#334155"))[SHOP NOTES / CALIBRATED BIT DIAMETERS & FEED TUNING:]
  #v(16pt)
  #line(length: 100%, stroke: 0.4pt + rgb("#cbd5e1"))
  #v(16pt)
  #line(length: 100%, stroke: 0.4pt + rgb("#cbd5e1"))
]
"""


def generate_pdf(out_pdf: Path) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    typst_bin = shutil.which("typst") or "/opt/homebrew/bin/typst"
    with tempfile.NamedTemporaryFile("w", suffix=".typ", delete=False, encoding="utf-8") as tmp:
        tmp.write(TYPST_SOURCE)
        tmp_path = Path(tmp.name)
    try:
        subprocess.run([typst_bin, "compile", str(tmp_path), str(out_pdf)], check=True)
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "docs" / "Workshop_CNC_Commissioning_Checklist.pdf"
    generate_pdf(target)
    print(f"Generated printable PDF: {target} ({target.stat().st_size} bytes)")
