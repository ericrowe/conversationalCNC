/**
 * Surfacing & Facing Operation Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";

  const lengthXInput = document.getElementById("lengthX");
  const widthYInput = document.getElementById("widthY");
  const originModeSelect = document.getElementById("originMode");
  const overtravelInput = document.getElementById("overtravel");

  const totalDepthInput = document.getElementById("totalDepth");
  const stepdownZInput = document.getElementById("stepdownZ");
  const cutDirectionSelect = document.getElementById("cutDirection");
  const stepoverPercentInput = document.getElementById("stepoverPercent");
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

  const statStockArea = document.getElementById("statStockArea");
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
      let flycutterDefault = null;
      toolsList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `T${t.tool_number}: ${t.name} (${t.diameter}mm)`;
        toolSelect.appendChild(opt);
        if (t.diameter >= 20.0 && !flycutterDefault) {
          flycutterDefault = t;
        }
      });

      const selected = flycutterDefault || toolsList[toolsList.length - 1];
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

  function updatePreview() {
    const lenX = parseFloat(lengthXInput.value) || 150.0;
    const widY = parseFloat(widthYInput.value) || 100.0;
    statStockArea.textContent = `${lenX}x${widY}mm`;

    const totalZ = parseFloat(totalDepthInput.value) || 1.0;
    const stepZ = parseFloat(stepdownZInput.value) || 0.5;
    const zPasses = Math.max(1, Math.ceil(totalZ / stepZ));
    statZPasses.textContent = zPasses;

    const envelope = activeMachine ? { x: activeMachine.work_area_x, y: activeMachine.work_area_y } : null;

    visualizer.setData({
      opType: "surfacing",
      machineEnvelope: envelope,
      surfacing: {
        lengthX: lenX,
        widthY: widY,
        originX: 0.0,
        originY: 0.0,
        originMode: originModeSelect.value,
        cutDirection: cutDirectionSelect.value,
        toolDiameter: parseFloat(toolDiameterInput.value) || 25.4,
        stepoverPercent: parseFloat(stepoverPercentInput.value) || 70,
        overtravel: parseFloat(overtravelInput.value) || 3.0,
      },
    });
  }

  document.querySelectorAll("#surfacingForm input, #surfacingForm select").forEach((el) => {
    el.addEventListener("input", () => updatePreview());
  });

  document.getElementById("zoomInBtn")?.addEventListener("click", () => visualizer.zoom(1.2));
  document.getElementById("zoomOutBtn")?.addEventListener("click", () => visualizer.zoom(0.8));
  document.getElementById("fitViewBtn")?.addEventListener("click", () => visualizer.autoFit());

  // Generate G-Code Handler
  generateBtn.addEventListener("click", async () => {
    const payload = {
      length_x: parseFloat(lengthXInput.value),
      width_y: parseFloat(widthYInput.value),
      origin_x: 0.0,
      origin_y: 0.0,
      origin_mode: originModeSelect.value,
      total_depth_z: parseFloat(totalDepthInput.value),
      stepdown_z: parseFloat(stepdownZInput.value),
      tool_diameter: parseFloat(toolDiameterInput.value),
      stepover_percent: parseFloat(stepoverPercentInput.value),
      cut_direction: cutDirectionSelect.value,
      overtravel: parseFloat(overtravelInput.value),
      start_z: 0.0,
      retract_z: parseFloat(retractZInput.value) || 5.0,
      feed_rate_xy: parseFloat(feedRateXyInput.value),
      plunge_feed: parseFloat(plungeFeedInput.value),
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      spindle_type: activeMachine ? activeMachine.spindle_type : "router",
      router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
      router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
    };

    generateBtn.disabled = true;
    generateBtn.textContent = "Calculating Surfacing G-Code...";

    try {
      const result = await API.generateSurfacing(payload);
      currentGeneratedGCode = result.data.gcode;
      gcodeOutput.textContent = currentGeneratedGCode;

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
      alert("Failed to generate Surfacing G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Surfacing G-Code & Preview";
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
    a.download = `surfacing_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  await initData();
});
