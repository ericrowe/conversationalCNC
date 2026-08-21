/**
 * Circular Pocket & Boss / Shaft Operation Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";
  let activeMode = "pocket"; // "pocket" or "boss"

  // Mode Tabs & Cards
  const opTabs = document.querySelectorAll(".op-tab");
  const pocketPatternCard = document.getElementById("pocketPatternCard");
  const pocketDimsCard = document.getElementById("pocketDimsCard");
  const bossDimsCard = document.getElementById("bossDimsCard");

  // Pocket Pattern Elements
  const patternTabs = document.querySelectorAll(".pattern-tab");
  const singleInputs = document.getElementById("singleHoleInputs");
  const gridInputs = document.getElementById("gridHoleInputs");
  const circleInputs = document.getElementById("boltCircleInputs");

  // Pocket Dimensions Elements
  const pocketDiameterInput = document.getElementById("pocketDiameter");
  const targetDepthInput = document.getElementById("targetDepth");
  const stepdownZInput = document.getElementById("stepdownZ");
  const stepoverPercentInput = document.getElementById("stepoverPercent");
  const finishAllowanceInput = document.getElementById("finishAllowance");
  const retractZInput = document.getElementById("retractZ");

  // Boss Elements
  const bossCenterXInput = document.getElementById("bossCenterX");
  const bossCenterYInput = document.getElementById("bossCenterY");
  const bossDiameterInput = document.getElementById("bossDiameter");
  const bossStockShapeSelect = document.getElementById("bossStockShape");
  const bossStockDiameterInput = document.getElementById("bossStockDiameter");
  const bossStockLengthXInput = document.getElementById("bossStockLengthX");
  const bossStockWidthYInput = document.getElementById("bossStockWidthY");
  const bossRoundStockGroup = document.getElementById("bossRoundStockGroup");
  const bossRectStockGroup = document.getElementById("bossRectStockGroup");
  const bossTargetDepthInput = document.getElementById("bossTargetDepth");
  const bossStepdownZInput = document.getElementById("bossStepdownZ");
  const bossStepoverPercentInput = document.getElementById("bossStepoverPercent");
  const bossFinishAllowanceInput = document.getElementById("bossFinishAllowance");

  // Tool & Feed Elements
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
  const statCountLabel = document.getElementById("statCountLabel");
  const statZPasses = document.getElementById("statZPasses");
  const statTime = document.getElementById("statTime");
  const statDialect = document.getElementById("statDialect");
  const warningBanner = document.getElementById("warningBanner");

  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");

  const DEWALT_DIALS = { 1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000 };

  // Mode Switcher (Pocket vs Boss)
  opTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      opTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeMode = tab.dataset.mode;

      if (activeMode === "pocket") {
        if (pocketPatternCard) pocketPatternCard.style.display = "block";
        if (pocketDimsCard) pocketDimsCard.style.display = "block";
        if (bossDimsCard) bossDimsCard.style.display = "none";
        statCountLabel.textContent = "Pocket Count";
        generateBtn.textContent = "⚡ Generate Pocket G-Code & Preview";
      } else {
        if (pocketPatternCard) pocketPatternCard.style.display = "none";
        if (pocketDimsCard) pocketDimsCard.style.display = "none";
        if (bossDimsCard) bossDimsCard.style.display = "block";
        statCountLabel.textContent = "Boss Count";
        generateBtn.textContent = "⚡ Generate Circular Boss G-Code & Preview";
      }
      updatePreview();
    });
  });

  // Boss Stock Shape Switcher
  if (bossStockShapeSelect) {
    bossStockShapeSelect.addEventListener("change", () => {
      const shape = bossStockShapeSelect.value;
      if (shape === "circle") {
        bossRoundStockGroup.style.display = "block";
        bossRectStockGroup.style.display = "none";
      } else {
        bossRoundStockGroup.style.display = "none";
        bossRectStockGroup.style.display = "block";
      }
      updatePreview();
    });
  }

  async function initData() {
    try {
      activeMachine = await API.getActiveMachine();
      if (activeMachine) {
        document.getElementById("activeMachineName").textContent = activeMachine.name;
        const spindleTag = activeMachine.spindle_type === "router" ? "DeWalt Router" : "VFD Spindle";
        document.getElementById("activeMachineDialect").textContent = `(${activeMachine.controller_dialect.toUpperCase()} | ${spindleTag})`;
        if (retractZInput) retractZInput.value = activeMachine.safe_z_retract || 5.0;

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
      if (preset.pass_depth) {
        stepdownZInput.value = preset.pass_depth;
        if (bossStepdownZInput) bossStepdownZInput.value = preset.pass_depth;
      }
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
    const envelope = activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null;

    if (activeMode === "pocket") {
      const pockets = getPocketCoordinates();
      statPocketCount.textContent = pockets.length;

      const targetZ = parseFloat(targetDepthInput.value) || -5.0;
      const stepdownZ = parseFloat(stepdownZInput.value) || 1.5;
      const zPasses = Math.max(1, Math.ceil(Math.abs(targetZ) / stepdownZ));
      statZPasses.textContent = zPasses;

      visualizer.setData({
        opType: "pocket",
        pockets: pockets,
        machineEnvelope: envelope,
        pocketDiameter: parseFloat(pocketDiameterInput.value) || 20.0,
        toolDiameter: parseFloat(toolDiameterInput.value) || 3.175,
      });
    } else {
      // Boss Mode
      statPocketCount.textContent = 1;
      const targetZ = parseFloat(bossTargetDepthInput.value) || -15.0;
      const stepdownZ = parseFloat(bossStepdownZInput.value) || 1.0;
      const zPasses = Math.max(1, Math.ceil(Math.abs(targetZ) / stepdownZ));
      statZPasses.textContent = zPasses;

      visualizer.setData({
        opType: "circular_boss",
        machineEnvelope: envelope,
        bossCenterX: parseFloat(bossCenterXInput.value) || 50.0,
        bossCenterY: parseFloat(bossCenterYInput.value) || 50.0,
        bossDiameter: parseFloat(bossDiameterInput.value) || 10.0,
        stockShape: bossStockShapeSelect.value,
        stockDiameter: parseFloat(bossStockDiameterInput.value) || 25.0,
        stockLengthX: parseFloat(bossStockLengthXInput.value) || 30.0,
        stockWidthY: parseFloat(bossStockWidthYInput.value) || 30.0,
        toolDiameter: parseFloat(toolDiameterInput.value) || 6.35,
      });
    }
  }

  document.querySelectorAll("#pocketForm input, #pocketForm select").forEach((el) => {
    el.addEventListener("input", () => updatePreview());
  });

  document.getElementById("zoomInBtn")?.addEventListener("click", () => visualizer.zoom(1.2));
  document.getElementById("zoomOutBtn")?.addEventListener("click", () => visualizer.zoom(0.8));
  document.getElementById("fitViewBtn")?.addEventListener("click", () => visualizer.autoFit());

  // Generate G-Code Handler
  generateBtn.addEventListener("click", async () => {
    generateBtn.disabled = true;
    generateBtn.textContent = activeMode === "pocket" ? "Calculating Circular Pocket..." : "Calculating Circular Boss...";

    try {
      let result;
      if (activeMode === "pocket") {
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
        result = await API.generateCircularPocket(payload);
      } else {
        // Boss Mode
        const payload = {
          boss_center_x: parseFloat(bossCenterXInput.value) || 0.0,
          boss_center_y: parseFloat(bossCenterYInput.value) || 0.0,
          boss_diameter: parseFloat(bossDiameterInput.value) || 10.0,
          stock_shape: bossStockShapeSelect.value,
          stock_diameter: parseFloat(bossStockDiameterInput.value) || 25.0,
          stock_length_x: parseFloat(bossStockLengthXInput.value) || 30.0,
          stock_width_y: parseFloat(bossStockWidthYInput.value) || 30.0,
          target_depth_z: parseFloat(bossTargetDepthInput.value) || -15.0,
          stepdown_z: parseFloat(bossStepdownZInput.value) || 1.0,
          stepover_percent: parseFloat(bossStepoverPercentInput.value) || 50.0,
          finish_allowance: parseFloat(bossFinishAllowanceInput.value) || 0.2,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
          plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
          retract_z: parseFloat(retractZInput.value) || 5.0,
          spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
          tool_diameter: parseFloat(toolDiameterInput.value) || 6.35,
          spindle_type: activeMachine ? activeMachine.spindle_type : "router",
          router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
          router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
          tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
          material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
        };
        result = await API.generateCircularBoss(payload);
      }

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
      alert("Failed to generate G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = activeMode === "pocket" ? "⚡ Generate Pocket G-Code & Preview" : "⚡ Generate Circular Boss G-Code & Preview";
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
    a.download = `${activeMode === "pocket" ? "circular_pocket" : "circular_boss"}_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Add to Job Queue Handler
  const addToJobQueueBtn = document.getElementById("addToJobQueueBtn");
  if (addToJobQueueBtn) {
    addToJobQueueBtn.addEventListener("click", () => {
      const toolId = toolSelect.value ? parseInt(toolSelect.value, 10) : 1;
      const selectedTool = toolsList.find((t) => t.id === toolId);
      const toolDia = selectedTool ? selectedTool.diameter : parseFloat(toolDiameterInput.value) || 6.35;
      const toolNum = selectedTool ? selectedTool.tool_number : 1;
      const toolName = selectedTool ? selectedTool.name : "Endmill";

      let opPayload;
      if (activeMode === "pocket") {
        const pockets = getPocketCoordinates();
        if (pockets.length === 0) {
          alert("Please configure at least one pocket location first.");
          return;
        }
        const dia = parseFloat(pocketDiameterInput.value) || 20.0;
        opPayload = {
          op_name: `Circular Pocket (Ø${dia}mm, ${pockets.length} locs)`,
          op_type: "circular_pocket",
          tool_number: toolNum,
          tool_name: toolName,
          tool_diameter: toolDia,
          spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
          plunge_feed: parseFloat(plungeFeedInput.value) || 300.0,
          params: {
            pockets: pockets,
            pocket_diameter: dia,
            target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
            tool_diameter: toolDia,
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
      } else {
        // Boss Mode
        const bossDia = parseFloat(bossDiameterInput.value) || 10.0;
        const stockDia = parseFloat(bossStockDiameterInput.value) || 25.0;
        const shape = bossStockShapeSelect.value;
        const stockDesc = shape === "circle" ? `Ø${stockDia}mm Round` : `Rect ${bossStockLengthXInput.value}x${bossStockWidthYInput.value}mm`;

        opPayload = {
          op_name: `Circular Boss (Ø${bossDia}mm Shaft from ${stockDesc})`,
          op_type: "circular_boss",
          tool_number: toolNum,
          tool_name: toolName,
          tool_diameter: toolDia,
          spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
          plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
          params: {
            boss_center_x: parseFloat(bossCenterXInput.value) || 0.0,
            boss_center_y: parseFloat(bossCenterYInput.value) || 0.0,
            boss_diameter: bossDia,
            stock_shape: shape,
            stock_diameter: stockDia,
            stock_length_x: parseFloat(bossStockLengthXInput.value) || 30.0,
            stock_width_y: parseFloat(bossStockWidthYInput.value) || 30.0,
            target_depth_z: parseFloat(bossTargetDepthInput.value) || -15.0,
            stepdown_z: parseFloat(bossStepdownZInput.value) || 1.0,
            stepover_percent: parseFloat(bossStepoverPercentInput.value) || 50.0,
            finish_allowance: parseFloat(bossFinishAllowanceInput.value) || 0.2,
            feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
            plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
            retract_z: parseFloat(retractZInput.value) || 5.0,
            spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
            tool_diameter: toolDia,
            tool_id: toolId,
          },
          raw_gcode: currentGeneratedGCode || null,
        };
      }

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
