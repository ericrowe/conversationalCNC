/**
 * Text Engraving Operation Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";

  const layoutTabs = document.querySelectorAll(".layout-tab");
  const linearInputs = document.getElementById("linearLayoutInputs");
  const arcInputs = document.getElementById("arcLayoutInputs");

  const engravingTextInput = document.getElementById("engravingText");
  const fontSelect = document.getElementById("fontSelect");
  const curveSubdivisionsSelect = document.getElementById("curveSubdivisions");
  const fontSizeInput = document.getElementById("fontSize");
  const letterSpacingInput = document.getElementById("letterSpacing");



  const startXInput = document.getElementById("startX");
  const startYInput = document.getElementById("startY");
  const rotationDegInput = document.getElementById("rotationDeg");
  const alignSelect = document.getElementById("alignSelect");

  const centerXInput = document.getElementById("centerX");
  const centerYInput = document.getElementById("centerY");
  const arcRadiusInput = document.getElementById("arcRadius");
  const startAngleInput = document.getElementById("startAngle");
  const arcDirectionSelect = document.getElementById("arcDirection");
  const arcAlignSelect = document.getElementById("arcAlign");

  const targetDepthInput = document.getElementById("targetDepth");
  const stepdownZInput = document.getElementById("stepdownZ");
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

  const statCharCount = document.getElementById("statCharCount");
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
        retractZInput.value = activeMachine.safe_z_retract || 2.0;

        if (activeMachine.spindle_type === "router") {
          routerDialGroup.style.display = "block";
          routerModelBadge.textContent = activeMachine.router_model === "dewalt_611" ? "DeWalt DWP611" : "Router";
        } else {
          routerDialGroup.style.display = "none";
        }
      }

      // Fetch Fonts
      try {
        const fontData = await API.getEngravingFonts();
        if (fontData && fontData.fonts) {
          const currentVal = fontSelect.value;
          fontSelect.innerHTML = "";
          for (const [key, label] of Object.entries(fontData.fonts)) {
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = label;
            fontSelect.appendChild(opt);
          }
          if (currentVal && fontData.fonts[currentVal]) {
            fontSelect.value = currentVal;
          }
        }
      } catch (fErr) {
        console.warn("Could not fetch font list, using defaults:", fErr);
      }

      toolsList = await API.getTools();
      toolSelect.innerHTML = '<option value="">-- Select Tool --</option>';
      let vbitDefault = null;
      toolsList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `T${t.tool_number}: ${t.name} (${t.diameter}mm)`;
        toolSelect.appendChild(opt);
        if ((t.tool_type === "vbit" || t.name.toLowerCase().includes("v-bit") || t.name.toLowerCase().includes("engrav")) && !vbitDefault) {
          vbitDefault = t;
        }
      });

      const selected = vbitDefault || toolsList[0];
      if (selected) {
        toolSelect.value = selected.id;
        const isVbit = selected.tool_type === "vbit" || selected.name.toLowerCase().includes("v-bit") || selected.name.toLowerCase().includes("engrav");
        toolDiameterInput.value = isVbit ? 0.20 : selected.diameter;
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
      syncDialFromRpm(preset.spindle_speed);
    }
  }

  toolSelect?.addEventListener("change", () => {
    const selectedId = parseInt(toolSelect.value, 10);
    const tool = toolsList.find((t) => t.id === selectedId);
    if (tool) {
      const isVbit = tool.tool_type === "vbit" || tool.name.toLowerCase().includes("v-bit") || tool.name.toLowerCase().includes("engrav");
      toolDiameterInput.value = isVbit ? 0.20 : tool.diameter;
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

  let activeLayout = "linear";
  layoutTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      layoutTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeLayout = tab.dataset.layout;

      linearInputs.style.display = activeLayout === "linear" ? "block" : "none";
      arcInputs.style.display = activeLayout === "arc" ? "block" : "none";

      updatePreview();
    });
  });

  function updatePreview() {
    const text = engravingTextInput.value || "CNC";
    statCharCount.textContent = text.length;

    const targetZ = parseFloat(targetDepthInput.value) || -0.5;
    const stepZ = parseFloat(stepdownZInput.value) || 0.5;
    const zPasses = Math.max(1, Math.ceil(Math.abs(targetZ) / stepZ));
    statZPasses.textContent = zPasses;

    // Estimate stroke width on surface
    const tipWidth = parseFloat(toolDiameterInput.value) || 0.20;
    const cutDepth = Math.abs(targetZ);
    const selectedToolId = parseInt(toolSelect.value, 10);
    const selectedTool = toolsList.find((t) => t.id === selectedToolId);
    const isVbit = selectedTool ? (selectedTool.tool_type === "vbit" || selectedTool.name.toLowerCase().includes("v-bit") || selectedTool.name.toLowerCase().includes("engrav")) : true;

    let estWidth = tipWidth;
    if (isVbit) {
      const angleDeg = selectedTool?.name.includes("90") ? 90 : 60;
      const halfAngleRad = (angleDeg / 2.0) * (Math.PI / 180.0);
      estWidth = tipWidth + 2.0 * cutDepth * Math.tan(halfAngleRad);
    }

    const estWidthEl = document.getElementById("estimatedStrokeWidth");
    if (estWidthEl) {
      estWidthEl.textContent = `~${estWidth.toFixed(2)} mm (${isVbit ? "V-groove at Z" + targetZ.toFixed(2) : "Cutter width"})`;
    }

    const envelope = activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null;


    visualizer.setData({
      opType: "engraving",
      machineEnvelope: envelope,
      engraving: {
        text: text,
        layoutMode: activeLayout,
        startX: parseFloat(startXInput.value) || 20.0,
        startY: parseFloat(startYInput.value) || 30.0,
        rotationDeg: parseFloat(rotationDegInput.value) || 0.0,
        align: alignSelect.value,
        centerX: parseFloat(centerXInput.value) || 50.0,
        centerY: parseFloat(centerYInput.value) || 50.0,
        arcRadius: parseFloat(arcRadiusInput.value) || 35.0,
        startAngleDeg: parseFloat(startAngleInput.value) || 90.0,
        arcDirection: arcDirectionSelect.value,
        fontSize: parseFloat(fontSizeInput.value) || 10.0,
        letterSpacing: parseFloat(letterSpacingInput.value) || 1.0,
        fontName: fontSelect ? fontSelect.value : "simplex_sans",
        curveSubdivisions: curveSubdivisionsSelect ? parseInt(curveSubdivisionsSelect.value, 10) || 4 : 4,
      },
    });
  }

  document.querySelectorAll("#engravingForm input, #engravingForm select, #engravingForm textarea").forEach((el) => {
    el.addEventListener("input", () => {
      visualizer.clearGCode();
      updatePreview();
    });
  });

  document.getElementById("zoomInBtn")?.addEventListener("click", () => visualizer.zoom(1.2));
  document.getElementById("zoomOutBtn")?.addEventListener("click", () => visualizer.zoom(0.8));
  document.getElementById("fitViewBtn")?.addEventListener("click", () => visualizer.autoFit());

  // Generate G-Code Handler
  generateBtn.addEventListener("click", async () => {
    const text = engravingTextInput.value;
    if (!text.trim()) {
      alert("Please enter text to engrave.");
      return;
    }

    const payload = {
      text: text,
      layout_mode: activeLayout,
      start_x: parseFloat(startXInput.value) || 0.0,
      start_y: parseFloat(startYInput.value) || 0.0,
      rotation_deg: parseFloat(rotationDegInput.value) || 0.0,
      align: activeLayout === "linear" ? alignSelect.value : arcAlignSelect.value,
      center_x: parseFloat(centerXInput.value) || 0.0,
      center_y: parseFloat(centerYInput.value) || 0.0,
      arc_radius: parseFloat(arcRadiusInput.value) || 30.0,
      start_angle_deg: parseFloat(startAngleInput.value) || 90.0,
      arc_direction: arcDirectionSelect.value,
      font_size: parseFloat(fontSizeInput.value) || 10.0,
      letter_spacing: parseFloat(letterSpacingInput.value) || 1.0,
      font_name: fontSelect ? fontSelect.value : "simplex_sans",
      curve_subdivisions: curveSubdivisionsSelect ? parseInt(curveSubdivisionsSelect.value, 10) || 4 : 4,
      target_depth_z: parseFloat(targetDepthInput.value) || -0.5,

      stepdown_z: parseFloat(stepdownZInput.value) || 0.5,
      start_z: 0.0,
      retract_z: parseFloat(retractZInput.value) || 2.0,
      feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
      plunge_feed: parseFloat(plungeFeedInput.value) || 300.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      spindle_type: activeMachine ? activeMachine.spindle_type : "router",
      router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
      router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
    };


    generateBtn.disabled = true;
    generateBtn.textContent = "Calculating Engraving Path...";

    try {
      const result = await API.generateTextEngraving(payload);
      currentGeneratedGCode = result.data.gcode;

      // 1. Load G-Code directly into 3D visualizer & simulation
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

      alert("Failed to generate Engraving G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Engraving G-Code & Preview";
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
    a.download = `engraving_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  await initData();
});
