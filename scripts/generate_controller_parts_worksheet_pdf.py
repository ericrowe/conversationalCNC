#!/usr/bin/env python3
"""Generate printable 1-page Barn Shop Parts & Caliper Worksheet PDF for Plan 11."""

import subprocess
import tempfile
from pathlib import Path

TYPST_SOURCE = r"""
#set page(
  paper: "us-letter",
  margin: (top: 0.42in, bottom: 0.42in, left: 0.45in, right: 0.45in),
  header: align(right)[
    #text(size: 8pt, fill: luma(110))[
      *Standardized CNC Controller Box (Plan 11)* — Barn Shop Parts & Caliper Measurement Worksheet
    ]
  ],
  footer: [
    #line(length: 100%, stroke: 0.5pt + luma(180))
    #grid(
      columns: (1fr, 1fr),
      align(left)[#text(size: 8pt, fill: luma(110))[Target: Box \#1 (X-Carve Arduino Uno + Daughterboard + 24V PSU)]],
      align(right)[#text(size: 8pt, fill: luma(110))[Page #context counter(page).display("1 of 1", both: true)]]
    )
  ]
)

#set text(font: "Helvetica", size: 9.2pt, fill: rgb("#111827"))
#set par(leading: 0.48em)

#block(
  width: 100%,
  fill: rgb("#1e293b"),
  inset: (x: 12pt, y: 9pt),
  radius: 4pt,
)[
  #text(size: 14pt, weight: "bold", fill: white)[CNC Controller Box — Simplified Barn Parts & Measurement Worksheet] \
  #v(2pt)
  #text(size: 8.8pt, fill: rgb("#cbd5e1"))[
    Simplified topology: Rear Switched AC Inlet + USB-Powered Arduino + Front Power LED & Probe + Recessed Top E-Stop.
  ]
]

#v(5pt)

#text(size: 10.5pt, weight: "bold", fill: rgb("#0f172a"))[1. Parts to Locate & Measure with Calipers (For Enclosure CAD)]
#v(2pt)

#table(
  columns: (24pt, 1.55fr, 34pt, 2.25fr),
  inset: (x: 6pt, y: 7pt),
  align: (center + horizon, left + horizon, center + horizon, left + horizon),
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (x, y) => if y == 0 { rgb("#f1f5f9") } else if calc.even(y) { rgb("#f8fafc") } else { white },

  [*Got*], [*Component Type & Purpose*], [*Qty*], [*Caliper Measurements to Write Down (`mm`)*],

  [$square$], [
    *1. Switched 120V AC Wall Power Inlet* \
    #text(size: 8pt, fill: luma(90))[Rear Panel: IEC C14 3-prong socket with built-in main rocker switch]
  ], [*1*], [
    Panel Cutout W × H: `_______ × _______ mm` \
    Mounting Screw Spacing (C-to-C): `_______ mm` | Internal Depth: `_______ mm`
  ],

  [$square$], [
    *2. USB-B Female Panel-Mount Patch Cable* \
    #text(size: 8pt, fill: luma(90))[Rear Panel USB-B socket to internal Arduino USB-B port (Data + 5V)]
  ], [*1*], [
    Mounting Ear Screw Spacing (C-to-C): `_______ mm` (usually ~28–30mm) \
    Rect/D-Cutout W × H: `_______ × _______ mm` | Cable Length: `_______ cm`
  ],

  [$square$], [
    *3. Front Panel Power Indicator LED* \
    #text(size: 8pt, fill: luma(90))[Front Panel: `Power ON` status indicator]
  ], [*1*], [
    Mounting Hole Ø: `_______ mm` (e.g. 6 / 8 / 10 / 12mm) \
    Rated Voltage: $square$ 24V  $square$ 12V  $square$ 5V  $square$ Bare 2V LED (needs resistor)
  ],

  [$square$], [
    *4. Existing X-Carve 24V DC Power Supply + Fan* \
    #text(size: 8pt, fill: luma(90))[120V AC in, 24V DC out (with integrated forced-air cooling fan)]
  ], [*1*], [
    PSU Brick L × W × H: `_______ × _______ × _______ mm` \
    Mounting Screw Hole Pattern / Spacing: `_______________________` \
    Fan Location & Airflow Direction (`Intake` vs `Exhaust`): `______________`
  ],

  [$square$], [
    *5. Arduino Uno + Motor Daughterboard + Fan* \
    #text(size: 8pt, fill: luma(90))[Existing X-Carve controller stack + integrated cooling fan]
  ], [*1*], [
    Total Stack L × W × H (including fan): `_______ × _______ × _______ mm` \
    Fan Position & Airflow Direction (`Down onto chips` vs `Side`): `_________`
  ],
)

#v(8pt)

#text(size: 10.5pt, weight: "bold", fill: rgb("#0f172a"))[2. Known Parts to Grab from Bins (Dimensions Already Locked)]
#v(2pt)

#table(
  columns: (24pt, 1.4fr, 34pt, 1.8fr),
  inset: (x: 6pt, y: 6pt),
  align: (center + horizon, left + horizon, center + horizon, left + horizon),
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (x, y) => if y == 0 { rgb("#f1f5f9") } else if calc.even(y) { rgb("#f8fafc") } else { white },

  [*Got*], [*Component*], [*Qty*], [*Panel Location & Cutout Spec*],

  [$square$], [*GX16-4* (4-Pin 16mm Aviation Pairs — Kit `B07F5B5LLX`)], [*3 pairs*], [Rear Panel: `X-MOTOR`, `Y-MOTOR`, `Z-MOTOR` (*16.0 mm* holes)],
  [$square$], [*GX16-6* (6-Pin 16mm Aviation Pairs — Kit `B07F5FJVHD`)], [*2 pairs*], [Rear Panel: `LIMITS-LOW (MIN)` & `LIMITS-HIGH (MAX)` (*16.0 mm* holes)],
  [$square$], [*GX16-2* (2-Pin 16mm Aviation Pair — Kit `B07F5B5LLX`)], [*1 pair*], [Front Panel: `TOUCH PROBE` (*16.0 mm* hole)],
  [$square$], [*22mm Red Mushroom Latching E-Stop* (`B00548585A`)], [*1*], [Top Panel: Recessed `EMERGENCY STOP` well (*22.0 mm* hole, `1 NO + 1 NC`)],
)

#v(8pt)

#text(size: 10.5pt, weight: "bold", fill: rgb("#0f172a"))[3. Small Wiring Hardware & Consumables (Check Stock for Build Phase)]
#v(2pt)

#block(
  width: 100%,
  fill: rgb("#f8fafc"),
  stroke: 0.5pt + rgb("#cbd5e1"),
  inset: 7pt,
  radius: 4pt,
)[
  #grid(
    columns: (1fr, 1fr),
    row-gutter: 5pt,
    [$square$ *Spade Crimp Terminals* (Female quick-disconnects for Switched AC Inlet)],
    [$square$ *Fork / Ring Terminals* (For 24V PSU screw terminal strip & E-Stop screws)],
    [$square$ *16–18 AWG Stranded Wire* (AC Mains, 24V Motor Supply, Stepper Motor leads)],
    [$square$ *20–22 AWG Stranded Wire* (Limit Switches, Touch Probe, Power LED)],
    [$square$ *Heat-Shrink Tubing Assortment* (For insulating GX16 solder cups)],
    [$square$ *4× 0.1 µF Ceramic Capacitors* (Optional EMI noise filter on X/Y/Z Limit & Probe pins)],
  )
]

#v(8pt)
#block(
  width: 100%,
  stroke: (paint: rgb("#94a3b8"), thickness: 0.6pt, dash: "dashed"),
  inset: 8pt,
  radius: 4pt,
)[
  *Additional Barn Notes / Part Numbers Found:* \
  #v(36pt)
]
"""

def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    out_pdf = repo_root / "docs" / "CNC_Controller_Box_Shop_Parts_Worksheet.pdf"
    with tempfile.NamedTemporaryFile(suffix=".typ", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(TYPST_SOURCE)
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            ["/opt/homebrew/bin/typst", "compile", str(tmp_path), str(out_pdf)],
            check=True,
        )
        print(f"Generated {out_pdf} ({out_pdf.stat().st_size:,} bytes)")
    finally:
        tmp_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
