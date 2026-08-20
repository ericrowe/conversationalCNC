/**
 * G-Code Inspector & Plain English Hints Engine (Phase 4 & 5)
 * Translates G-code blocks into plain conversational English and tracks live CNC modal state.
 */

class GCodeInspector {
  constructor() {
    this.modalState = this.getDefaultModalState();
    this.parsedBlocks = [];
    this.activeLineIndex = 0;
  }

  getDefaultModalState() {
    return {
      wcs: "G54",
      plane: "G17 (XY)",
      units: "G21 (mm)",
      distanceMode: "G90 (Absolute)",
      feedMode: "G94 (Units/min)",
      motionMode: "G0 (Rapid)",
      tool: 1,
      spindleState: "M5 (Stopped)",
      spindleRpm: 0,
      feedRate: 0,
      coolant: "M9 (Off)",
    };
  }

  parseProgram(gcodeText) {
    if (!gcodeText) return [];
    const lines = gcodeText.split("\n");
    const blocks = [];
    let curX = 0, curY = 0, curZ = 0;
    let state = this.getDefaultModalState();

    for (let idx = 0; idx < lines.length; idx++) {
      const raw = lines[idx];
      const commentMatch = raw.match(/\((.*?)\)/);
      const comment = commentMatch ? commentMatch[1] : "";
      const cleanCode = raw.replace(/\(.*?\)/g, "").split(";")[0].trim().toUpperCase();

      const block = {
        lineIndex: idx,
        lineNumber: idx + 1,
        rawText: raw,
        cleanCode: cleanCode,
        comment: comment,
        isCommentOnly: cleanCode.length === 0,
        tokens: cleanCode ? cleanCode.split(/\s+/) : [],
        startX: curX,
        startY: curY,
        startZ: curZ,
        endX: curX,
        endY: curY,
        endZ: curZ,
        i: 0, j: 0, r: 0,
        feed: state.feedRate,
        rpm: state.spindleRpm,
        motion: state.motionMode,
        explanation: "",
        modalSnapshot: { ...state },
      };

      if (!block.isCommentOnly) {
        let hasX = false, hasY = false, hasZ = false;
        for (let t of block.tokens) {
          if (t === "G0" || t === "G00") { state.motionMode = "G0 (Rapid)"; block.motion = "G0"; }
          else if (t === "G1" || t === "G01") { state.motionMode = "G1 (Linear Cut)"; block.motion = "G1"; }
          else if (t === "G2" || t === "G02") { state.motionMode = "G2 (CW Arc)"; block.motion = "G2"; }
          else if (t === "G3" || t === "G03") { state.motionMode = "G3 (CCW Arc)"; block.motion = "G3"; }
          else if (t === "G17") { state.plane = "G17 (XY Plane)"; }
          else if (t === "G18") { state.plane = "G18 (XZ Plane)"; }
          else if (t === "G19") { state.plane = "G19 (YZ Plane)"; }
          else if (t === "G20") { state.units = "G20 (Inches)"; }
          else if (t === "G21") { state.units = "G21 (Metric mm)"; }
          else if (t === "G90") { state.distanceMode = "G90 (Absolute)"; }
          else if (t === "G91") { state.distanceMode = "G91 (Incremental)"; }
          else if (t === "G94") { state.feedMode = "G94 (mm/min)"; }
          else if (t === "M3" || t === "M03") { state.spindleState = "M3 (CW Spindle On)"; }
          else if (t === "M4" || t === "M04") { state.spindleState = "M4 (CCW Spindle On)"; }
          else if (t === "M5" || t === "M05") { state.spindleState = "M5 (Spindle Off)"; }
          else if (t === "M8" || t === "M08") { state.coolant = "M8 (Flood On)"; }
          else if (t === "M9" || t === "M09") { state.coolant = "M9 (Coolant Off)"; }
          else if (t.startsWith("X")) { block.endX = parseFloat(t.slice(1)) || curX; hasX = true; }
          else if (t.startsWith("Y")) { block.endY = parseFloat(t.slice(1)) || curY; hasY = true; }
          else if (t.startsWith("Z")) { block.endZ = parseFloat(t.slice(1)) || curZ; hasZ = true; }
          else if (t.startsWith("I")) { block.i = parseFloat(t.slice(1)) || 0; }
          else if (t.startsWith("J")) { block.j = parseFloat(t.slice(1)) || 0; }
          else if (t.startsWith("R")) { block.r = parseFloat(t.slice(1)) || 0; }
          else if (t.startsWith("F")) { state.feedRate = parseFloat(t.slice(1)) || state.feedRate; block.feed = state.feedRate; }
          else if (t.startsWith("S")) { state.spindleRpm = parseInt(t.slice(1), 10) || state.spindleRpm; block.rpm = state.spindleRpm; }
          else if (t.startsWith("T")) { state.tool = parseInt(t.slice(1), 10) || state.tool; }
          else if (t.startsWith("G54") || t.startsWith("G55") || t.startsWith("G56")) { state.wcs = t; }
        }

        curX = block.endX;
        curY = block.endY;
        curZ = block.endZ;
      }

      block.modalSnapshot = { ...state };
      block.explanation = this.generateExplanation(block);
      blocks.push(block);
    }

    this.parsedBlocks = blocks;
    return blocks;
  }

