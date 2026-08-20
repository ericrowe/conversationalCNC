/**
 * Conversational Rectangular Pocket & Boss Machining Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";
  let activeMode = "pocket"; // "pocket" or "boss"

  // Elements
  const opTabs = document.querySelectorAll(".op-tab");
  const geomCardTitle = document.getElementById("geomCardTitle");
  const bossStockInputs = document.getElementById("bossStockInputs");
  const finishAllowGroup = document.getElementById("finishAllowGroup");
  const entryStrategyGroup = document.getElementById("entryStrategyGroup");

  const originModeSelect = document.getElementById("originMode");
  const originXInput = document.getElementById("originX");
  const originYInput = document.getElementById("originY");
  const lengthXInput = document.getElementById("lengthX");
  const widthYInput = document.getElementById("widthY");
  const cornerRadiusInput = document.getElementById("cornerRadius");
  const stockLengthXInput = document.getElementById("stockLengthX");
  const stockWidthYInput = document.getElementById("stockWidthY");

  const startZInput = document.getElementById("startZ");
  const targetDepthInput = document.getElementById("targetDepth");
  const stepdownZInput = document.getElementById("stepdownZ");
  const retractZInput = document.getElementById("retractZ");

  const stepoverPercentInput = document.getElementById("stepoverPercent");
  const finishAllowanceInput = document.getElementById("finishAllowance");
  const entryStrategySelect = document.getElementById("entryStrategy");
  const rampAngleInput = document.getElementById("rampAngle");

  const toolSelect = document.getElementById("toolSelect");
  const presetSelect = document.getElementById("presetSelect");
  const feedRateXyInput = document.getElementById("feedRateXy");
  const plungeFeedInput = document.getElementById("plungeFeed");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const unitsSelect = document.getElementById("unitsSelect");

  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");

  const generateBtn = document.getElementById("generateGCodeBtn");
  const gcodeOutput = document.getElementById("gcodeOutput");
  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");
  const resetViewBtn = document.getElementById("resetViewBtn");

  const statPocketSize = document.getElementById("statPocketSize");
  const statPasses = document.getElementById("statPasses");
  const statTime = document.getElementById("statTime");
  const statDialect = document.getElementById("statDialect");
  const warningBanner = document.getElementById("warningBanner");

  const DEWALT_DIALS = {
    1: 16000,
    2: 18200,
    3: 20400,
    4: 22600,
    5: 24800,
    6: 27000,
  };

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
      toolsList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `T${t.tool_number}: ${t.name} (${t.diameter}mm)`;
        toolSelect.appendChild(opt);
      });

      if (toolsList.length > 0) {
        toolSelect.value = toolsList[0].id;
        populatePresets(toolsList[0]);
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

  function populatePresets(tool) {
    presetSelect.innerHTML = '<option value="">-- Select Material Preset --</option>';
    if (tool && tool.material_presets && tool.material_presets.length > 0) {
      tool.material_presets.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.material_name} (RPM: ${p.spindle_speed}, Feed: ${p.feed_rate_xy} mm/min)`;
        presetSelect.appendChild(opt);
      });
      presetSelect.value = tool.material_presets[0].id;
      applyPreset(tool.material_presets[0]);
    }
  }

  function applyPreset(preset) {
    if (preset) {
      spindleRpmInput.value = preset.spindle_speed;
      feedRateXyInput.value = preset.feed_rate_xy;
      plungeFeedInput.value = preset.plunge_rate_z;
      if (preset.pass_depth !== undefined) stepdownZInput.value = preset.pass_depth;
      syncDialFromRpm(preset.spindle_speed);

    }
  }

  // Mode Switcher (Pocket vs Boss)
  opTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      opTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeMode = tab.dataset.mode;

      if (activeMode === "boss") {
        geomCardTitle.textContent = "2. Boss Island & Stock Dimensions";
        bossStockInputs.style.display = "block";
        finishAllowGroup.style.display = "none";
        entryStrategyGroup.style.display = "none";
        generateBtn.textContent = "⚡ Generate Raised Boss G-Code";
      } else {
        geomCardTitle.textContent = "2. Pocket Geometry & Dimensions";
        bossStockInputs.style.display = "none";
        finishAllowGroup.style.display = "block";
        entryStrategyGroup.style.display = "flex";
        generateBtn.textContent = "⚡ Generate Rectangular G-Code";
      }
      updatePreview();
    });
  });

  function updatePreview() {
    const selectedToolId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedToolId);
    const toolDia = tool ? tool.diameter : 6.35;

    const lx = parseFloat(lengthXInput.value) || 60.0;
    const wy = parseFloat(widthYInput.value) || 40.0;
    const cr = parseFloat(cornerRadiusInput.value) || 0.0;
    const ox = parseFloat(originXInput.value) || 50.0;
    const oy = parseFloat(originYInput.value) || 50.0;
    const originMode = originModeSelect.value;

    const startZ = parseFloat(startZInput.value) || 0.0;
    const targetZ = parseFloat(targetDepthInput.value) || -6.0;
    const stepdownZ = parseFloat(stepdownZInput.value) || 1.5;
    const totalDepth = Math.abs(startZ - (-Math.abs(targetZ)));
    const passes = Math.max(1, Math.ceil(totalDepth / Math.max(0.1, stepdownZ)));

    statPocketSize.textContent = `${lx.toFixed(1)} x ${wy.toFixed(1)} mm`;
    statPasses.textContent = `${passes} pass${passes > 1 ? "es" : ""}`;

    if (activeMode === "pocket") {
      visualizer.setData({
        opType: "rectangular_pocket",
        machineEnvelope: activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null,
        toolDiameter: toolDia,
        rectangularPocket: {
          originX: ox,
          originY: oy,
          lengthX: lx,
          widthY: wy,
          cornerRadius: cr,
          originMode: originMode,
          stepoverPercent: parseFloat(stepoverPercentInput.value) || 60.0,
          finishPassAllowance: parseFloat(finishAllowanceInput.value) || 0.3,
        }
      });
    } else {
      visualizer.setData({
        opType: "rectangular_boss",
        machineEnvelope: activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null,
        toolDiameter: toolDia,
        rectangularBoss: {
          bossOriginX: ox,
          bossOriginY: oy,
          bossLengthX: lx,
          bossWidthY: wy,
          stockLengthX: parseFloat(stockLengthXInput.value) || 100.0,
          stockWidthY: parseFloat(stockWidthYInput.value) || 80.0,
          bossCornerRadius: cr,
          bossOriginMode: originMode,
        }
      });
    }
  }

  // Event Listeners
  [
    originModeSelect, originXInput, originYInput, lengthXInput, widthYInput,
    cornerRadiusInput, stockLengthXInput, stockWidthYInput, startZInput,
    targetDepthInput, stepdownZInput, retractZInput, stepoverPercentInput,
    finishAllowanceInput, entryStrategySelect, rampAngleInput
  ].forEach((el) => {
    el.addEventListener("input", updatePreview);
    el.addEventListener("change", updatePreview);
  });

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

  spindleRpmInput.addEventListener("input", () => {
    syncDialFromRpm(parseFloat(spindleRpmInput.value) || 16000);
  });

  if (routerDialSelect) {
    routerDialSelect.addEventListener("change", () => {
      const dial = parseInt(routerDialSelect.value, 10);
      if (DEWALT_DIALS[dial]) spindleRpmInput.value = DEWALT_DIALS[dial];
    });
  }

  resetViewBtn.addEventListener("click", () => visualizer.autoFit());

  // Generate Button Click
  generateBtn.addEventListener("click", async () => {
    warningBanner.style.display = "none";
    gcodeOutput.textContent = "// Generating G-Code...";

    const selectedToolId = toolSelect.value ? parseInt(toolSelect.value, 10) : null;
    const selectedPresetId = presetSelect.value ? parseInt(presetSelect.value, 10) : null;

    try {
      let result;
      if (activeMode === "pocket") {
        const payload = {
          origin_x: parseFloat(originXInput.value),
          origin_y: parseFloat(originYInput.value),
          length_x: parseFloat(lengthXInput.value),
          width_y: parseFloat(widthYInput.value),
          corner_radius: parseFloat(cornerRadiusInput.value),
          origin_mode: originModeSelect.value,
          start_z: parseFloat(startZInput.value),
          target_depth_z: parseFloat(targetDepthInput.value),
          stepdown_z: parseFloat(stepdownZInput.value),
          retract_z: parseFloat(retractZInput.value),
          stepover_percent: parseFloat(stepoverPercentInput.value),
          finish_pass_allowance: parseFloat(finishAllowanceInput.value),
          entry_strategy: entryStrategySelect.value,
          ramp_angle_deg: parseFloat(rampAngleInput.value),
          feed_rate_xy: parseFloat(feedRateXyInput.value),
          plunge_feed: parseFloat(plungeFeedInput.value),
          spindle_speed: parseInt(spindleRpmInput.value, 10),
          units: unitsSelect.value,
          tool_id: selectedToolId,
          material_preset_id: selectedPresetId,
          router_dial: routerDialSelect ? parseInt(routerDialSelect.value, 10) : null,
        };
        result = await API.generateRectangularPocket(payload);
      } else {
        const payload = {
          boss_origin_x: parseFloat(originXInput.value),
          boss_origin_y: parseFloat(originYInput.value),
          boss_length_x: parseFloat(lengthXInput.value),
          boss_width_y: parseFloat(widthYInput.value),
          stock_length_x: parseFloat(stockLengthXInput.value),
          stock_width_y: parseFloat(stockWidthYInput.value),
          boss_corner_radius: parseFloat(cornerRadiusInput.value),
          boss_origin_mode: originModeSelect.value,
          start_z: parseFloat(startZInput.value),
          target_depth_z: parseFloat(targetDepthInput.value),
          stepdown_z: parseFloat(stepdownZInput.value),
          retract_z: parseFloat(retractZInput.value),
          stepover_percent: parseFloat(stepoverPercentInput.value),
          feed_rate_xy: parseFloat(feedRateXyInput.value),
          plunge_feed: parseFloat(plungeFeedInput.value),
          spindle_speed: parseInt(spindleRpmInput.value, 10),
          units: unitsSelect.value,
          tool_id: selectedToolId,
          material_preset_id: selectedPresetId,
          router_dial: routerDialSelect ? parseInt(routerDialSelect.value, 10) : null,
        };
        result = await API.generateRectangularBoss(payload);
      }

      const { data, dialect_used } = result;
      currentGeneratedGCode = data.gcode;

      // 1. Load G-Code directly into 3D visualizer & simulation
      visualizer.loadGCode(data.gcode);

      // 2. Render Interactive G-Code Editor with Plain English Hints
      const inspector = new GCodeInspector();
      inspector.renderInteractiveEditor(
        gcodeOutput,
        data.gcode,
        (block, lineIdx) => {
          const hintEl = document.getElementById("hintText");
          if (hintEl) hintEl.textContent = block.explanation;
          inspector.renderModalStateBar(document.getElementById("modalStateBar"), block);
          visualizer.setHighlightedLine(lineIdx);
        }
      );

      statTime.textContent = `${data.estimated_time_seconds}s`;
      statDialect.textContent = dialect_used ? dialect_used.toUpperCase() : "GRBL";

      if (data.warnings && data.warnings.length > 0) {
        warningBanner.textContent = `⚠️ Machine Warning: ${data.warnings.join(" | ")}`;
        warningBanner.style.display = "block";
      }
    } catch (err) {
      gcodeOutput.textContent = `// Error: ${err.message}`;
      console.error(err);
    }

  });

  // Copy & Download
  copyGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    navigator.clipboard.writeText(currentGeneratedGCode);
    const originalText = copyGcodeBtn.textContent;
    copyGcodeBtn.textContent = "✅ Copied!";
    setTimeout(() => (copyGcodeBtn.textContent = originalText), 2000);
  });

  downloadGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    const blob = new Blob([currentGeneratedGCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeMode === "boss" ? "rectangular_boss" : "rectangular_pocket"}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Add to Job Queue Handler
  const addToJobQueueBtn = document.getElementById("addToJobQueueBtn");
  if (addToJobQueueBtn) {
    addToJobQueueBtn.addEventListener("click", () => {
      const selectedToolId = toolSelect.value ? parseInt(toolSelect.value, 10) : 1;
      const selectedTool = toolsList.find((t) => t.id === selectedToolId);
      const lx = parseFloat(lengthXInput.value) || 50;
      const wy = parseFloat(widthYInput.value) || 40;

      let opPayload;
      if (activeMode === "pocket") {
        opPayload = {
          op_name: `Rect Pocket (${lx}x${wy}mm)`,
          op_type: "rectangular_pocket",
          tool_number: selectedTool ? selectedTool.tool_number : 1,
          tool_name: selectedTool ? selectedTool.name : "Endmill",
          tool_diameter: selectedTool ? selectedTool.diameter : 3.175,
          spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800,
          plunge_feed: parseFloat(plungeFeedInput.value) || 300,
          params: {
            origin_x: parseFloat(originXInput.value) || 0,
            origin_y: parseFloat(originYInput.value) || 0,
            length_x: lx,
            width_y: wy,
            corner_radius: parseFloat(cornerRadiusInput.value) || 0,
            origin_mode: originModeSelect.value || "center",
            start_z: parseFloat(startZInput.value) || 0,
            target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
            stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
            retract_z: parseFloat(retractZInput.value) || 5.0,
            stepover_percent: parseFloat(stepoverPercentInput.value) || 50,
            finish_pass_allowance: parseFloat(finishAllowanceInput.value) || 0.2,
            entry_strategy: entryStrategySelect.value || "helical",
            ramp_angle_deg: parseFloat(rampAngleInput.value) || 3.0,
            feed_rate_xy: parseFloat(feedRateXyInput.value) || 800,
            plunge_feed: parseFloat(plungeFeedInput.value) || 300,
            spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
            tool_id: selectedToolId,
          },
          raw_gcode: currentGeneratedGCode || null,
        };
      } else {
        opPayload = {
          op_name: `Rect Boss (${lx}x${wy}mm)`,
          op_type: "rectangular_boss",
          tool_number: selectedTool ? selectedTool.tool_number : 1,
          tool_name: selectedTool ? selectedTool.name : "Endmill",
          tool_diameter: selectedTool ? selectedTool.diameter : 3.175,
          spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800,
          plunge_feed: parseFloat(plungeFeedInput.value) || 300,
          params: {
            boss_origin_x: parseFloat(originXInput.value) || 0,
            boss_origin_y: parseFloat(originYInput.value) || 0,
            boss_length_x: lx,
            boss_width_y: wy,
            stock_length_x: parseFloat(stockLengthXInput.value) || 80,
            stock_width_y: parseFloat(stockWidthYInput.value) || 60,
            boss_corner_radius: parseFloat(cornerRadiusInput.value) || 0,
            boss_origin_mode: originModeSelect.value || "center",
            start_z: parseFloat(startZInput.value) || 0,
            target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
            stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
            retract_z: parseFloat(retractZInput.value) || 5.0,
            stepover_percent: parseFloat(stepoverPercentInput.value) || 50,
            finish_pass_allowance: parseFloat(finishAllowanceInput.value) || 0.2,
            feed_rate_xy: parseFloat(feedRateXyInput.value) || 800,
            plunge_feed: parseFloat(plungeFeedInput.value) || 300,
            spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
            tool_id: selectedToolId,
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

