/**
 * Conversational Drilling Operation Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";

  // Elements
  const patternTabs = document.querySelectorAll(".pattern-tab");
  const singleInputs = document.getElementById("singleHoleInputs");
  const gridInputs = document.getElementById("gridHoleInputs");
  const circleInputs = document.getElementById("boltCircleInputs");

  const toolSelect = document.getElementById("toolSelect");
  const presetSelect = document.getElementById("presetSelect");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const plungeFeedInput = document.getElementById("plungeFeed");
  const startZInput = document.getElementById("startZ");
  const targetDepthInput = document.getElementById("targetDepth");
  const retractZInput = document.getElementById("retractZ");
  const dwellSecondsInput = document.getElementById("dwellSeconds");
  const unitsSelect = document.getElementById("unitsSelect");

  const generateBtn = document.getElementById("generateGCodeBtn");
  const gcodeOutput = document.getElementById("gcodeOutput");
  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");

  const statHoles = document.getElementById("statHoles");
  const statTime = document.getElementById("statTime");
  const statBounds = document.getElementById("statBounds");
  const statDialect = document.getElementById("statDialect");
  const warningBanner = document.getElementById("warningBanner");

  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");

  const DEWALT_DIALS = {
    1: 16000,
    2: 18200,
    3: 20400,
    4: 22600,
    5: 24800,
    6: 27000,
  };

  // Load Machine & Tool data
  async function initData() {
    try {
      activeMachine = await API.getActiveMachine();
      if (activeMachine) {
        document.getElementById("activeMachineName").textContent = activeMachine.name;
        const spindleTag = activeMachine.spindle_type === "router" ? "DeWalt Router" : "VFD Spindle";
        document.getElementById("activeMachineDialect").textContent = `(${activeMachine.controller_dialect.toUpperCase()} | ${spindleTag})`;
        retractZInput.value = activeMachine.safe_z_retract || 5.0;

        // Configure Router Dial visibility
        if (activeMachine.spindle_type === "router") {
          routerDialGroup.style.display = "block";
          routerModelBadge.textContent = activeMachine.router_model === "dewalt_611" ? "DeWalt DWP611" : "Router";
        } else {
          routerDialGroup.style.display = "none";
        }

        visualizer.setData(getHoleCoordinates(), {
          x: activeMachine.work_area_x,
          y: activeMachine.work_area_y,
        });
      }

      toolsList = await API.getTools();
      toolSelect.innerHTML = '<option value="">-- Select Tool --</option>';
      toolsList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `T${t.tool_number}: ${t.name} (${t.diameter}mm)`;
        toolSelect.appendChild(opt);
      });

      // Default select first tool if available
      if (toolsList.length > 0) {
        toolSelect.value = toolsList[0].id;
        populatePresets(toolsList[0]);
      }
    } catch (err) {
      console.error("Initialization error:", err);
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

  spindleRpmInput.addEventListener("input", () => {
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

      // Select first preset if available
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

  toolSelect.addEventListener("change", () => {
    const selectedId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedId);
    populatePresets(tool);
    updatePreview();
  });

  presetSelect.addEventListener("change", () => {
    const selectedToolId = parseInt(toolSelect.value, 10);
    const selectedPresetId = parseInt(presetSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedToolId);
    if (tool && tool.material_presets) {
      const preset = tool.material_presets.find((p) => p.id === selectedPresetId);
      applyPreset(preset);
    }
  });

  // Pattern Switcher
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

  function getSelectedToolDiameter() {
    const selectedId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedId);
    return tool ? tool.diameter : 3.175;
  }

  function updatePreview() {
    const holes = getHoleCoordinates();
    statHoles.textContent = holes.length;
    const envelope = activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null;
    visualizer.setData(holes, envelope, getSelectedToolDiameter());
  }

  // Live input changes trigger visualizer update
  document.querySelectorAll("#drillingForm input").forEach((input) => {
    input.addEventListener("input", () => updatePreview());
  });

  // Zoom controls
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
      target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
      start_z: parseFloat(startZInput.value) || 0.0,
      retract_z: parseFloat(retractZInput.value) || 5.0,
      dwell_seconds: parseFloat(dwellSecondsInput.value) || 0.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      spindle_type: activeMachine ? activeMachine.spindle_type : "router",
      router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
      router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
    };

    generateBtn.disabled = true;
    generateBtn.textContent = "Calculating G-Code...";

    try {
      const result = await API.generateStraightPlunge(payload);
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

      // Stats
      statTime.textContent = `${result.data.estimated_time_seconds.toFixed(1)}s`;
      const b = result.data.bounds;
      statBounds.textContent = `X[${b.min_x}, ${b.max_x}] Y[${b.min_y}, ${b.max_y}]`;
      statDialect.textContent = result.dialect_used.toUpperCase();

      // Warnings
      if (result.data.warnings && result.data.warnings.length > 0) {
        warningBanner.style.display = "block";
        warningBanner.innerHTML = `⚠️ <strong>Soft Limit Alert:</strong> ${result.data.warnings.join("<br>")}`;
      } else {
        warningBanner.style.display = "none";
      }

      copyGcodeBtn.disabled = false;
      downloadGcodeBtn.disabled = false;
    } catch (err) {

      alert("Failed to generate G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate G-Code & Preview";
    }
  });

  // Clipboard copy
  copyGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    navigator.clipboard.writeText(currentGeneratedGCode).then(() => {
      const originalText = copyGcodeBtn.textContent;
      copyGcodeBtn.textContent = "✅ Copied!";
      setTimeout(() => (copyGcodeBtn.textContent = originalText), 2000);
    });
  });

  // File download
  downloadGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    const blob = new Blob([currentGeneratedGCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `drilling_operation_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Initialize
  await initData();
  updatePreview();
});
