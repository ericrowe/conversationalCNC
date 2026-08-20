document.addEventListener("DOMContentLoaded", () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  const inspector = new GCodeInspector();

  const sourceGCodeInput = document.getElementById("sourceGCode");
  const uploadBtn = document.getElementById("uploadFileBtn");
  const fileInput = document.getElementById("fileUploadInput");
  const loadSampleBtn = document.getElementById("loadSampleBtn");

  const patternTabs = document.querySelectorAll(".pattern-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");

  const btnApplyShift = document.getElementById("btnApplyShift");
  const btnApplyRotate = document.getElementById("btnApplyRotate");
  const btnApplyMirror = document.getElementById("btnApplyMirror");
  const btnApplyOverride = document.getElementById("btnApplyOverride");
  const btnApplySplit = document.getElementById("btnApplySplit");

  const gcodeOutput = document.getElementById("gcodeOutput");
  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");
  const splitFilesList = document.getElementById("splitFilesList");

  let currentResultGCode = "";

  // Tab switching
  patternTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      patternTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.tab;

      tabPanes.forEach((p) => (p.style.display = "none"));
      if (target === "shift") document.getElementById("tabContentShift").style.display = "block";
      else if (target === "rotate") document.getElementById("tabContentRotate").style.display = "block";
      else if (target === "mirror") document.getElementById("tabContentMirror").style.display = "block";
      else if (target === "override") document.getElementById("tabContentOverride").style.display = "block";
      else if (target === "split") document.getElementById("tabContentSplit").style.display = "block";
    });
  });

  // Sample Multi-Tool G-Code
  const SAMPLE_MULTITOOL = `(ConversationalCNC Sample Multi-Tool Program)
G21 G90 G94 G17
( --- TOOL 1: 6.35mm Flat Endmill --- )
T1 M6 (Roughing Pocket)
S18000 M3
G0 Z5.000
G0 X10.000 Y10.000
G1 Z-3.000 F300.0
G1 X50.000 Y10.000 F1200.0
G1 X50.000 Y40.000
G1 X10.000 Y40.000
G1 X10.000 Y10.000
G0 Z5.000

( --- TOOL 2: 90-Deg V-Bit --- )
T2 M6 (Perimeter Chamfering)
S16000 M3
G0 X8.000 Y8.000
G1 Z-1.000 F400.0
G1 X52.000 Y8.000 F800.0
G1 X52.000 Y42.000
G1 X8.000 Y42.000
G1 X8.000 Y8.000
G0 Z5.000
M5
M30`;

  loadSampleBtn.addEventListener("click", () => {
    sourceGCodeInput.value = SAMPLE_MULTITOOL;
    visualizer.loadGCode(SAMPLE_MULTITOOL);
  });

  uploadBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      sourceGCodeInput.value = evt.target.result;
      visualizer.loadGCode(evt.target.result);
    };
    reader.readAsText(file);
  });

  sourceGCodeInput.addEventListener("input", () => {
    if (sourceGCodeInput.value.trim()) {
      visualizer.loadGCode(sourceGCodeInput.value);
    }
  });

  function displayTransformedResult(gcode) {
    currentResultGCode = gcode;
    visualizer.loadGCode(gcode);

    inspector.renderInteractiveEditor(
      gcodeOutput,
      gcode,
      (block, lineIdx) => {
        const hintEl = document.getElementById("hintText");
        if (hintEl) hintEl.textContent = block.explanation;
        inspector.renderModalStateBar(document.getElementById("modalStateBar"), block);
        visualizer.setHighlightedLine(lineIdx);
      }
    );

    copyGcodeBtn.disabled = false;
    downloadGcodeBtn.disabled = false;
  }

  // 1. Shift
  btnApplyShift.addEventListener("click", async () => {
    const src = sourceGCodeInput.value.trim();
    if (!src) return alert("Please enter or load source G-code first.");

    try {
      const res = await API.transformShift({
        gcode: src,
        delta_x: parseFloat(document.getElementById("shiftX").value) || 0,
        delta_y: parseFloat(document.getElementById("shiftY").value) || 0,
        delta_z: parseFloat(document.getElementById("shiftZ").value) || 0,
      });
      displayTransformedResult(res.gcode);
    } catch (err) {
      alert("Shift failed: " + err.message);
    }
  });

  // 2. Rotate
  btnApplyRotate.addEventListener("click", async () => {
    const src = sourceGCodeInput.value.trim();
    if (!src) return alert("Please enter or load source G-code first.");

    try {
      const res = await API.transformRotate({
        gcode: src,
        angle_deg: parseFloat(document.getElementById("rotAngle").value) || 0,
        center_x: parseFloat(document.getElementById("rotCenterX").value) || 0,
        center_y: parseFloat(document.getElementById("rotCenterY").value) || 0,
      });
      displayTransformedResult(res.gcode);
    } catch (err) {
      alert("Rotate failed: " + err.message);
    }
  });

  // 3. Mirror
  btnApplyMirror.addEventListener("click", async () => {
    const src = sourceGCodeInput.value.trim();
    if (!src) return alert("Please enter or load source G-code first.");

    try {
      const axis = document.getElementById("mirrorAxis").value;
      const originVal = parseFloat(document.getElementById("mirrorOrigin").value) || 0;
      const res = await API.transformMirror({
        gcode: src,
        mirror_axis: axis,
        origin_x: axis === "y" ? originVal : 0,
        origin_y: axis === "x" ? originVal : 0,
      });
      displayTransformedResult(res.gcode);
    } catch (err) {
      alert("Mirror failed: " + err.message);
    }
  });

  // 4. Feed/Speed Override
  btnApplyOverride.addEventListener("click", async () => {
    const src = sourceGCodeInput.value.trim();
    if (!src) return alert("Please enter or load source G-code first.");

    try {
      const res = await API.transformOverrideFeeds({
        gcode: src,
        feed_percent: parseFloat(document.getElementById("overrideFeedPercent").value) || 100,
        speed_percent: parseFloat(document.getElementById("overrideSpeedPercent").value) || 100,
      });
      displayTransformedResult(res.gcode);
    } catch (err) {
      alert("Override failed: " + err.message);
    }
  });

  // 5. Split Tools
  btnApplySplit.addEventListener("click", async () => {
    const src = sourceGCodeInput.value.trim();
    if (!src) return alert("Please enter or load source G-code first.");

    try {
      const res = await API.transformSplitTools({
        gcode: src,
        safe_retract_z: parseFloat(document.getElementById("splitRetractZ").value) || 5.0,
      });

      splitFilesList.innerHTML = "";
      if (res.sub_programs && res.sub_programs.length > 0) {
        displayTransformedResult(res.sub_programs[0].gcode);

        const card = document.createElement("div");
        card.style.background = "#1e293b";
        card.style.padding = "0.75rem";
        card.style.borderRadius = "6px";
        card.style.border = "1px solid #334155";
        card.innerHTML = `<strong style="color: #38bdf8;">Extracted ${res.count} Standalone Tool Programs:</strong>`;

        res.sub_programs.forEach((prog, i) => {
          const row = document.createElement("div");
          row.style.display = "flex";
          row.style.justifyContent = "space-between";
          row.style.alignItems = "center";
          row.style.marginTop = "0.5rem";
          row.style.padding = "0.35rem 0.5rem";
          row.style.background = "#0f172a";
          row.style.borderRadius = "4px";

          row.innerHTML = `
            <span><strong>Tool T${prog.tool_number}</strong>: <code>${prog.filename}</code> (${prog.line_count} lines)</span>
            <div style="display: flex; gap: 0.35rem;">
              <button type="button" class="btn btn-secondary btn-sm" data-idx="${i}">👁 View</button>
              <button type="button" class="btn btn-primary btn-sm" data-dl="${i}">💾 Download</button>
            </div>
          `;

          row.querySelector(`[data-idx="${i}"]`).addEventListener("click", () => {
            displayTransformedResult(prog.gcode);
          });

          row.querySelector(`[data-dl="${i}"]`).addEventListener("click", () => {
            const blob = new Blob([prog.gcode], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = prog.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          });

          card.appendChild(row);
        });

        splitFilesList.appendChild(card);
      } else {
        alert("No tool changes detected in program.");
      }
    } catch (err) {
      alert("Split failed: " + err.message);
    }
  });

  // Clipboard copy
  copyGcodeBtn.addEventListener("click", () => {
    if (!currentResultGCode) return;
    navigator.clipboard.writeText(currentResultGCode).then(() => {
      const orig = copyGcodeBtn.textContent;
      copyGcodeBtn.textContent = "✅ Copied!";
      setTimeout(() => (copyGcodeBtn.textContent = orig), 2000);
    });
  });

  // File download
  downloadGcodeBtn.addEventListener("click", () => {
    if (!currentResultGCode) return;
    const blob = new Blob([currentResultGCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transformed_program_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
});
