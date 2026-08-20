/**
 * 2.5D Profile & Contour Milling Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  const visualizer = new ToolpathVisualizer("toolpathCanvas");
  let activeMachine = null;
  let toolsList = [];
  let currentGeneratedGCode = "";

  // Preset profiles definitions
  const SHAPE_PRESETS = {
    rectangle: {
      startX: 0.0,
      startY: 0.0,
      isClosed: true,
      segments: [
        { type: "line", x: 40.0, y: 0.0, i: 0, j: 0, cw: false },
        { type: "line", x: 40.0, y: 30.0, i: 0, j: 0, cw: false },
        { type: "line", x: 0.0, y: 30.0, i: 0, j: 0, cw: false },
        { type: "line", x: 0.0, y: 0.0, i: 0, j: 0, cw: false },
      ]
    },
    l_bracket: {
      startX: 0.0,
      startY: 0.0,
      isClosed: true,
      segments: [
        { type: "line", x: 50.0, y: 0.0, i: 0, j: 0, cw: false },
        { type: "line", x: 50.0, y: 20.0, i: 0, j: 0, cw: false },
        { type: "line", x: 20.0, y: 20.0, i: 0, j: 0, cw: false },
        { type: "line", x: 20.0, y: 50.0, i: 0, j: 0, cw: false },
        { type: "line", x: 0.0, y: 50.0, i: 0, j: 0, cw: false },
        { type: "line", x: 0.0, y: 0.0, i: 0, j: 0, cw: false },
      ]
    },
    slot: {
      startX: 10.0,
      startY: 0.0,
      isClosed: true,
      segments: [
        { type: "line", x: 40.0, y: 0.0, i: 0, j: 0, cw: false },
        { type: "arc", x: 40.0, y: 20.0, i: 0, j: 10.0, cw: false },
        { type: "line", x: 10.0, y: 20.0, i: 0, j: 0, cw: false },
        { type: "arc", x: 10.0, y: 0.0, i: 0, j: -10.0, cw: false },
      ]
    },
    hexagon: {
      startX: 30.0,
      startY: 0.0,
      isClosed: true,
      segments: [
        { type: "line", x: 15.0, y: 25.98, i: 0, j: 0, cw: false },
        { type: "line", x: -15.0, y: 25.98, i: 0, j: 0, cw: false },
        { type: "line", x: -30.0, y: 0.0, i: 0, j: 0, cw: false },
        { type: "line", x: -15.0, y: -25.98, i: 0, j: 0, cw: false },
        { type: "line", x: 15.0, y: -25.98, i: 0, j: 0, cw: false },
        { type: "line", x: 30.0, y: 0.0, i: 0, j: 0, cw: false },
      ]
    }
  };

  let currentSegments = JSON.parse(JSON.stringify(SHAPE_PRESETS.rectangle.segments));

  // Form Elements
  const shapePresetSelect = document.getElementById("shapePresetSelect");
  const cutSideSelect = document.getElementById("cutSide");
  const leadInTypeSelect = document.getElementById("leadInType");
  const leadInRadiusInput = document.getElementById("leadInRadius");
  const isClosedLoopSelect = document.getElementById("isClosedLoop");

  const startXInput = document.getElementById("startX");
  const startYInput = document.getElementById("startY");
  const segmentsTableBody = document.getElementById("segmentsTableBody");
  const addLineSegBtn = document.getElementById("addLineSegBtn");
  const addArcSegBtn = document.getElementById("addArcSegBtn");

  const startZInput = document.getElementById("startZ");
  const targetDepthInput = document.getElementById("targetDepth");
  const stepdownZInput = document.getElementById("stepdownZ");
  const retractZInput = document.getElementById("retractZ");
  const finishAllowanceInput = document.getElementById("finishAllowance");
  const springPassSelect = document.getElementById("springPass");

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

  const statSegments = document.getElementById("statSegments");
  const statZPasses = document.getElementById("statZPasses");
  const statTime = document.getElementById("statTime");
  const statDialect = document.getElementById("statDialect");
  const warningBanner = document.getElementById("warningBanner");

  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");

  const DEWALT_DIALS = { 1: 16000, 2: 18200, 3: 20400, 4: 22600, 5: 24800, 6: 27000 };

  function renderSegmentsTable() {
    segmentsTableBody.innerHTML = "";
    currentSegments.forEach((seg, idx) => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-color)";

      tr.innerHTML = `
        <td style="padding: 4px 8px; font-weight: 600;">${idx + 1}</td>
        <td style="padding: 4px 8px;">
          <select class="seg-type" data-idx="${idx}" style="font-size: 0.75rem; padding: 2px 4px;">
            <option value="line" ${seg.type === "line" ? "selected" : ""}>Line</option>
            <option value="arc" ${seg.type === "arc" ? "selected" : ""}>Arc</option>
          </select>
        </td>
        <td style="padding: 4px 8px;">
          <input type="number" step="0.1" class="seg-x" data-idx="${idx}" value="${seg.x}" style="width: 65px; font-size: 0.75rem; padding: 2px 4px;">
        </td>
        <td style="padding: 4px 8px;">
          <input type="number" step="0.1" class="seg-y" data-idx="${idx}" value="${seg.y}" style="width: 65px; font-size: 0.75rem; padding: 2px 4px;">
        </td>
        <td style="padding: 4px 8px;">
          ${seg.type === "arc" ? `
            <span style="font-size: 0.7rem;">I:<input type="number" step="0.1" class="seg-i" data-idx="${idx}" value="${seg.i || 0}" style="width: 45px; font-size: 0.7rem; padding: 1px 2px;">
            J:<input type="number" step="0.1" class="seg-j" data-idx="${idx}" value="${seg.j || 0}" style="width: 45px; font-size: 0.7rem; padding: 1px 2px;">
            <select class="seg-dir" data-idx="${idx}" style="font-size: 0.7rem;">
              <option value="ccw" ${!seg.cw ? "selected" : ""}>CCW (G3)</option>
              <option value="cw" ${seg.cw ? "selected" : ""}>CW (G2)</option>
            </select></span>
          ` : `<span style="color: var(--text-muted); font-size: 0.75rem;">—</span>`}
        </td>
        <td style="padding: 4px 8px; text-align: center;">
          <button type="button" class="del-seg-btn" data-idx="${idx}" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 0.85rem;" title="Delete segment">✕</button>
        </td>
      `;
      segmentsTableBody.appendChild(tr);
    });

    statSegments.textContent = currentSegments.length;
    attachTableEvents();
    updatePreview();
  }

  function attachTableEvents() {
    document.querySelectorAll(".seg-type").forEach(el => {
      el.addEventListener("change", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments[idx].type = e.target.value;
        if (e.target.value === "arc" && currentSegments[idx].i === undefined) {
          currentSegments[idx].i = 0.0;
          currentSegments[idx].j = 10.0;
          currentSegments[idx].cw = false;
        }
        shapePresetSelect.value = "custom";
        renderSegmentsTable();
      });
    });

    document.querySelectorAll(".seg-x").forEach(el => {
      el.addEventListener("input", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments[idx].x = parseFloat(e.target.value) || 0;
        shapePresetSelect.value = "custom";
        updatePreview();
      });
    });

    document.querySelectorAll(".seg-y").forEach(el => {
      el.addEventListener("input", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments[idx].y = parseFloat(e.target.value) || 0;
        shapePresetSelect.value = "custom";
        updatePreview();
      });
    });

    document.querySelectorAll(".seg-i").forEach(el => {
      el.addEventListener("input", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments[idx].i = parseFloat(e.target.value) || 0;
        shapePresetSelect.value = "custom";
        updatePreview();
      });
    });

    document.querySelectorAll(".seg-j").forEach(el => {
      el.addEventListener("input", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments[idx].j = parseFloat(e.target.value) || 0;
        shapePresetSelect.value = "custom";
        updatePreview();
      });
    });

    document.querySelectorAll(".seg-dir").forEach(el => {
      el.addEventListener("change", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments[idx].cw = (e.target.value === "cw");
        shapePresetSelect.value = "custom";
        updatePreview();
      });
    });

    document.querySelectorAll(".del-seg-btn").forEach(el => {
      el.addEventListener("click", (e) => {
        const idx = parseInt(e.target.dataset.idx, 10);
        currentSegments.splice(idx, 1);
        shapePresetSelect.value = "custom";
        renderSegmentsTable();
      });
    });
  }

  addLineSegBtn.addEventListener("click", () => {
    const last = currentSegments[currentSegments.length - 1] || { x: parseFloat(startXInput.value) || 0, y: parseFloat(startYInput.value) || 0 };
    currentSegments.push({ type: "line", x: last.x + 20.0, y: last.y, i: 0, j: 0, cw: false });
    shapePresetSelect.value = "custom";
    renderSegmentsTable();
  });

  addArcSegBtn.addEventListener("click", () => {
    const last = currentSegments[currentSegments.length - 1] || { x: parseFloat(startXInput.value) || 0, y: parseFloat(startYInput.value) || 0 };
    currentSegments.push({ type: "arc", x: last.x + 20.0, y: last.y + 20.0, i: 0, j: 10.0, cw: false });
    shapePresetSelect.value = "custom";
    renderSegmentsTable();
  });

  shapePresetSelect.addEventListener("change", () => {
    const key = shapePresetSelect.value;
    if (SHAPE_PRESETS[key]) {
      const preset = SHAPE_PRESETS[key];
      startXInput.value = preset.startX;
      startYInput.value = preset.startY;
      isClosedLoopSelect.value = preset.isClosed ? "true" : "false";
      currentSegments = JSON.parse(JSON.stringify(preset.segments));
      renderSegmentsTable();
    }
  });

  async function initData() {
    try {
      activeMachine = await API.getActiveMachine();
      if (activeMachine) {
        statDialect.textContent = activeMachine.controller_dialect.toUpperCase();
        retractZInput.value = activeMachine.safe_z_retract || 5.0;
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


  function updatePreview() {
    if (currentGeneratedGCode) return;
    const sx = parseFloat(startXInput.value) || 0;
    const sy = parseFloat(startYInput.value) || 0;

    visualizer.clear();
    let cx = sx;
    let cy = sy;

    currentSegments.forEach(seg => {
      visualizer.drawPoint(cx, cy, "#38bdf8", 3);
      visualizer.drawLine(cx, cy, seg.x, seg.y, "#0ea5e9", 2);
      cx = seg.x;
      cy = seg.y;
    });
    visualizer.drawPoint(cx, cy, "#38bdf8", 3);
  }

  // Generate G-Code Handler
  generateBtn.addEventListener("click", async () => {
    if (currentSegments.length === 0) {
      alert("Please configure at least one profile geometry segment.");
      return;
    }

    const payload = {
      segments: currentSegments,
      start_point: [parseFloat(startXInput.value) || 0.0, parseFloat(startYInput.value) || 0.0],
      is_closed: isClosedLoopSelect.value === "true",
      side: cutSideSelect.value,
      lead_in_type: leadInTypeSelect.value,
      lead_in_radius: parseFloat(leadInRadiusInput.value) || 5.0,
      target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
      start_z: parseFloat(startZInput.value) || 0.0,
      stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
      retract_z: parseFloat(retractZInput.value) || 5.0,
      finish_allowance: parseFloat(finishAllowanceInput.value) || 0.2,
      spring_pass: springPassSelect.value === "true",
      tool_diameter: parseFloat(toolDiameterInput.value) || 3.175,
      tool_id: toolSelect.value ? parseInt(toolSelect.value, 10) : null,
      feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
      plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      spindle_type: activeMachine ? activeMachine.spindle_type : "router",
      router_model: activeMachine ? activeMachine.router_model : "dewalt_611",
      router_dial: activeMachine?.spindle_type === "router" ? parseInt(routerDialSelect.value, 10) : null,
      material_preset_id: presetSelect.value ? parseInt(presetSelect.value, 10) : null,
    };

    generateBtn.disabled = true;
    generateBtn.textContent = "Calculating Contour Toolpaths...";

    try {
      const result = await API.generateContourMilling(payload);
      currentGeneratedGCode = result.data.gcode;

      // 1. Load into 3D Visualizer
      visualizer.loadGCode(currentGeneratedGCode);

      // 2. Render Interactive G-Code Editor with Hints
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
      statZPasses.textContent = result.data.passes;
      statDialect.textContent = result.dialect_used.toUpperCase();

      copyGcodeBtn.disabled = false;
      downloadGcodeBtn.disabled = false;
    } catch (err) {
      alert("Failed to generate Contouring G-Code: " + err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Contour G-Code & Preview";
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
    a.download = `contouring_${Date.now()}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Add to Job Queue Handler
  const addToJobQueueBtn = document.getElementById("addToJobQueueBtn");
  if (addToJobQueueBtn) {
    addToJobQueueBtn.addEventListener("click", () => {
      if (currentSegments.length === 0) {
        alert("Please configure at least one profile geometry segment first.");
        return;
      }
      const toolId = toolSelect.value ? parseInt(toolSelect.value, 10) : 1;
      const selectedTool = toolsList.find((t) => t.id === toolId);
      const sideName = cutSideSelect.value.toUpperCase();

      const opPayload = {
        op_name: `Contour ${sideName} (${currentSegments.length} segs)`,
        op_type: "contouring",
        tool_number: selectedTool ? selectedTool.tool_number : 1,
        tool_name: selectedTool ? selectedTool.name : "Endmill",
        tool_diameter: selectedTool ? selectedTool.diameter : parseFloat(toolDiameterInput.value) || 3.175,
        spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
        feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
        plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
        params: {
          segments: currentSegments,
          start_point: [parseFloat(startXInput.value) || 0.0, parseFloat(startYInput.value) || 0.0],
          is_closed: isClosedLoopSelect.value === "true",
          side: cutSideSelect.value,
          lead_in_type: leadInTypeSelect.value,
          lead_in_radius: parseFloat(leadInRadiusInput.value) || 5.0,
          target_depth_z: parseFloat(targetDepthInput.value) || -5.0,
          start_z: parseFloat(startZInput.value) || 0.0,
          stepdown_z: parseFloat(stepdownZInput.value) || 1.5,
          retract_z: parseFloat(retractZInput.value) || 5.0,
          finish_allowance: parseFloat(finishAllowanceInput.value) || 0.2,
          spring_pass: springPassSelect.value === "true",
          tool_diameter: parseFloat(toolDiameterInput.value) || 3.175,
          feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
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
  renderSegmentsTable();
});
