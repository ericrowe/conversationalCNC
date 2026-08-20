/**
 * Step-and-Repeat Array Nesting & Soft Jaw Fixturing Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";

  // Mode Selection Elements
  const nestingModeSelect = document.getElementById("nestingModeSelect");
  const stepRepeatCard = document.getElementById("stepRepeatCard");
  const softJawCard = document.getElementById("softJawCard");
  const toolingSpeedsCard = document.getElementById("toolingSpeedsCard");

  // Step-and-Repeat Elements
  const colsXInput = document.getElementById("colsX");
  const rowsYInput = document.getElementById("rowsY");
  const spacingXInput = document.getElementById("spacingX");
  const spacingYInput = document.getElementById("spacingY");
  const layoutPatternSelect = document.getElementById("layoutPattern");
  const orderStrategySelect = document.getElementById("orderStrategy");
  const arraySafeZInput = document.getElementById("arraySafeZ");
  const sourceGCodeInput = document.getElementById("sourceGCodeInput");
  const loadSampleSnippetBtn = document.getElementById("loadSampleSnippetBtn");
  const generateArrayBtn = document.getElementById("generateArrayBtn");

  // Soft Jaw Elements
  const jawTypeSelect = document.getElementById("jawTypeSelect");
  const rectJawDimensions = document.getElementById("rectJawDimensions");
  const roundJawDimensions = document.getElementById("roundJawDimensions");
  const dogboneRow = document.getElementById("dogboneRow");
  const partLengthXInput = document.getElementById("partLengthX");
  const partWidthYInput = document.getElementById("partWidthY");
  const partDiameterInput = document.getElementById("partDiameter");
  const stepDepthZInput = document.getElementById("stepDepthZ");
  const jawGapInput = document.getElementById("jawGap");
  const dogboneReliefSelect = document.getElementById("dogboneRelief");
  const stepdownZInput = document.getElementById("stepdownZ");
  const generateSoftJawBtn = document.getElementById("generateSoftJawBtn");

  // Standardized Tool & Speeds Elements
  const toolSelect = document.getElementById("toolSelect");
  const toolDiameterInput = document.getElementById("toolDiameter");
  const presetSelect = document.getElementById("presetSelect");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const feedRateXyInput = document.getElementById("feedRateXy");
  const plungeFeedInput = document.getElementById("plungeFeed");
  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");

  // Common UI Elements
  const addToJobQueueBtn = document.getElementById("addToJobQueueBtn");
  const gcodeOutput = document.getElementById("gcodeOutput");
  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");
  const statInstances = document.getElementById("statInstances");
  const statPattern = document.getElementById("statPattern");
  const statTime = document.getElementById("statTime");
  const statDialect = document.getElementById("statDialect");
  const warningBanner = document.getElementById("warningBanner");

  const DEWALT_DIALS = { 1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000 };

  // Mode Switch Handler
  nestingModeSelect.addEventListener("change", () => {
    const mode = nestingModeSelect.value;
    if (mode === "step_and_repeat") {
      stepRepeatCard.style.display = "block";
      softJawCard.style.display = "none";
      toolingSpeedsCard.style.display = "none";
      statPattern.textContent = layoutPatternSelect.value.toUpperCase();
      statInstances.textContent = (parseInt(colsXInput.value, 10) || 1) * (parseInt(rowsYInput.value, 10) || 1);
    } else {
      stepRepeatCard.style.display = "none";
      softJawCard.style.display = "block";
      toolingSpeedsCard.style.display = "block";
      statPattern.textContent = jawTypeSelect.value === "round_bore" ? "BORE JAW" : "RECT JAW";
      statInstances.textContent = "1 Cavity";
    }
  });

  // Soft Jaw Type Switch Handler
  jawTypeSelect.addEventListener("change", () => {
    const isRound = jawTypeSelect.value === "round_bore";
    rectJawDimensions.style.display = isRound ? "none" : "flex";
    dogboneRow.style.display = isRound ? "none" : "flex";
    roundJawDimensions.style.display = isRound ? "block" : "none";
    statPattern.textContent = isRound ? "BORE JAW" : "RECT JAW";
  });

  loadSampleSnippetBtn.addEventListener("click", () => {
    sourceGCodeInput.value = `( Sample Circle Contour )
G0 X0 Y0
G1 Z-3.000 F250.0
G2 X0.000 Y0.000 I15.000 J0.000 F800.0
G0 Z5.000`;
  });

  async function initData() {
    try {
      activeMachine = await API.getActiveMachine();
      if (activeMachine) {
        statDialect.textContent = activeMachine.controller_dialect.toUpperCase();
        arraySafeZInput.value = activeMachine.safe_z_retract || 5.0;
        if (activeMachine.spindle_type === "router") {
          routerDialGroup.style.display = "block";
          routerModelBadge.textContent = activeMachine.router_model === "dewalt_611" ? "DeWalt DWP611" : "Router";
        } else {
          routerDialGroup.style.display = "none";
        }
      }

      const rawTools = await API.getTools();
      toolsList = Array.isArray(rawTools) ? rawTools : (rawTools.data || []);
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

  toolSelect.addEventListener("change", () => {
    const tId = parseInt(toolSelect.value, 10);
    const sel = toolsList.find((t) => t.id === tId);
    if (sel) {
      toolDiameterInput.value = sel.diameter;
      populatePresets(sel);
    }
  });

  presetSelect.addEventListener("change", () => {
    const pId = parseInt(presetSelect.value, 10);
    const toolId = parseInt(toolSelect.value, 10);
    const selectedTool = toolsList.find((t) => t.id === toolId);
    if (selectedTool && selectedTool.material_presets) {
      const preset = selectedTool.material_presets.find((p) => p.id === pId);
      applyPreset(preset);
    }
  });

  function handleGenerationSuccess(gcode, count, patternName) {
    currentGeneratedGCode = gcode;
    statInstances.textContent = count;
    statPattern.textContent = patternName;
    copyGcodeBtn.disabled = false;
    downloadGcodeBtn.disabled = false;

    // 1. Load G-Code into 3D Visualizer & Simulation
    if (visualizer && visualizer.loadGCode) {
      visualizer.loadGCode(currentGeneratedGCode);
    }

    // 2. Render Interactive G-Code Editor with Plain English Hints
    const inspector = new GCodeInspector();
    inspector.renderInteractiveEditor(
      gcodeOutput,
      currentGeneratedGCode,
      (block, lineIdx) => {
        const hintEl = document.getElementById("hintText");
        if (hintEl) hintEl.textContent = block.explanation;
        inspector.renderModalStateBar(document.getElementById("modalStateBar"), block);
        if (visualizer && visualizer.setHighlightedLine) {
          visualizer.setHighlightedLine(lineIdx);
        }
      }
    );

    const linesCount = gcode.split("\n").length;
    const estSec = Math.max(15, Math.round(linesCount * 0.4));
    const mins = Math.floor(estSec / 60);
    const secs = estSec % 60;
    statTime.textContent = `~${mins}m ${secs.toString().padStart(2, "0")}s`;
  }


  // Generate Step-and-Repeat Array
  generateArrayBtn.addEventListener("click", async () => {
    const snippet = sourceGCodeInput.value.trim();
    if (!snippet) {
      alert("Please provide a base G-code snippet to array.");
      return;
    }

    const payload = {
      gcode: snippet,
      cols_x: parseInt(colsXInput.value, 10) || 2,
      rows_y: parseInt(rowsYInput.value, 10) || 2,
      spacing_x: parseFloat(spacingXInput.value) || 60.0,
      spacing_y: parseFloat(spacingYInput.value) || 50.0,
      layout_pattern: layoutPatternSelect.value,
      order_strategy: orderStrategySelect.value,
      safe_z_retract: parseFloat(arraySafeZInput.value) || 5.0,
      dialect: activeMachine ? activeMachine.controller_dialect : "grbl",
      units: "mm",
    };

    try {
      generateArrayBtn.disabled = true;
      generateArrayBtn.textContent = "⏳ Generating Array...";
      const res = await API.generateStepAndRepeatGrid(payload);
      if (res && res.data && res.data.gcode) {
        handleGenerationSuccess(res.data.gcode, `${res.data.total_instances} parts`, res.data.layout_pattern.toUpperCase());
      }
    } catch (err) {
      alert("Step-and-repeat generation failed: " + err.message);
    } finally {
      generateArrayBtn.disabled = false;
      generateArrayBtn.textContent = "⚡ Generate Step-and-Repeat Array & Preview";
    }
  });

  // Generate Soft Jaw Fixture
  generateSoftJawBtn.addEventListener("click", async () => {
    const isRound = jawTypeSelect.value === "round_bore";
    const payload = {
      jaw_type: jawTypeSelect.value,
      part_length_x: parseFloat(partLengthXInput.value) || 60.0,
      part_width_y: parseFloat(partWidthYInput.value) || 40.0,
      part_diameter: parseFloat(partDiameterInput.value) || 50.0,
      step_depth_z: parseFloat(stepDepthZInput.value) || 3.0,
      jaw_gap: parseFloat(jawGapInput.value) || 10.0,
      dogbone_relief: dogboneReliefSelect.value === "true",
      tool_diameter: parseFloat(toolDiameterInput.value) || 6.35,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
      feed_rate_xy: parseFloat(feedRateXyInput.value) || 1000.0,
      plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      safe_z_retract: activeMachine ? activeMachine.safe_z_retract || 5.0 : 5.0,
      dialect: activeMachine ? activeMachine.controller_dialect : "grbl",
      units: "mm",
    };

    try {
      generateSoftJawBtn.disabled = true;
      generateSoftJawBtn.textContent = "⏳ Generating Soft Jaw...";
      const res = await API.generateSoftJawFixture(payload);
      if (res && res.data && res.data.gcode) {
        handleGenerationSuccess(res.data.gcode, "1 Cavity", isRound ? "BORE JAW" : "RECT JAW");
      }
    } catch (err) {
      alert("Soft jaw generation failed: " + err.message);
    } finally {
      generateSoftJawBtn.disabled = false;
      generateSoftJawBtn.textContent = "⚡ Generate Soft Jaw G-Code & Preview";
    }
  });

  // Copy & Download Handlers
  copyGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    navigator.clipboard.writeText(currentGeneratedGCode);
    const orig = copyGcodeBtn.textContent;
    copyGcodeBtn.textContent = "✅ Copied!";
    setTimeout(() => (copyGcodeBtn.textContent = orig), 1500);
  });

  downloadGcodeBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) return;
    const blob = new Blob([currentGeneratedGCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const mode = nestingModeSelect.value;
    a.href = url;
    a.download = mode === "soft_jaw" ? "soft_jaw_fixture.nc" : "step_and_repeat_array.nc";
    a.click();
    URL.revokeObjectURL(url);
  });

  // Multi-Op Job Builder Queue Integration
  if (addToJobQueueBtn) {
    addToJobQueueBtn.addEventListener("click", () => {
      const toolId = toolSelect.value ? parseInt(toolSelect.value, 10) : 1;
      const selectedTool = toolsList.find((t) => t.id === toolId);
      const isRound = jawTypeSelect.value === "round_bore";

      const opPayload = {
        op_name: `Soft Jaw (${isRound ? 'Ø' + partDiameterInput.value + 'mm' : partLengthXInput.value + 'x' + partWidthYInput.value + 'mm'})`,
        op_type: "soft_jaw",
        tool_number: selectedTool ? selectedTool.tool_number : 1,
        tool_name: selectedTool ? selectedTool.name : "Endmill",
        tool_diameter: selectedTool ? selectedTool.diameter : parseFloat(toolDiameterInput.value) || 6.35,
        spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
        feed_rate_xy: parseFloat(feedRateXyInput.value) || 1000.0,
        plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
        params: {
          jaw_type: jawTypeSelect.value,
          part_length_x: parseFloat(partLengthXInput.value) || 60.0,
          part_width_y: parseFloat(partWidthYInput.value) || 40.0,
          part_diameter: parseFloat(partDiameterInput.value) || 50.0,
          step_depth_z: parseFloat(stepDepthZInput.value) || 3.0,
          jaw_gap: parseFloat(jawGapInput.value) || 10.0,
          dogbone_relief: dogboneReliefSelect.value === "true",
          tool_diameter: parseFloat(toolDiameterInput.value) || 6.35,
          stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 1000.0,
          plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
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
