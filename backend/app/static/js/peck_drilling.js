/**
 * Peck Drilling Operation Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";

  const patternTabs = document.querySelectorAll(".pattern-tab");
  const singleInputs = document.getElementById("singleHoleInputs");
  const gridInputs = document.getElementById("gridHoleInputs");
  const circleInputs = document.getElementById("boltCircleInputs");

  const startZInput = document.getElementById("startZ");
  const targetDepthInput = document.getElementById("targetDepth");
  const peckDepthInput = document.getElementById("peckDepth");
  const peckRetractTypeSelect = document.getElementById("peckRetractType");
  const retractZInput = document.getElementById("retractZ");
  const dwellSecondsInput = document.getElementById("dwellSeconds");

  const toolSelect = document.getElementById("toolSelect");
  const presetSelect = document.getElementById("presetSelect");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const plungeFeedInput = document.getElementById("plungeFeed");

  const generateBtn = document.getElementById("generateGCodeBtn");
  const gcodeOutput = document.getElementById("gcodeOutput");
  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");

  const statHoles = document.getElementById("statHoles");
  const statPeckCount = document.getElementById("statPeckCount");
  const statTime = document.getElementById("statTime");
  const statDialect = document.getElementById("statDialect");
  const warningBanner = document.getElementById("warningBanner");

  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");

  const DEWALT_DIALS = { 1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000 };

  async function initData() {
    try {
      activeMachine = await API.getActiveMachine();
      if (activeMachine) {
        document.getElementById("activeMachineName").textContent = activeMachine.name;
        const spindleTag = activeMachine.spindle_type === "router" ? "DeWalt Router" : "VFD Spindle";
        document.getElementById("activeMachineDialect").textContent = `(${activeMachine.controller_dialect.toUpperCase()} | ${spindleTag})`;
        retractZInput.value = activeMachine.safe_z_retract || 5.0;

        if (activeMachine.spindle_type === "router") {
          routerDialGroup.style.display = "block";
          routerModelBadge.textContent = activeMachine.router_model === "dewalt_611" ? "DeWalt DWP611" : "Router";
        } else {
          routerDialGroup.style.display = "none";
        }
      }

      toolsList = await API.getTools();
      toolSelect.innerHTML = '<option value="">-- Select Tool --</option>';
      let drillDefault = null;
      toolsList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `T${t.tool_number}: ${t.name} (${t.diameter}mm)`;
        toolSelect.appendChild(opt);
        if (t.tool_type === "drill" && !drillDefault) {
          drillDefault = t;
        }
      });

      const selected = drillDefault || toolsList[0];
      if (selected) {
        toolSelect.value = selected.id;
        populatePresets(selected);
      }

      updatePreview();
    } catch (err) {
      console.error("Init error:", err);
    }
  }

  function syncDialFromRpm(rpm) {
    if (!routerDialSelect) return;
    let closestDial = 1;
    let minDiff = Infinity;
    for (const [dial, dialRpm] of Object.entries(DEWALT_DIALS)) {
      const diff = Math.abs(dialRpm - rpm);
      if (diff < minDiff) {
        minDiff = diff;
        closestDial = dial;
      }
    }
    routerDialSelect.value = closestDial;
  }

  routerDialSelect?.addEventListener("change", () => {
    const dial = parseInt(routerDialSelect.value, 10);
    if (DEWALT_DIALS[dial]) {
      spindleRpmInput.value = DEWALT_DIALS[dial];
    }
  });

  spindleRpmInput?.addEventListener("input", () => {
    const rpm = parseInt(spindleRpmInput.value, 10) || 16000;
    syncDialFromRpm(rpm);
  });

  function populatePresets(tool) {
    presetSelect.innerHTML = '<option value="">-- Manual Speeds/Feeds --</option>';
    if (tool && tool.material_presets) {
      tool.material_presets.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.material_name} (${p.spindle_speed} RPM, ${p.plunge_rate_z} mm/min)`;
        presetSelect.appendChild(opt);
      });

      if (tool.material_presets.length > 0) {
        presetSelect.value = tool.material_presets[0].id;
        applyPreset(tool.material_presets[0]);
      }
    }
  }

  function applyPreset(preset) {
    if (preset) {
      spindleRpmInput.value = preset.spindle_speed;
      plungeFeedInput.value = preset.plunge_rate_z;
      syncDialFromRpm(preset.spindle_speed);
    }
  }

  toolSelect?.addEventListener("change", () => {
    const selectedId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedId);
    if (tool) populatePresets(tool);
    updatePreview();
  });

  presetSelect?.addEventListener("change", () => {
    const selectedToolId = parseInt(toolSelect.value, 10);
    const selectedPresetId = parseInt(presetSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedToolId);
    if (tool && tool.material_presets) {
      const preset = tool.material_presets.find((p) => p.id === selectedPresetId);
      applyPreset(preset);
    }
  });

  let activePattern = "single";
  patternTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      patternTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activePattern = tab.dataset.pattern;

      singleInputs.style.display = activePattern === "single" ? "block" : "none";
      gridInputs.style.display = activePattern === "grid" ? "block" : "none";
      circleInputs.style.display = activePattern === "circle" ? "block" : "none";

      updatePreview();
    });
  });

  function getHoleCoordinates() {
    const holes = [];
    if (activePattern === "single") {
      const x = parseFloat(document.getElementById("singleX").value) || 0;
      const y = parseFloat(document.getElementById("singleY").value) || 0;
      holes.push([x, y]);
    } else if (activePattern === "grid") {
      const startX = parseFloat(document.getElementById("gridStartX").value) || 0;
      const startY = parseFloat(document.getElementById("gridStartY").value) || 0;
      const spacingX = parseFloat(document.getElementById("gridSpacingX").value) || 10;
      const spacingY = parseFloat(document.getElementById("gridSpacingY").value) || 10;
      const countX = parseInt(document.getElementById("gridCountX").value, 10) || 1;
      const countY = parseInt(document.getElementById("gridCountY").value, 10) || 1;

      for (let r = 0; r < countY; r++) {
        for (let c = 0; c < countX; c++) {
          holes.push([
            Math.round((startX + c * spacingX) * 1000) / 1000,
            Math.round((startY + r * spacingY) * 1000) / 1000,
          ]);
        }
      }
    } else if (activePattern === "circle") {
      const centerX = parseFloat(document.getElementById("circleCenterX").value) || 0;
      const centerY = parseFloat(document.getElementById("circleCenterY").value) || 0;
      const diameter = parseFloat(document.getElementById("circleDiameter").value) || 50;
      const numHoles = parseInt(document.getElementById("circleHoles").value, 10) || 4;
      const startAngleDeg = parseFloat(document.getElementById("circleStartAngle").value) || 0;
      const radius = diameter / 2.0;

      for (let i = 0; i < numHoles; i++) {
        const angleRad = ((startAngleDeg + (i * 360) / numHoles) * Math.PI) / 180.0;
        const hx = Math.round((centerX + radius * Math.cos(angleRad)) * 1000) / 1000;
        const hy = Math.round((centerY + radius * Math.sin(angleRad)) * 1000) / 1000;
        holes.push([hx, hy]);
      }
    }
    return holes;
  }

  function updatePreview() {
    const holes = getHoleCoordinates();
    statHoles.textContent = holes.length;

    const startZ = parseFloat(startZInput.value) || 0;
    const targetZ = parseFloat(targetDepthInput.value) || -15;
    const peckQ = parseFloat(peckDepthInput.value) || 2.5;
    const totalDepth = Math.abs(startZ - targetZ);
    const pecks = Math.max(1, Math.ceil(totalDepth / peckQ));
    statPeckCount.textContent = pecks;

    const selectedToolId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedToolId);
    const toolDia = tool ? tool.diameter : 3.175;

    const envelope = activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null;

    visualizer.setData({
      opType: "peck",
      holes: holes,
      machineEnvelope: envelope,
      toolDiameter: toolDia,
    });
  }

  document.querySelectorAll("#peckForm input, #peckForm select").forEach((el) => {
    el.addEventListener("input", () => updatePreview());
  });

  document.getElementById("zoomInBtn")?.addEventListener("click", () => visualizer.zoom(1.2));
  document.getElementById("zoomOutBtn")?.addEventListener("click", () => visualizer.zoom(0.8));
  document.getElementById("fitViewBtn")?.addEventListener("click", () => visualizer.autoFit());

  // Generate G-Code Handler
  generateBtn.addEventListener("click", async () => {
    const holes = getHoleCoordinates();
    if (holes.length === 0) {
      alert("Please configure at least one hole coordinate.");
      return;
    }

    const payload = {
      holes: holes,
      target_depth_z: parseFloat(targetDepthInput.value) || -15.0,
      peck_depth: parseFloat(peckDepthInput.value) || 2.5,
      peck_retract_type: peckRetractTypeSelect.value,
      start_z: parseFloat(startZInput.value) || 0.0,
      retract_z: parseFloat(retractZInput.value) || 5.0,
      dwell_seconds: parseFloat(dwellSecondsInput.value) || 0.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      plunge_feed: parseFloat(plungeFeedInput.value) || 200.0,
      spindle_type: activeMachine ? activeMachine.spindle_type : "router",
      router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
      router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
    };

    generateBtn.disabled = true;
    generateBtn.textContent = "Calculating Peck G-Code...";

    try {
      const result = await API.generatePeckDrilling(payload);
      currentGeneratedGCode = result.data.gcode;

      // 1. Load G-Code into 3D Visualizer & Simulation
      visualizer.loadGCode(currentGeneratedGCode);

      // 2. Render Interactive G-Code Editor with Plain English Hints
      const inspector = new GCodeInspector();
      inspector.renderInteractiveEditor(
        gcodeOutput,
        currentGeneratedGCode,
        (block, lineIdx) => {
          const hintEl = document.getElementById("hintText");
          if (hintEl) hintEl.textContent = block.explanation;
          inspector.renderModalStateBar(document.getElementById("modalStateBar"), block);
          visualizer.setHighlightedLine(lineIdx);
        }
      );

      statTime.textContent = `${result.data.estimated_time_seconds.toFixed(1)}s`;
      statDialect.textContent = result.dialect_used.toUpperCase();

      if (result.data.warnings && result.data.warnings.length > 0) {
        warningBanner.style.display = "block";
        warningBanner.innerHTML = `⚠️ <strong>Notice:</strong> ${result.data.warnings.join("<br>")}`;
      } else {
        warningBanner.style.display = "none";
      }

      copyGcodeBtn.disabled = false;
      downloadGcodeBtn.disabled = false;
    } catch (err) {

      alert("Failed to generate Peck Drilling G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Peck G-Code & Preview";
    }
  });

  copyGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    navigator.clipboard.writeText(currentGeneratedGCode).then(() => {
      const orig = copyGcodeBtn.textContent;
      copyGcodeBtn.textContent = "✅ Copied!";
      setTimeout(() => (copyGcodeBtn.textContent = orig), 2000);
    });
  });

  downloadGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    const blob = new Blob([currentGeneratedGCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `peck_drilling_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  await initData();
});