  generateExplanation(block) {
    if (block.isCommentOnly) {
      return block.comment ? `Comment: "${block.comment}"` : "Empty block / blank line";
    }

    const m = block.motion;
    const dx = (block.endX - block.startX).toFixed(2);
    const dy = (block.endY - block.startY).toFixed(2);
    const dz = (block.endZ - block.startZ).toFixed(2);
    const moveDist = Math.hypot(block.endX - block.startX, block.endY - block.startY, block.endZ - block.startZ).toFixed(2);

    if (m === "G0") {
      if (Math.abs(block.endZ - block.startZ) > 0.001 && Math.abs(block.endX - block.startX) < 0.001 && Math.abs(block.endY - block.startY) < 0.001) {
        return block.endZ > block.startZ
          ? `Rapid Retract: Lift Z to ${block.endZ.toFixed(3)}mm clearance (+${dz}mm)`
          : `Rapid Approach: Position Z to ${block.endZ.toFixed(3)}mm (${dz}mm)`;
      }
      return `Rapid Traverse: G0 to (X: ${block.endX.toFixed(3)}, Y: ${block.endY.toFixed(3)}, Z: ${block.endZ.toFixed(3)}) | Travel: ${moveDist}mm`;
    }

    if (m === "G1") {
      if (block.endZ < block.startZ && Math.abs(block.endX - block.startX) < 0.001 && Math.abs(block.endY - block.startY) < 0.001) {
        return `Cutting Plunge: Feed plunge Z down to ${block.endZ.toFixed(3)}mm at ${block.feed} mm/min`;
      }
      return `Linear Cut: Feed to (X: ${block.endX.toFixed(3)}, Y: ${block.endY.toFixed(3)}, Z: ${block.endZ.toFixed(3)}) at ${block.feed} mm/min (Cut length: ${moveDist}mm)`;
    }

    if (m === "G2" || m === "G3") {
      const arcDir = m === "G2" ? "Clockwise (CW)" : "Counter-Clockwise (CCW)";
      const centerX = (block.startX + block.i).toFixed(3);
      const centerY = (block.startY + block.j).toFixed(3);
      const radius = Math.hypot(block.i, block.j).toFixed(3);
      const isHelical = Math.abs(block.endZ - block.startZ) > 0.001;

      if (isHelical) {
        return `${arcDir} Helical Arc to (X: ${block.endX.toFixed(3)}, Y: ${block.endY.toFixed(3)}, Z: ${block.endZ.toFixed(3)}) | Center: (${centerX}, ${centerY}), Radius: ${radius}mm | Descent: ${dz}mm | Feed: ${block.feed} mm/min`;
      }
      return `${arcDir} Circular Arc to (X: ${block.endX.toFixed(3)}, Y: ${block.endY.toFixed(3)}) | Center: (${centerX}, ${centerY}), Radius: ${radius}mm | Feed: ${block.feed} mm/min`;
    }

    if (block.cleanCode.includes("G21") || block.cleanCode.includes("G20") || block.cleanCode.includes("G90")) {
      const snap = block.modalSnapshot || this.modalState || {};
      const wcsMsg = block.cleanCode.includes("G54") ? " | Work Datum G54 Active" : "";
      return `Safety Header: ${snap.units || "G21"} | ${snap.distanceMode || "G90"} | ${snap.plane || "G17"}${wcsMsg}`;
    }


    if (block.cleanCode.includes("G38.2") || block.cleanCode.includes("G38.")) {
      return `Z-Probe Touch: Probing downward toward touch plate to establish physical Z-Zero`;
    }

    if (block.cleanCode.includes("G10 L20")) {
      return `WCS Coordinate Calibration: Setting Work Coordinate System offset to touch plate thickness`;
    }

    if (block.cleanCode.includes("M0") || block.cleanCode.includes("M00")) {
      return `Operator Pause (M0): Execution paused for manual action (e.g. attach/remove probe clip, flip stock)`;
    }

    if (block.cleanCode.includes("G4") || block.cleanCode.includes("G04")) {
      return `Dwell / Pause: Spindle pause for spinup stabilization or hole bottom dwell`;
    }

    if (block.cleanCode.includes("M3") || block.cleanCode.includes("M03")) {
      return `Spindle Start: Clockwise spindle ON at ${block.rpm} RPM`;
    }

    if (block.cleanCode.includes("M5") || block.cleanCode.includes("M05")) {
      return `Spindle Stop: Spindle power shut off`;
    }

    if (block.cleanCode.includes("M30") || block.cleanCode.includes("M2")) {
      return `Program End & Rewind: Spindle off, motion stopped, program reset`;
    }

    return `Standard CNC block: ${block.cleanCode}`;
  }


