# Conversational CNC Controller Backend

Stateless, deterministic Python/Flask G-code generator and SQLite configuration manager designed for conversational CNC machining on Raspberry Pi (targeting Grbl / X-Carve and expandable to other machines).

---

> [!CAUTION]
> ### ⚠️ EXPERIMENTAL & UNTESTED SOFTWARE DISCLAIMER
> **Conversational CNC is an active open-source project and is AS OF YET UNTESTED ON PHYSICAL CNC MACHINERY.**
>
> CNC milling machines and routers are capable of severe physical injury, tool breakage, and machine damage if commanded improperly. Always execute the safe startup testing protocol detailed in [docs/MACHINE_INTEGRATION_TEST_PLAN.md](../docs/MACHINE_INTEGRATION_TEST_PLAN.md) (including Spindle UNPLUGGED Air Cuts) before attempting physical cutting on live hardware.

---

## Architecture Highlights
- **Pure Operation Generators**: Zero database or web framework dependencies in the mathematical G-code generation functions (`app/generators/`) covering Straight Plunge Drilling, Peck Drilling, Bolt Circle & Grid Pattern calculation, Helical Thread Milling, Circular Pocketing, Rectangular Pocketing & Boss Machining, Linear Slotting, 2D Chamfering, Surfacing/Facing, Single-Line Vector Text Engraving, 2.5D Arbitrary Profile & Contour Milling with cutter compensation, Step-and-Repeat Array Nesting & Soft Jaw Fixturing, DXF 2D Vector CAD Importer, and SVG 2D Vector CAD Importer with Grayscale Depth Mapping.
- **Machine Probing & Setup Engine**: 2-stage precision Z-touch plate probing macros, 3-axis Corner XYZ touch block macros with tool radius and block lip offset compensation, and machine homing cycles (`$H`).
- **Manual Jog Controller & Machine Control Engine**: Directional incremental jog command generation ($J=G91 for Grbl/Smoothie and G91 G1 for Standard), quick WCS coordinate zeroing (`G10 L20 P1`), and safe 2-stage Return to Work Origin.
- **Multi-Operation Job Program Sequencer**: Assembles multi-operation part programs into a single cohesive `.nc` file with tool change optimization, safe retracts, and coordinate continuity.
- **G-Code Transformations & Multi-Tool Splitter**: Coordinate shifting, rotation around arbitrary pivot centers, axis mirroring with automatic $G2 \leftrightarrow G3$ arc direction reversal, global feed/speed overrides, and standalone tool file extraction.
- **Physics-Based Feeds & Speeds Engine**: Surface speed (SMM/SFM) to RPM conversion, Radial Chip Thinning Factor (RCTF) compensation for light stepovers ($<50\%$ tool diameter), Material Removal Rate (MRR), and spindle cutting power estimation.
- **Modular Post-Processor / Dialect Strategy**: Abstract base class (`app/postprocessors/base.py`) with concrete implementations (`GrblPostProcessor`, `StandardPostProcessor`) to support Grbl (no canned cycles) as well as standard CNC controllers.
- **Router & Spindle Support**: Handles manual trim routers (DeWalt DWP611 with 16,000–27,000 RPM speed dial mapping) and continuous VFD/PWM spindles.
- **Machine Modularity**: Store and dynamically switch active machine profiles (`MachineProfile`) with distinct work envelopes, max feed rates, probe thickness, and controller dialects.
- **Tool Library & Presets**: Manage tools and material feeds/speeds presets in SQLite.

## Documentation
Complete REST API documentation with endpoint schemas, request/response examples, and error formats is available in:
👉 [docs/API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md)

## Getting Started

### 1. Environment Setup
```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Seed Database
```bash
PYTHONPATH=backend python backend/seed.py
```

### 3. Run Automated Tests
```bash
PYTHONPATH=backend pytest backend/tests -v
```
*(Runs 150 automated unit and integration tests)*









### 4. Start Development Server
```bash
python backend/run.py
```
Server runs at `http://localhost:5001`.
