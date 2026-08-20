/**
 * SVG 2D Vector CAD Importer & Grayscale Depth Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
  // DOM Elements
  const svgFileInput = document.getElementById("svgFileInput");
  const loadSampleSvgBtn = document.getElementById("loadSampleSvgBtn");
  const toggleSvgTextBtn = document.getElementById("toggleSvgTextBtn");
  const svgTextContainer = document.getElementById("svgTextContainer");
  const svgTextInput = document.getElementById("svgTextInput");
  const parseSvgBtn = document.getElementById("parseSvgBtn");

  const svgWidthInput = document.getElementById("svgWidthInput");
  const svgHeightInput = document.getElementById("svgHeightInput");
  const svgLinkAspectBtn = document.getElementById("svgLinkAspectBtn");
  const svgLinkAspectIcon = document.getElementById("svgLinkAspectIcon");
  const svgLinkAspectText = document.getElementById("svgLinkAspectText");
  const svgResetDimensionsBtn = document.getElementById("svgResetDimensionsBtn");
  const spanOrigDimensions = document.getElementById("spanOrigDimensions");
  const spanAspectRatio = document.getElementById("spanAspectRatio");

  const maxCutDepthInput = document.getElementById("maxCutDepthInput");
  const shadingModeSelect = document.getElementById("shadingModeSelect");
  const invertShadingInput = document.getElementById("invertShadingInput");
  const flipYInput = document.getElementById("flipYInput");
  const legendMaxDepth = document.getElementById("legendMaxDepth");
  const legendMidDepth = document.getElementById("legendMidDepth");

  const spanBbox = document.getElementById("spanBbox");
  const spanEntities = document.getElementById("spanEntities");
  const spanChainCount = document.getElementById("spanChainCount");
  const spanCircleCount = document.getElementById("spanCircleCount");
  const depthTableBody = document.getElementById("depthTableBody");

  const opTypeSelect = document.getElementById("opTypeSelect");
  const sideSelect = document.getElementById("sideSelect");
  const stepdownInput = document.getElementById("stepdownInput");
  const retractZInput = document.getElementById("retractZInput");
  const leadInTypeSelect = document.getElementById("leadInTypeSelect");
  const useGrayscaleDepthsInput = document.getElementById("useGrayscaleDepthsInput");

  const toolSelect = document.getElementById("toolSelect");
  const toolDiameterInput = document.getElementById("toolDiameter");
  const presetSelect = document.getElementById("presetSelect");
  const routerDialGroup = document.getElementById("routerDialGroup");
  const routerDialSelect = document.getElementById("routerDialSelect");
  const routerModelBadge = document.getElementById("routerModelBadge");
  const spindleRpmInput = document.getElementById("spindleRpm");
  const feedRateXyInput = document.getElementById("feedRateXy");
  const plungeFeedInput = document.getElementById("plungeFeed");

  const generateSvgBtn = document.getElementById("generateSvgBtn");
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
  let parsedSvgData = null;
  let currentGeneratedGCode = "";
  let isAspectLinked = true; // Enabled by default
  let nativeSvgWidth = null;
  let nativeSvgHeight = null;
  let currentAspectRatio = 1.0;
  let parseDebounceTimer = null;

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

  function updateDepthLegend() {
    const maxD = Math.abs(parseFloat(maxCutDepthInput?.value) || 6.0);
    const midD = (maxD / 2.0).toFixed(2);
    if (legendMaxDepth) legendMaxDepth.textContent = `-${maxD.toFixed(2)}mm`;
    if (legendMidDepth) legendMidDepth.textContent = `-${midD}mm`;
  }

  function updateLinkAspectButton() {
    if (!svgLinkAspectBtn) return;
    if (isAspectLinked) {
      svgLinkAspectBtn.style.background = "var(--primary-color, #0284c7)";
      svgLinkAspectBtn.style.color = "#ffffff";
      if (svgLinkAspectIcon) svgLinkAspectIcon.textContent = "🔗";
      if (svgLinkAspectText) svgLinkAspectText.textContent = "Linked";
      svgLinkAspectBtn.title = "Aspect Ratio Locked (Linked): Auto-adjusts Height when Width changes and vice versa";

      const w = parseFloat(svgWidthInput?.value);
      const h = parseFloat(svgHeightInput?.value);
      if (w > 0 && h > 0) {
        currentAspectRatio = w / h;
        if (spanAspectRatio) spanAspectRatio.textContent = currentAspectRatio.toFixed(3);
      }
    } else {
      svgLinkAspectBtn.style.background = "var(--bg-input, #1e293b)";
      svgLinkAspectBtn.style.color = "var(--text-muted, #94a3b8)";
      if (svgLinkAspectIcon) svgLinkAspectIcon.textContent = "🔓";
      if (svgLinkAspectText) svgLinkAspectText.textContent = "Unlinked";
      svgLinkAspectBtn.title = "Aspect Ratio Unlocked: Width and Height can be scaled independently";
    }
  }

  svgLinkAspectBtn?.addEventListener("click", () => {
    isAspectLinked = !isAspectLinked;
    updateLinkAspectButton();
  });

  function triggerDebouncedParse() {
    clearTimeout(parseDebounceTimer);
    parseDebounceTimer = setTimeout(() => {
      const text = svgTextInput?.value.trim();
      if (text) {
        parseSvg(text, false);
      }
    }, 450);
  }

  svgWidthInput?.addEventListener("input", () => {
    const w = parseFloat(svgWidthInput.value);
    if (w > 0 && isAspectLinked && currentAspectRatio > 0) {
      const h = w / currentAspectRatio;
      if (svgHeightInput) svgHeightInput.value = parseFloat(h.toFixed(2));
    }
    triggerDebouncedParse();
  });

  svgHeightInput?.addEventListener("input", () => {
    const h = parseFloat(svgHeightInput.value);
    if (h > 0 && isAspectLinked && currentAspectRatio > 0) {
      const w = h * currentAspectRatio;
      if (svgWidthInput) svgWidthInput.value = parseFloat(w.toFixed(2));
    }
    triggerDebouncedParse();
  });

  svgResetDimensionsBtn?.addEventListener("click", () => {
    if (nativeSvgWidth && nativeSvgHeight) {
      if (svgWidthInput) svgWidthInput.value = parseFloat(nativeSvgWidth.toFixed(2));
      if (svgHeightInput) svgHeightInput.value = parseFloat(nativeSvgHeight.toFixed(2));
      currentAspectRatio = nativeSvgWidth / nativeSvgHeight;
      if (spanAspectRatio) spanAspectRatio.textContent = currentAspectRatio.toFixed(3);
      if (svgTextInput.value.trim()) {
        parseSvg(svgTextInput.value.trim(), false);
      }
    }
  });

  updateDepthLegend();
  updateLinkAspectButton();

  maxCutDepthInput?.addEventListener("input", () => {
    updateDepthLegend();
    if (parsedSvgData && svgTextInput.value.trim()) {
      parseSvg(svgTextInput.value.trim());
    }
  });

  invertShadingInput?.addEventListener("change", () => {
    if (parsedSvgData && svgTextInput.value.trim()) {
      parseSvg(svgTextInput.value.trim());
    }
  });

  shadingModeSelect?.addEventListener("change", () => {
    if (parsedSvgData && svgTextInput.value.trim()) {
      parseSvg(svgTextInput.value.trim());
    }
  });

  flipYInput?.addEventListener("change", () => {
    if (parsedSvgData && svgTextInput.value.trim()) {
      parseSvg(svgTextInput.value.trim());
    }
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

  // Toggle SVG Textarea
  toggleSvgTextBtn.addEventListener("click", () => {
    svgTextContainer.style.display = svgTextContainer.style.display === "none" ? "block" : "none";
  });

  // Sample SVG Generator: Multi-Depth Badge with Shading
  function getSampleBadgeSvg() {
    return `<svg width="100mm" height="70mm" viewBox="0 0 100 70" xmlns="http://www.w3.org/2000/svg">
  <!-- Perimeter Profile: 100% Black -> Full Depth (-6.0mm) -->
  <rect x="5" y="5" width="90" height="60" rx="6" ry="6" fill="#000000" stroke="#000000" />
  
  <!-- Stepped Pocket Cavity: 50% Gray -> Mid Depth (-3.0mm) -->
  <circle cx="50" cy="35" r="18" fill="#808080" />
  
  <!-- Center Island / Shallow Detail: 25% Gray -> Light Depth (-1.5mm) -->
  <rect x="42" y="27" width="16" height="16" fill="#c0c0c0" />
  
  <!-- Bolt Mounting Holes: 100% Black -> Full Drill Depth (-6.0mm) -->
  <circle cx="15" cy="35" r="2.5" fill="#000000" />
  <circle cx="85" cy="35" r="2.5" fill="#000000" />
</svg>`;
  }

  loadSampleSvgBtn.addEventListener("click", () => {
    const sample = getSampleBadgeSvg();
    svgTextInput.value = sample;
    svgTextContainer.style.display = "block";
    nativeSvgWidth = null;
    nativeSvgHeight = null;
    if (svgWidthInput) svgWidthInput.value = "";
    if (svgHeightInput) svgHeightInput.value = "";
    parseSvg(sample, true);
  });

  // File Upload Handling
  svgFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target.result;
      svgTextInput.value = content;
      nativeSvgWidth = null;
      nativeSvgHeight = null;
      if (svgWidthInput) svgWidthInput.value = "";
      if (svgHeightInput) svgHeightInput.value = "";
      parseSvg(content, true);
    };
    reader.readAsText(file);
  });

  parseSvgBtn.addEventListener("click", () => {
    const text = svgTextInput.value.trim();
    if (!text) {
      alert("Please upload an .svg file or paste SVG code first.");
      return;
    }
    parseSvg(text, false);
  });

  async function parseSvg(svgText, isInitialFileLoad = false) {
    try {
      parseSvgBtn.disabled = true;
      parseSvgBtn.textContent = "⏳ Parsing SVG...";

      const targetW = (!isInitialFileLoad && svgWidthInput) ? (parseFloat(svgWidthInput.value) || null) : null;
      const targetH = (!isInitialFileLoad && svgHeightInput) ? (parseFloat(svgHeightInput.value) || null) : null;

      const payload = {
        svg_text: svgText,
        default_dpi: 96.0,
        flip_y: flipYInput.checked,
        max_cut_depth: parseFloat(maxCutDepthInput.value) || -6.0,
        invert_shading: invertShadingInput.checked,
        shading_mode: shadingModeSelect.value,
        target_width: targetW,
        target_height: targetH,
      };

      const res = await API.parseSVG(payload);
      parsedSvgData = res.data;

      // Handle Native vs Scaled Dimensions
      if (res.data.original_dimensions) {
        nativeSvgWidth = res.data.original_dimensions.width;
        nativeSvgHeight = res.data.original_dimensions.height;
        currentAspectRatio = res.data.original_dimensions.aspect_ratio || (nativeSvgWidth / (nativeSvgHeight || 1.0));

        if (spanOrigDimensions) {
          spanOrigDimensions.textContent = `${nativeSvgWidth.toFixed(1)} x ${nativeSvgHeight.toFixed(1)} mm`;
        }
        if (spanAspectRatio) {
          spanAspectRatio.textContent = currentAspectRatio.toFixed(3);
        }

        if (isInitialFileLoad || !svgWidthInput.value || !svgHeightInput.value) {
          if (svgWidthInput) svgWidthInput.value = parseFloat((res.data.target_dimensions?.width || res.data.bounding_box.width).toFixed(2));
          if (svgHeightInput) svgHeightInput.value = parseFloat((res.data.target_dimensions?.height || res.data.bounding_box.height).toFixed(2));
        }
      }

      spanBbox.textContent = `${parsedSvgData.bounding_box.width} x ${parsedSvgData.bounding_box.height} mm (X: ${parsedSvgData.bounding_box.min_x}..${parsedSvgData.bounding_box.max_x}, Y: ${parsedSvgData.bounding_box.min_y}..${parsedSvgData.bounding_box.max_y})`;
      spanEntities.textContent = parsedSvgData.entity_count;
      spanChainCount.textContent = parsedSvgData.chains.length;
      spanCircleCount.textContent = parsedSvgData.circles.length;

      statEntities.textContent = parsedSvgData.entity_count;
      statChains.textContent = parsedSvgData.chains.length + parsedSvgData.circles.length;

      // Populate Depth Table
      renderDepthTable(parsedSvgData);

      // Auto-trigger toolpath preview
      await generateToolpath();
    } catch (err) {
      alert("Failed to parse SVG: " + err.message);
    } finally {
      parseSvgBtn.disabled = false;
      parseSvgBtn.textContent = "🔍 Parse SVG Geometry";
    }
  }

  function renderDepthTable(data) {
    depthTableBody.innerHTML = "";
    const items = [...data.chains, ...data.circles];
    if (items.length === 0) {
      depthTableBody.innerHTML = '<tr><td colspan="4" style="padding: 0.5rem; text-align: center; color: var(--text-muted);">No vector elements detected</td></tr>';
      return;
    }

    items.forEach((item, idx) => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
      
      const tagLabel = item.tag ? item.tag.toUpperCase() : "HOLE (CIRCLE)";
      const colorHex = item.fill || "#000000";
      const shadingPct = item.shading_percent !== undefined ? `${item.shading_percent}%` : "100%";
      const depthZ = item.target_depth_z !== undefined ? `${item.target_depth_z} mm` : "0.00 mm";

      tr.innerHTML = `
        <td style="padding: 0.25rem;">${tagLabel} #${idx + 1}</td>
        <td style="padding: 0.25rem; display: flex; align-items: center; gap: 0.35rem;">
          <span style="display: inline-block; width: 12px; height: 12px; border-radius: 2px; background: ${colorHex}; border: 1px solid #64748b;"></span>
          <span>${colorHex}</span>
        </td>
        <td style="padding: 0.25rem;">${shadingPct}</td>
        <td style="padding: 0.25rem; font-weight: 600; color: #38bdf8;">${depthZ}</td>
      `;
      depthTableBody.appendChild(tr);
    });
  }

  async function generateToolpath() {
    if (!parsedSvgData) {
      alert("Please parse an SVG drawing first.");
      return;
    }

    const tId = parseInt(toolSelect.value, 10);
    const selTool = toolsList.find((t) => t.id === tId) || null;

    const payload = {
      chains: parsedSvgData.chains,
      circles: parsedSvgData.circles,
      operation_type: opTypeSelect.value,
      side: sideSelect.value,
      target_depth_z: null, // Allow individual grayscale depths
      stepdown_z: parseFloat(stepdownInput.value) || 1.5,
      finish_allowance: 0.0,
      spring_pass: false,
      lead_in_type: leadInTypeSelect.value,
      use_grayscale_depths: useGrayscaleDepthsInput.checked,
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
      generateSvgBtn.disabled = true;
      generateSvgBtn.textContent = "⏳ Generating Toolpath...";

      const res = await API.generateSVGToolpath(payload);
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
      alert("Failed to generate SVG G-code: " + err.message);
    } finally {
      generateSvgBtn.disabled = false;
      generateSvgBtn.textContent = "⚡ Generate SVG G-Code & Preview";
    }
  }

  generateSvgBtn.addEventListener("click", generateToolpath);

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
    a.download = `svg_${opTypeSelect.value}_program.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Queue Operation to Multi-Op Job Builder
  queueOpBtn.addEventListener("click", () => {
    if (!currentGeneratedGCode) {
      alert("Please generate SVG G-Code first before queueing.");
      return;
    }

    const tId = parseInt(toolSelect.value, 10);
    const selTool = toolsList.find((t) => t.id === tId) || null;

    if (window.JobBuilder) {
      window.JobBuilder.addOperation({
        id: "op_" + Date.now(),
        name: `SVG ${opTypeSelect.value.toUpperCase()} (Ø${toolDiameterInput.value}mm)`,
        op_type: "contouring",
        tool_number: selTool ? selTool.tool_number : 1,
        tool_name: selTool ? selTool.name : "Endmill",
        tool_diameter: parseFloat(toolDiameterInput.value) || 3.175,
        spindle_speed: parseInt(spindleRpmInput.value, 10) || 16000,
        feed_rate_xy: parseFloat(feedRateXyInput.value) || 800.0,
        plunge_feed: parseFloat(plungeFeedInput.value) || 250.0,
        target_depth_z: parseFloat(maxCutDepthInput.value) || -6.0,
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
  updateDepthLegend();
  await initData();
});
