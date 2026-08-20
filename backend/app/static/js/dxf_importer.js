/**
 * DXF 2D Vector CAD Importer & Direct-to-GCode Controller (Phase 5)
 */

document.addEventListener("DOMContentLoaded", async () => {
  // DOM Elements
  const dxfFileInput = document.getElementById("dxfFileInput");
  const loadSampleBracketBtn = document.getElementById("loadSampleBracketBtn");
  const toggleDxfTextBtn = document.getElementById("toggleDxfTextBtn");
  const dxfTextContainer = document.getElementById("dxfTextContainer");
  const dxfTextInput = document.getElementById("dxfTextInput");
  const parseDxfBtn = document.getElementById("parseDxfBtn");

  const spanBbox = document.getElementById("spanBbox");
  const spanLayers = document.getElementById("spanLayers");
  const spanEntities = document.getElementById("spanEntities");
  const spanChainCount = document.getElementById("spanChainCount");
  const spanCircleCount = document.getElementById("spanCircleCount");

  const opTypeSelect = document.getElementById("opTypeSelect");
  const contourOptionsGroup = document.getElementById("contourOptionsGroup");
  const sideSelect = document.getElementById("sideSelect");
  const finishAllowanceInput = document.getElementById("finishAllowanceInput");
  const springPassInput = document.getElementById("springPassInput");

  const targetDepthInput = document.getElementById("targetDepthInput");
  const stepdownInput = document.getElementById("stepdownInput");
  const retractZInput = document.getElementById("retractZInput");

  const toolSelect = document.getElementById("toolSelect");
  const toolDiameterInput = document.getElementById("toolDiameter");
  const presetSelect = document.getElementById("presetSelect");
  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const feedRateXyInput = document.getElementById("feedRateXy");
  const plungeFeedInput = document.getElementById("plungeFeed");

  const generateDxfBtn = document.getElementById("generateDxfBtn");
  const queueOpBtn = document.getElementById("queueOpBtn");

  const statEntities = document.getElementById("statEntities");
  const statChains = document.getElementById("statChains");
  const statTime = document.getElementById("statTime");
  const statDialect = document.getElementById("statDialect");

  const copyGcodeBtn = document.getElementById("copyGcodeBtn");
  const downloadGcodeBtn = document.getElementById("downloadGcodeBtn");
  const gcodeOutput = document.getElementById("gcodeOutput");
  const warningBanner = document.getElementById("warningBanner");

  // State
  let toolsList = [];
  let activeMachine = null;
  let parsedDxfData = null;
  let currentGeneratedGCode = "";
  // Initialize 3D Visualizer
  const visualizer = new ToolpathVisualizer("toolpathCanvas");


  // DeWalt DWP611 Speed Dial Map
  const DEWALT_DIALS = {
    1: 16000,
    2: 18200,
    3: 20400,
    4: 22600,
    5: 24800,
    6: 27000,
  };

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

  // Load Machine & Tool data
  async function initData() {
    try {
      activeMachine = await API.getActiveMachine();
      if (activeMachine) {
        statDialect.textContent = activeMachine.controller_dialect.toUpperCase();
        if (retractZInput) retractZInput.value = activeMachine.safe_z_retract || 5.0;
        if (activeMachine.spindle_type === "router") {
          routerDialGroup.style.display = "block";
          if (routerModelBadge) routerModelBadge.textContent = activeMachine.router_model === "dewalt_611" ? "DeWalt DWP611" : "Router";
        } else {
          routerDialGroup.style.display = "none";
        }
        if (visualizer) {
          visualizer.machineEnvelope = {
            x: activeMachine.work_area_x,
            y: activeMachine.work_area_y,
          };
          visualizer.draw();
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
      if (preset.pass_depth && stepdownInput) stepdownInput.value = preset.pass_depth;
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
    const sel = toolsList.find((t) => t.id === toolId);
    if (sel && sel.material_presets) {
      const preset = sel.material_presets.find((p) => p.id === pId);
      applyPreset(preset);
    }
  });

  // Toggle DXF Textarea
  toggleDxfTextBtn.addEventListener("click", () => {
    dxfTextContainer.style.display = dxfTextContainer.style.display === "none" ? "block" : "none";
  });

  // Sample DXF ASCII Generator
  function getSampleBracketDxf() {
    return `0
SECTION
2
ENTITIES
0
LWPOLYLINE
8
0
70
1
90
4
10
0.0
20
0.0
10
60.0
20
0.0
10
60.0
20
40.0
10
0.0
20
40.0
0
CIRCLE
8
HOLES
10
15.0
20
20.0
40
2.5
0
CIRCLE
8
HOLES
10
45.0
20
20.0
40
2.5
0
ENDSEC
0
EOF`;
  }

  loadSampleBracketBtn.addEventListener("click", () => {
    const sample = getSampleBracketDxf();
    dxfTextInput.value = sample;
    dxfTextContainer.style.display = "block";
    parseDxf(sample);
  });

  // File Upload Handling
  dxfFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target.result;
      dxfTextInput.value = content;
      parseDxf(content);
    };
    reader.readAsText(file);
  });

  parseDxfBtn.addEventListener("click", () => {
    const text = dxfTextInput.value.trim();
    if (!text) {
      alert("Please upload a .dxf file or paste DXF text first.");
      return;
    }
    parseDxf(text);
  });

  opTypeSelect.addEventListener("change", () => {
    const isContour = opTypeSelect.value === "contour";
    contourOptionsGroup.style.display = isContour ? "block" : "none";
  });

  async function parseDxf(dxfText) {
    try {
      parseDxfBtn.disabled = true;
      parseDxfBtn.textContent = "⏳ Parsing DXF...";
      const res = await API.parseDXF({ dxf_text: dxfText });
      parsedDxfData = res.data;

      spanBbox.textContent = `${parsedDxfData.bounding_box.width} x ${parsedDxfData.bounding_box.height} mm (X: ${parsedDxfData.bounding_box.min_x}..${parsedDxfData.bounding_box.max_x}, Y: ${parsedDxfData.bounding_box.min_y}..${parsedDxfData.bounding_box.max_y})`;
      spanLayers.textContent = parsedDxfData.layers.join(", ");
      spanEntities.textContent = parsedDxfData.entity_count;
      spanChainCount.textContent = parsedDxfData.chains.length;
      spanCircleCount.textContent = parsedDxfData.circles.length;

      statEntities.textContent = parsedDxfData.entity_count;
      statChains.textContent = parsedDxfData.chains.length + parsedDxfData.circles.length;

      if (parsedDxfData.circles.length > 0 && parsedDxfData.chains.length === 0) {
        opTypeSelect.value = "drill";
        contourOptionsGroup.style.display = "none";
      }

      // Auto-trigger toolpath preview
      await generateToolpath();
    } catch (err) {
      alert("Failed to parse DXF: " + err.message);
    } finally {
      parseDxfBtn.disabled = false;
      parseDxfBtn.textContent = "🔍 Parse DXF Geometry";
    }
  }

  async function generateToolpath() {
    if (!parsedDxfData) {
      alert("Please parse a DXF drawing first.");
      return;
    }

    const tId = parseInt(toolSelect.value, 10);
    const selTool = toolsList.find((t) => t.id === tId) || null;

    const payload = {
      chains: parsedDxfData.chains,
      circles: parsedDxfData.circles,
      operation_type: opTypeSelect.value,
      side: sideSelect.value,
      target_depth_z: parseFloat(targetDepthInput.value) || -6.0,
      stepdown_z: parseFloat(stepdownInput.value) || 1.5,
      finish_allowance: parseFloat(finishAllowanceInput.value) || 0.0,
      spring_pass: springPassInput.checked,
      tool_id: selTool ? selTool.id : null,
      tool_diameter: parseFloat(toolDiameterInput.value) || 3.175,
      tool_number: selTool ? selTool.tool_number : 1,
      tool_name: selTool ? selTool.name : "Endmill",
      feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
      plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
      spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
      safe_z_retract: parseFloat(retractZInput.value) || 5.0,
      units: "mm",
    };

    try {
      generateDxfBtn.disabled = true;
      generateDxfBtn.textContent = "⏳ Generating Toolpath...";

      const res = await API.generateDXFToolpath(payload);
      currentGeneratedGCode = res.data.gcode;

      copyGcodeBtn.disabled = false;
      downloadGcodeBtn.disabled = false;
      statDialect.textContent = (res.dialect_used || "GRBL").toUpperCase();

      // 1. Load into 3D Visualizer
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

      const linesCount = currentGeneratedGCode.split("\n").length;
      const estSec = Math.max(15, Math.round(linesCount * 0.35));
      const mins = Math.floor(estSec / 60);
      const secs = estSec % 60;
      statTime.textContent = `~${mins}m ${secs.toString().padStart(2, "0")}s`;
    } catch (err) {
      alert("Failed to generate DXF G-code: " + err.message);
    } finally {
      generateDxfBtn.disabled = false;
      generateDxfBtn.textContent = "⚡ Generate DXF G-Code & Preview";
    }
  }

  generateDxfBtn.addEventListener("click", generateToolpath);

  // Copy & Download Handlers
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
    a.download = `dxf_${opTypeSelect.value}_program.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Queue Operation to Multi-Op Job Builder
  queueOpBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) {
      alert("Please generate DXF G-Code first before queueing.");
      return;
    }

    const tId = parseInt(toolSelect.value, 10);
    const selTool = toolsList.find((t) => t.id === tId) || null;

    if (window.JobBuilder) {
      window.JobBuilder.addOperation({
        id: "op_" + Date.now(),
        name: `DXF ${opTypeSelect.value.toUpperCase()} (Ø${toolDiameterInput.value}mm)`,
        op_type: "contouring",
        tool_number: selTool ? selTool.tool_number : 1,
        tool_name: selTool ? selTool.name : "Endmill",
        tool_diameter: parseFloat(toolDiameterInput.value) || 3.175,
        spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
        feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
        plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
        target_depth_z: parseFloat(targetDepthInput.value) || -6.0,
        raw_gcode: currentGeneratedGCode,
      });

      const origText = queueOpBtn.textContent;
      queueOpBtn.textContent = "✅ Queued!";
      setTimeout(() => (queueOpBtn.textContent = origText), 1800);
    } else {
      alert("Job Builder drawer not loaded.");
    }
  });

  // Initialize
  await initData();
});
