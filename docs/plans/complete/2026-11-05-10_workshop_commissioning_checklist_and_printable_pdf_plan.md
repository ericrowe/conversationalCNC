# Plan 10: Workshop CNC Software Feature Exerciser, Bit-Saver Checklist & Printable 2-Page PDF

## 1. Goal Description

### Problem Statement & Background Context
Because the physical X-Carve CNC machine has been in operation for over a decade, the workshop checklist does not need hardware build commissioning or multi-person sign-off blocks. Instead, it needs a practical, single-sheet (2-page front/back) **Software Feature Exerciser & Carbide Bit-Saver Checklist** that walks through 100% of the **Conversational CNC Controller (`voltron.local`)** generators, probing macros, transformations, and multi-operation sequencer features to ensure safe toolpath generation and prevent breaking expensive carbide bits.

---

## 2. Architecture & Workflow Diagram

```mermaid
flowchart LR
    Rules["Top 5 Carbide Bit-Saver Rules<br/>• Split Tools & Re-Zero Z0<br/>• Z0 = +20mm Air Cut First<br/>• Helical & 90° Arc Entry"] --> S12["Sections 1 & 2: Host, Profiles,<br/>Feeds/Speeds, Jog/DRO, Touch Plate<br/>& Surface Mesh Warper"]
    S12 --> S3["Section 3: All 9 Generator Tabs<br/>Plunge/Peck, Thread Mill, Pockets/Bosses,<br/>Slots/Surfacing, 2.5D Contour, V-Bit Chamfer,<br/>Engraving, DXF & SVG"]
    S3 --> S4["Section 4: Transformations,<br/>2x2 Grid Nesting, Soft Jaws<br/>& Multi-Op Job Builder"]
    S4 --> S5["Section 5: Wax/Foam Offset Proof<br/>& 20mm Brass Trumpet Button<br/>Caliper Table + Shop Notes"]
```

---

## 3. Code Modifications

### 1. Printable PDF Generator Script ([`scripts/generate_commissioning_pdf.py`](../../../scripts/generate_commissioning_pdf.py))
- **`[NEW]`** [`scripts/generate_commissioning_pdf.py`](../../../scripts/generate_commissioning_pdf.py):
  - Uses Typst (`/opt/homebrew/bin/typst`) to compile the 2-page US-Letter printable PDF [`docs/Workshop_CNC_Commissioning_Checklist.pdf`](../../Workshop_CNC_Commissioning_Checklist.pdf).

---

## 4. Test Updates & Specifications
- *None required* (Pure documentation and printable PDF generation under Invariant 14).

---

## 5. Documentation Updates
- **`[MODIFY]`** [`docs/MACHINE_INTEGRATION_TEST_PLAN.md`](../../MACHINE_INTEGRATION_TEST_PLAN.md)
- **`[NEW]`** [`docs/Workshop_CNC_Commissioning_Checklist.pdf`](../../Workshop_CNC_Commissioning_Checklist.pdf)

---

## 6. Verification Plan
- Verified 2-page US-Letter PDF layout (`180,152 bytes`) and updated Markdown checklist with user validation.