  renderInteractiveEditor(containerEl, gcodeText, onLineSelected) {
    if (!containerEl) return;
    this.parseProgram(gcodeText);
    containerEl.innerHTML = "";

    const pre = document.createElement("pre");
    pre.className = "gcode-code-view";

    this.parsedBlocks.forEach((b, idx) => {
      const lineDiv = document.createElement("div");
      lineDiv.className = "gcode-line-row";
      lineDiv.dataset.lineIndex = idx;

      const numSpan = document.createElement("span");
      numSpan.className = "gcode-line-num";
      numSpan.textContent = String(b.lineNumber).padStart(4, " ");

      const codeSpan = document.createElement("span");
      codeSpan.className = "gcode-line-content";

      // Syntax highlight comments vs codes
      if (b.isCommentOnly) {
        codeSpan.className += " gcode-syn-comment";
        codeSpan.textContent = b.rawText;
      } else {
        // Highlight tokens
        let html = b.rawText;
        html = html.replace(/\b(G00?|G01?|G02?|G03?|G17|G20|G21|G90|G91|G94)\b/g, '<span class="gcode-syn-g">$1</span>');
        html = html.replace(/\b(M0?3|M0?5|M0?8|M0?9|M30|M2|M6)\b/g, '<span class="gcode-syn-m">$1</span>');
        html = html.replace(/([XYZIJKR])([+-]?\d+\.?\d*)/g, '<span class="gcode-syn-axis">$1</span><span class="gcode-syn-num">$2</span>');
        html = html.replace(/([FS])(\d+\.?\d*)/g, '<span class="gcode-syn-feed">$1</span><span class="gcode-syn-num">$2</span>');
        html = html.replace(/\((.*?)\)/g, '<span class="gcode-syn-comment">($1)</span>');
        codeSpan.innerHTML = html;
      }

      lineDiv.appendChild(numSpan);
      lineDiv.appendChild(codeSpan);

      lineDiv.addEventListener("click", () => {
        this.selectLine(idx, containerEl, onLineSelected);
      });

      pre.appendChild(lineDiv);
    });

    containerEl.appendChild(pre);

    if (this.parsedBlocks.length > 0) {
      this.selectLine(0, containerEl, onLineSelected);
    }
  }

  selectLine(lineIndex, containerEl, onLineSelected) {
    if (lineIndex < 0 || lineIndex >= this.parsedBlocks.length) return;
    this.activeLineIndex = lineIndex;
    const block = this.parsedBlocks[lineIndex];

    // Highlight row
    if (containerEl) {
      const rows = containerEl.querySelectorAll(".gcode-line-row");
      rows.forEach((r) => r.classList.remove("active-line"));
      if (rows[lineIndex]) {
        rows[lineIndex].classList.add("active-line");
        rows[lineIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }

    if (typeof onLineSelected === "function") {
      onLineSelected(block, lineIndex);
    }
  }

  renderModalStateBar(modalBarEl, block) {
    if (!modalBarEl || !block) return;
    const s = block.modalSnapshot || this.modalState;
    modalBarEl.innerHTML = `
      <div class="modal-badge"><span class="modal-label">WCS</span> <span class="modal-val">${s.wcs}</span></div>
      <div class="modal-badge"><span class="modal-label">Plane</span> <span class="modal-val">${s.plane}</span></div>
      <div class="modal-badge"><span class="modal-label">Units</span> <span class="modal-val">${s.units}</span></div>
      <div class="modal-badge"><span class="modal-label">Dist</span> <span class="modal-val">${s.distanceMode}</span></div>
      <div class="modal-badge"><span class="modal-label">Motion</span> <span class="modal-val">${s.motionMode}</span></div>
      <div class="modal-badge"><span class="modal-label">Tool</span> <span class="modal-val">T${s.tool}</span></div>
      <div class="modal-badge"><span class="modal-label">Spindle</span> <span class="modal-val">${s.spindleRpm} RPM</span></div>
      <div class="modal-badge"><span class="modal-label">Feed</span> <span class="modal-val">${s.feedRate} mm/min</span></div>
    `;
  }
}
