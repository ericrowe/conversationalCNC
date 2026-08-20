/**
 * Circular Pocket & Bore Operation Controller
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

  const pocketDiameterInput = document.getElementById("pocketDiameter");
  const targetDepthInput = document.getElementById("targetDepth");
  const stepdownZInput = document.getElementById("stepdownZ");
  const stepoverPercentInput = document.getElementById("stepoverPercent");
  const finishAllowanceInput = document.getElementById("finishAllowance");
  const retractZInput = document.getElementById("retractZ");

  const toolSelect = document.getElementById("toolSelect");
  const toolDiameterInput = document.getElementById("toolDiameter");
  const presetSelect = document.getElementById("presetSelect");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const feedRateXyInput = document.getElementById("feedRateXy");
  const plungeFeedInput = document.getElementById("plungeFeed");

  const generateBtn = document.getElementById("generateGCodeBtn");
  const gcodeOutput = document.getElementById("gcodeOutput");
  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");

  const statPocketCount = document.getElementById("statPocketCount");
  const statZPasses = document.getElementById("statZPasses");
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
      let endmillDefault = null;
      toolsList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `T${t.tool_number}: ${t.name} (${t.diameter}mm)`;
        toolSelect.appendChild(opt);
        if (t.tool_type === "endmill" && !endmillDefault) {
          endmillDefault = t;
        }
      });

      const selected = endmillDefault || toolsList[0];
      if (selected) {
        toolSelect.value = selected.id;
        toolDiameterInput.value = selected.diameter;
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
        opt.textContent = `${p.material_name} (${p.spindle_speed} RPM, ${p.feed_rate_xy} mm/min)`;
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
      feedRateXyInput.value = preset.feed_rate_xy;
      plungeFeedInput.value = preset.plunge_rate_z;
      if (preset.pass_depth) stepdownZInput.value = preset.pass_depth;
      syncDialFromRpm(preset.spindle_speed);
    }
  }

  toolSelect?.addEventListener("change", () => {
    const selectedId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedId);
    if (tool) {
      toolDiameterInput.value = tool.diameter;
      populatePresets(tool);
    }
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

  function getPocketCoordinates() {
    const pockets = [];
    if (activePattern === "single") {
      const x = parseFloat(document.getElementById("singleX").value) || 0;
      const y = parseFloat(document.getElementById("singleY").value) || 0;
      pockets.push([x, y]);
    } else if (activePattern === "grid") {
      const startX = parseFloat(document.getElementById("gridStartX").value) || 0;
      const startY = parseFloat(document.getElementById("gridStartY").value) || 0;
      const spacingX = parseFloat(document.getElementById("gridSpacingX").value) || 10;
      const spacingY = parseFloat(document.getElementById("gridSpacingY").value) || 10;
      const countX = parseInt(document.getElementById("gridCountX").value, 10) || 1;
      const countY = parseInt(document.getElementById("gridCountY").value, 10) || 1;

      for (let r = 0; r < countY; r++) {
        for (let c = 0; c < countX; c++) {
          pockets.push([
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
        pockets.push([hx, hy]);
      }
    }
    return pockets;
  }

  function updatePreview() {
    const pockets = getPocketCoordinates();
    statPocketCount.textContent = pockets.length;

    const targetZ = parseFloat(targetDepthInput.value) || -5.0;
    const stepdownZ = parseFloat(stepdownZInput.value) || 1.5;
    const zPasses = Math.max(1, Math.ceil(Math.abs(targetZ) / stepdownZ));
    statZPasses.textContent = zPasses;

    const envelope = activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null;

    visualizer.setData({
      opType: "pocket",
      pockets: pockets,
      machineEnvelope: envelope,
      pocketDiameter: parseFloat(pocketDiameterInput.value) || 20.0,
      toolDiameter: parseFloat(toolDiameterInput.value) || 3.175,
    });
  }

  document.querySelectorAll("#pocketForm input, #pocketForm select").forEach((el) => {
    el.addEventListener("input", () => updatePreview());
  });

  document.getElementById("zoomInBtn")?.addEventListener("click", () => visualizer.zoom(1.2));
  document.getElementById("zoomOutBtn")?.addEventListener("click", () => visualizer.zoom(0.8));
  document.getElementById("fitViewBtn")?.addEventListener("click", () => visualizer.autoFit());

  // Generate G-Code Handler
  generateBtn.addEventListener("click", async () => {
    const pockets = getPocketCoordinates();
    if (pockets.length === 0) {
      alert("Please configure at least one pocket location.");
      return;
    }

    const payload = {
      pockets: pockets,
      pocket_diameter: parseFloat(pocketDiameterInput.value),
      target_depth_z: parseFloat(targetDepthInput.value),
      tool_diameter: parseFloat(toolDiameterInput.value),
      stepdown_z: parseFloat(stepdownZInput.value),
      stepover_percent: parseFloat(stepoverPercentInput.value),
      finish_allowance: parseFloat(finishAllowanceInput.value),
      feed_rate_xy: parseFloat(feedRateXyInput.value),
      plunge_feed: parseFloat(plungeFeedInput.value),
      retract_z: parseFloat(retractZInput.value) || 5.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      spindle_type: activeMachine ? activeMachine.spindle_type : "router",
      router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
      router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
    };

    generateBtn.disabled = true;
    generateBtn.textContent = "Calculating Circular Pocket...";

    try {
      const result = await API.generateCircularPocket(payload);
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

      alert("Failed to generate Pocket G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Pocket G-Code & Preview";
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
    a.download = `circular_pocket_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Add to Job Queue Handler
  const addToJobQueueBtn = document.getElementById("addToJobQueueBtn");
  if (addToJobQueueBtn) {
    addToJobQueueBtn.addEventListener("click", () => {
      const pockets = getPocketCoordinates();
      if (pockets.length === 0) {
        alert("Please configure at least one pocket location first.");
        return;
      }
      const toolId = toolSelect.value ? parseInt(toolSelect.value, 10) : 1;
      const selectedTool = toolsList.find((t) => t.id === toolId);
      const dia = parseFloat(pocketDiameterInput.value) || 20.0;

      const opPayload = {
        op_name: `Circular Pocket (${dia}mm dia, ${pockets.length} locs)`,
        op_type: "circular_pocket",
        tool_number: selectedTool ? selectedTool.tool_number : 1,
        tool_name: selectedTool ? selectedTool.name : "Endmill",
        tool_diameter: selectedTool ? selectedTool.diameter : parseFloat(toolDiameterInput.value) || 3.175,
        spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
        feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
        plunge_feed: parseFloat(plungeFeedInput.value) || 300.0,
        params: {
          pockets: pockets,
          pocket_diameter: dia,
          target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
          tool_diameter: parseFloat(toolDiameterInput.value) || 3.175,
          stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
          stepover_percent: parseFloat(stepoverPercentInput.value) || 50.0,
          finish_allowance: parseFloat(finishAllowanceInput.value) || 0.2,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
          plunge_feed: parseFloat(plungeFeedInput.value) || 300.0,
          retract_z: parseFloat(retractZInput.value) || 5.0,
          spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
          tool_id: toolId,
        },
        raw_gcode: currentGeneratedGCode || null,
      };

      if (window.JobBuilder) {
        window.JobBuilder.addOperation(opPayload);
        const origText = addToJobQueueBtn.textContent;
        addToJobQueueBtn.textContent = "✅ Queued!";
        setTimeout(() => (addToJobQueueBtn.textContent = origText), 1500);
      }
    });
  }


  await initData();
});

