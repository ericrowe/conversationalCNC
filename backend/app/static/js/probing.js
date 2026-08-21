document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("probingModal");
  const openBtn = document.getElementById("openProbingModalBtn");
  const closeBtn = document.getElementById("closeProbingModalBtn");

  if (!modal || !openBtn) return;

  const tabs = modal.querySelectorAll(".pattern-tab");
  const panes = modal.querySelectorAll(".ptab-pane");

  // Z-Probe Elements
  const zProbeThickness = document.getElementById("zProbeThickness");
  const zProbeRetract = document.getElementById("zProbeRetract");
  const zProbeFastFeed = document.getElementById("zProbeFastFeed");
  const zProbeSlowFeed = document.getElementById("zProbeSlowFeed");
  const btnGenZProbe = document.getElementById("btnGenZProbe");

  // Corner XYZ Elements
  const cornerToolDia = document.getElementById("cornerToolDia");
  const cornerPlateZ = document.getElementById("cornerPlateZ");
  const cornerLipX = document.getElementById("cornerLipX");
  const cornerLipY = document.getElementById("cornerLipY");
  const btnGenCornerProbe = document.getElementById("btnGenCornerProbe");

  // Homing Elements
  const btnGenHoming = document.getElementById("btnGenHoming");

  // Surface Mesh Elements
  const meshShapeSelect = document.getElementById("meshShapeSelect");
  const meshInsetMargin = document.getElementById("meshInsetMargin");
  const meshRectFields = document.getElementById("meshRectFields");
  const meshCircleFields = document.getElementById("meshCircleFields");
  const meshInnerDiaGroup = document.getElementById("meshInnerDiaGroup");

  const meshXMin = document.getElementById("meshXMin");
  const meshXMax = document.getElementById("meshXMax");
  const meshGridX = document.getElementById("meshGridX");
  const meshYMin = document.getElementById("meshYMin");
  const meshYMax = document.getElementById("meshYMax");
  const meshGridY = document.getElementById("meshGridY");

  const meshCenterX = document.getElementById("meshCenterX");
  const meshCenterY = document.getElementById("meshCenterY");
  const meshOuterDia = document.getElementById("meshOuterDia");
  const meshInnerDia = document.getElementById("meshInnerDia");
  const meshGridRes = document.getElementById("meshGridRes");

  const meshCanvas = document.getElementById("meshCanvas");
  const meshPointCounterBadge = document.getElementById("meshPointCounterBadge");

  const meshFastFeed = document.getElementById("meshFastFeed");
  const meshSlowFeed = document.getElementById("meshSlowFeed");
  const meshSafeTraverseZ = document.getElementById("meshSafeTraverseZ");

  const btnGenMeshProbe = document.getElementById("btnGenMeshProbe");
  const btnToggleMeshLog = document.getElementById("btnToggleMeshLog");
  const btnLoadSampleBowedMesh = document.getElementById("btnLoadSampleBowedMesh");
  const btnSaveActiveJobMesh = document.getElementById("btnSaveActiveJobMesh");

  const meshLogContainer = document.getElementById("meshLogContainer");
  const meshLogInput = document.getElementById("meshLogInput");
  const btnParseMeshLog = document.getElementById("btnParseMeshLog");

  const macroOutput = document.getElementById("probeMacroOutput");
  const copyBtn = document.getElementById("copyProbeMacroBtn");
  const downloadBtn = document.getElementById("downloadProbeMacroBtn");

  let currentMacroGCode = "";
  let currentMacroFilename = "z_probe_macro.nc";

  // Mesh State
  let currentMeshPoints = [];
  let currentMeshTriangles = [];
  let meshDebounceTimer = null;

  // Tab switching
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.ptab;

      panes.forEach((p) => (p.style.display = "none"));
      if (target === "zprobe") document.getElementById("ptabContentZProbe").style.display = "block";
      else if (target === "corner") document.getElementById("ptabContentCorner").style.display = "block";
      else if (target === "mesh") {
        document.getElementById("ptabContentMesh").style.display = "block";
        refreshMeshCandidatePoints();
      }
      else if (target === "homing") document.getElementById("ptabContentHoming").style.display = "block";
    });
  });

  async function syncWithActiveMachine() {
    try {
      const activeRes = await API.getActiveMachine();
      const machine = activeRes && activeRes.machine ? activeRes.machine : activeRes;
      if (machine) {
        if (machine.z_probe_thickness !== undefined && machine.z_probe_thickness !== null) {
          zProbeThickness.value = machine.z_probe_thickness;
          cornerPlateZ.value = machine.z_probe_thickness;
        }
        if (machine.safe_z_retract !== undefined && machine.safe_z_retract !== null) {
          zProbeRetract.value = machine.safe_z_retract;
          if (meshSafeTraverseZ) meshSafeTraverseZ.value = machine.safe_z_retract;
        }
      }
    } catch (e) {
      console.warn("Could not fetch active machine probe thickness", e);
    }
  }

  // Initial sync on page load
  syncWithActiveMachine();

  // Modal open/close
  openBtn.addEventListener("click", async () => {
    modal.style.display = "flex";
    await syncWithActiveMachine();
    if (document.querySelector('.pattern-tab[data-ptab="mesh"]').classList.contains("active")) {
      refreshMeshCandidatePoints();
    }
  });

  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });

  function setMacroResult(gcode, filename) {
    currentMacroGCode = gcode;
    currentMacroFilename = filename;
    macroOutput.value = gcode;
  }

  // 1. Z-Probe
  btnGenZProbe.addEventListener("click", async () => {
    try {
      const res = await API.generateZProbeMacro({
        plate_thickness: parseFloat(zProbeThickness.value) || 14.85,
        retract_height: parseFloat(zProbeRetract.value) || 20.0,
        fast_feed: parseFloat(zProbeFastFeed.value) || 150.0,
        slow_feed: parseFloat(zProbeSlowFeed.value) || 25.0,
      });
      setMacroResult(res.data.gcode, "z_probe_macro.nc");
    } catch (err) {
      alert("Z-Probe generation failed: " + err.message);
    }
  });

  // 2. Corner XYZ Probe
  btnGenCornerProbe.addEventListener("click", async () => {
    try {
      const res = await API.generateCornerXYZMacro({
        tool_diameter: parseFloat(cornerToolDia.value) || 6.35,
        plate_thickness: parseFloat(cornerPlateZ.value) || 14.85,
        block_x_lip: parseFloat(cornerLipX.value) || 10.0,
        block_y_lip: parseFloat(cornerLipY.value) || 10.0,
      });
      setMacroResult(res.data.gcode, "corner_xyz_probe.nc");
    } catch (err) {
      alert("Corner probe generation failed: " + err.message);
    }
  });

  // 3. Homing
  btnGenHoming.addEventListener("click", async () => {
    try {
      const res = await API.generateHomingMacro();
      setMacroResult(res.data.gcode, "homing_cycle.nc");
    } catch (err) {
      alert("Homing macro generation failed: " + err.message);
    }
  });

  // =========================================================================
  // 4. Surface Mesh Leveling & Interactive Canvas
  // =========================================================================

  function updateShapeFormVisibility() {
    const shape = meshShapeSelect.value;
    if (shape === "rectangle") {
      meshRectFields.style.display = "block";
      meshCircleFields.style.display = "none";
      meshInnerDiaGroup.style.display = "none";
    } else if (shape === "circle") {
      meshRectFields.style.display = "none";
      meshCircleFields.style.display = "block";
      meshInnerDiaGroup.style.display = "none";
    } else if (shape === "donut") {
      meshRectFields.style.display = "none";
      meshCircleFields.style.display = "block";
      meshInnerDiaGroup.style.display = "block";
    }
  }

  if (meshShapeSelect) {
    meshShapeSelect.addEventListener("change", () => {
      updateShapeFormVisibility();
      refreshMeshCandidatePoints();
    });
  }

  const meshInputs = [
    meshInsetMargin, meshXMin, meshXMax, meshGridX, meshYMin, meshYMax, meshGridY,
    meshCenterX, meshCenterY, meshOuterDia, meshInnerDia, meshGridRes
  ];

  meshInputs.forEach((input) => {
    if (input) {
      input.addEventListener("input", () => {
        clearTimeout(meshDebounceTimer);
        meshDebounceTimer = setTimeout(refreshMeshCandidatePoints, 250);
      });
    }
  });

  async function refreshMeshCandidatePoints() {
    if (!meshCanvas) return;
    const shape = meshShapeSelect.value;
    const margin = parseFloat(meshInsetMargin.value) || 0.0;

    const payload = {
      shape_type: shape,
      margin: margin,
      x_min: parseFloat(meshXMin.value) || 0.0,
      x_max: parseFloat(meshXMax.value) || 100.0,
      y_min: parseFloat(meshYMin.value) || 0.0,
      y_max: parseFloat(meshYMax.value) || 100.0,
      grid_x: parseInt(meshGridX.value, 10) || 5,
      grid_y: parseInt(meshGridY.value, 10) || 5,
      center_x: parseFloat(meshCenterX.value) || 50.0,
      center_y: parseFloat(meshCenterY.value) || 50.0,
      radius: (parseFloat(meshOuterDia.value) || 100.0) / 2.0,
      inner_radius: shape === "donut" ? ((parseFloat(meshInnerDia.value) || 30.0) / 2.0) : 0.0,
      grid_resolution: parseInt(meshGridRes.value, 10) || 5,
    };

    try {
      const res = await API.generateMeshPoints(payload);
      if (res && res.data) {
        // Retain previous active/excluded state if points match ID/pos
        const oldActiveMap = new Map();
        currentMeshPoints.forEach(p => oldActiveMap.set(`${p.x.toFixed(2)},${p.y.toFixed(2)}`, p.active));

        currentMeshPoints = res.data.points.map(p => {
          const key = `${p.x.toFixed(2)},${p.y.toFixed(2)}`;
          if (oldActiveMap.has(key)) {
            p.active = oldActiveMap.get(key);
          }
          return p;
        });

        currentMeshTriangles = res.data.triangles || [];
        drawMeshCanvas();
      }
    } catch (e) {
      console.warn("Could not calculate mesh points", e);
    }
  }

  function drawMeshCanvas() {
    if (!meshCanvas) return;
    const ctx = meshCanvas.getContext("2d");
    const width = meshCanvas.width;
    const height = meshCanvas.height;
    ctx.clearRect(0, 0, width, height);

    if (currentMeshPoints.length === 0) return;

    // Calculate bounding box
    const xs = currentMeshPoints.map(p => p.x);
    const ys = currentMeshPoints.map(p => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const spanX = Math.max(1.0, maxX - minX);
    const spanY = Math.max(1.0, maxY - minY);
    const pad = 24;

    const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
    const offsetX = (width - spanX * scale) / 2 - minX * scale;
    const offsetY = (height - spanY * scale) / 2 + maxY * scale;

    function toScreen(x, y) {
      return {
        sx: x * scale + offsetX,
        sy: offsetY - y * scale,
      };
    }

    // 1. Draw boundary outline
    const shape = meshShapeSelect.value;
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1.5;

    if (shape === "rectangle") {
      const p1 = toScreen(parseFloat(meshXMin.value), parseFloat(meshYMin.value));
      const p2 = toScreen(parseFloat(meshXMax.value), parseFloat(meshYMax.value));
      ctx.strokeRect(p1.sx, p2.sy, (p2.sx - p1.sx), (p1.sy - p2.sy));
    } else if (shape === "circle" || shape === "donut") {
      const cx = parseFloat(meshCenterX.value);
      const cy = parseFloat(meshCenterY.value);
      const r = (parseFloat(meshOuterDia.value) || 100.0) / 2.0;
      const centerScreen = toScreen(cx, cy);
      ctx.beginPath();
      ctx.arc(centerScreen.sx, centerScreen.sy, r * scale, 0, 2 * Math.PI);
      ctx.stroke();

      if (shape === "donut") {
        const inR = (parseFloat(meshInnerDia.value) || 30.0) / 2.0;
        ctx.beginPath();
        ctx.arc(centerScreen.sx, centerScreen.sy, inR * scale, 0, 2 * Math.PI);
        ctx.stroke();
      }
    }

    // 2. Draw triangulation wireframe
    ctx.strokeStyle = "rgba(56, 189, 248, 0.15)";
    ctx.lineWidth = 1.0;
    currentMeshTriangles.forEach(tri => {
      const p1 = currentMeshPoints[tri[0]];
      const p2 = currentMeshPoints[tri[1]];
      const p3 = currentMeshPoints[tri[2]];
      if (p1 && p2 && p3) {
        const s1 = toScreen(p1.x, p1.y);
        const s2 = toScreen(p2.x, p2.y);
        const s3 = toScreen(p3.x, p3.y);
        ctx.beginPath();
        ctx.moveTo(s1.sx, s1.sy);
        ctx.lineTo(s2.sx, s2.sy);
        ctx.lineTo(s3.sx, s3.sy);
        ctx.closePath();
        ctx.stroke();
      }
    });

    // 3. Draw probe point nodes
    let activeCount = 0;
    currentMeshPoints.forEach(p => {
      const s = toScreen(p.x, p.y);
      p._screenX = s.sx;
      p._screenY = s.sy;

      ctx.beginPath();
      ctx.arc(s.sx, s.sy, 5.0, 0, 2 * Math.PI);

      if (p.active !== false) {
        activeCount++;
        ctx.fillStyle = "#10b981"; // Active Green
        ctx.strokeStyle = "#047857";
      } else {
        ctx.fillStyle = "#ef4444"; // Excluded Red
        ctx.strokeStyle = "#b91c1c";
      }
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
    });

    // Update Counter Badge
    if (meshPointCounterBadge) {
      const excluded = currentMeshPoints.length - activeCount;
      meshPointCounterBadge.textContent = `${activeCount} / ${currentMeshPoints.length} Points Active ${excluded > 0 ? `(${excluded} Excluded)` : ""}`;
    }
  }

  // Click on canvas to toggle active/excluded state of points
  if (meshCanvas) {
    meshCanvas.addEventListener("click", (e) => {
      const rect = meshCanvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      let closest = null;
      let minDist = 18.0; // Click radius

      currentMeshPoints.forEach(p => {
        if (p._screenX !== undefined && p._screenY !== undefined) {
          const d = Math.hypot(clickX - p._screenX, clickY - p._screenY);
          if (d < minDist) {
            minDist = d;
            closest = p;
          }
        }
      });

      if (closest) {
        closest.active = closest.active === false ? true : false;
        drawMeshCanvas();
      }
    });
  }

  // Generate Mesh Probe Macro
  if (btnGenMeshProbe) {
    btnGenMeshProbe.addEventListener("click", async () => {
      try {
        const activePts = currentMeshPoints.filter(p => p.active !== false);
        if (activePts.length === 0) {
          alert("Please select at least 1 active probe point.");
          return;
        }

        const res = await API.generateMeshProbeMacro({
          points: currentMeshPoints,
          shape_type: meshShapeSelect.value,
          search_dist: 20.0,
          fast_feed: parseFloat(meshFastFeed.value) || 150.0,
          slow_feed: parseFloat(meshSlowFeed.value) || 25.0,
          safe_traverse_z: parseFloat(meshSafeTraverseZ.value) || 5.0,
          units: "mm",
        });

        setMacroResult(res.data.gcode, `mesh_probe_${meshShapeSelect.value}_${activePts.length}pts.nc`);
      } catch (e) {
        alert("Mesh probe generation failed: " + e.message);
      }
    });
  }

  // Toggle Log Container
  if (btnToggleMeshLog) {
    btnToggleMeshLog.addEventListener("click", () => {
      meshLogContainer.style.display = meshLogContainer.style.display === "none" ? "block" : "none";
    });
  }

  // Load Test Bowed Mesh (+0.35mm crown)
  if (btnLoadSampleBowedMesh) {
    btnLoadSampleBowedMesh.addEventListener("click", () => {
      if (currentMeshPoints.length === 0) return;

      const xs = currentMeshPoints.map(p => p.x);
      const ys = currentMeshPoints.map(p => p.y);
      const midX = (Math.min(...xs) + Math.max(...xs)) / 2.0;
      const midY = (Math.min(...ys) + Math.max(...ys)) / 2.0;
      const maxDist = Math.max(1.0, Math.hypot(Math.max(...xs) - midX, Math.max(...ys) - midY));

      currentMeshPoints.forEach(p => {
        const d = Math.hypot(p.x - midX, p.y - midY);
        // Quadratic dome bow (+0.35mm in center tapering to 0.0mm at corners)
        p.z = Math.round((0.35 * Math.max(0.0, 1.0 - (d / maxDist) ** 2)) * 1000) / 1000;
      });

      // Save to localStorage
      saveActiveSessionMesh();
      alert("🧪 Test Bowed Workpiece Mesh (+0.35mm crown) loaded and saved to active session!");
    });
  }

  // Parse Probe Log
  if (btnParseMeshLog) {
    btnParseMeshLog.addEventListener("click", async () => {
      const text = meshLogInput.value.trim();
      if (!text) {
        alert("Please paste sender probe console output.");
        return;
      }

      try {
        const res = await API.parseMeshProbeLog({
          log_text: text,
          points_template: currentMeshPoints,
        });

        if (res && res.data && res.data.points) {
          currentMeshPoints = res.data.points;
          saveActiveSessionMesh();
          alert(`✅ Successfully parsed ${res.data.active_point_count} probe points! (Z span: ${res.data.z_min}mm to ${res.data.z_max}mm)`);
          meshLogContainer.style.display = "none";
        }
      } catch (e) {
        alert("Failed to parse probe log: " + e.message);
      }
    });
  }

  function saveActiveSessionMesh() {
    const meshMapData = {
      shape_type: meshShapeSelect.value,
      points: currentMeshPoints,
      active_point_count: currentMeshPoints.filter(p => p.active !== false).length,
      updated_at: new Date().toISOString(),
    };
    localStorage.setItem("conversational_cnc_active_mesh", JSON.stringify(meshMapData));
    window.dispatchEvent(new CustomEvent("mesh-updated", { detail: meshMapData }));
  }

  if (btnSaveActiveJobMesh) {
    btnSaveActiveJobMesh.addEventListener("click", () => {
      saveActiveSessionMesh();
      const activePts = currentMeshPoints.filter(p => p.active !== false).length;
      alert(`💾 Active Workpiece Mesh (${meshShapeSelect.value.toUpperCase()}, ${activePts} points) saved! It will now auto-level Job Builder operations.`);
    });
  }

  // Copy & Download
  copyBtn.addEventListener("click", () => {
    if (!currentMacroGCode) return;
    navigator.clipboard.writeText(currentMacroGCode).then(() => {
      const orig = copyBtn.textContent;
      copyBtn.textContent = "✅ Copied!";
      setTimeout(() => (copyBtn.textContent = orig), 2000);
    });
  });

  downloadBtn.addEventListener("click", () => {
    if (!currentMacroGCode) return;
    const blob = new Blob([currentMacroGCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = currentMacroFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
});
