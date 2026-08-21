/**
 * 2D / 3D Interactive Toolpath Visualizer & Simulation Engine (Phase 4 Upgrade)
 * Supports 3D Isometric Orbit, 2D Plan View, Step-by-Step Playback, Animated Cutter Tool, and Bi-Directional Sync.
 */
class ToolpathVisualizer {
  constructor(canvasOrId) {
    this.canvas = typeof canvasOrId === "string" ? document.getElementById(canvasOrId) : canvasOrId;
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");


    this.opType = "drilling";
    this.holes = [];
    this.machineEnvelope = { x: 750, y: 750 };
    this.toolDiameter = 3.175;

    // Operation specific params
    this.pocketDiameter = 20.0;
    this.threadNominalDia = 6.0;
    this.threadPitch = 1.0;
    this.threadType = "internal";
    this.surfacing = null;
    this.rectangularPocket = null;
    this.rectangularBoss = null;
    this.surfaceMesh = null;

    // 3D Viewport State
    this.viewMode = "3d"; // "3d" or "2d"
    this.rotX = 35.0;     // Elevation / Tilt angle above horizontal ground plane (0 = front, 90 = top)
    this.rotZ = -45.0;    // Azimuth / Yaw orbit angle around vertical Z axis (degrees)
    this.scale = 1.2;
    this.offsetX = 200;
    this.offsetY = 240;

    // Mouse Interaction
    this.isDragging = false;
    this.isPanning = false;
    this.lastMouse = { x: 0, y: 0 };

    // G-Code & Simulation State
    this.gcodeToolpath = null;
    this.simPlaying = false;
    this.simIndex = 0;
    this.simSpeed = 1.0;
    this.simTimer = null;
    this.highlightedLine = -1;
    this.toolPosition = { x: 0, y: 0, z: 5.0 };

    // Callback when segment or line is selected
    this.onSegmentSelected = null;

    this.resizeCanvas();
    window.addEventListener("resize", () => this.resizeCanvas());
    this.bindEvents();
    this.bindToolbarControls();
    this.draw();
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width || 600;
    this.canvas.height = 380;
    this.draw();
  }

  bindEvents() {
    this.canvas.addEventListener("mousedown", (e) => {
      if (e.button === 2 || e.shiftKey) {
        this.isPanning = true;
      } else {
        this.isDragging = true;
      }
      this.lastMouse = { x: e.clientX, y: e.clientY };
    });

    this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());

    window.addEventListener("mousemove", (e) => {
      if (!this.isDragging && !this.isPanning) return;
      const dx = e.clientX - this.lastMouse.x;
      const dy = e.clientY - this.lastMouse.y;

      if (this.isPanning || this.viewMode === "2d") {
        this.offsetX += dx;
        this.offsetY += dy;
      } else if (this.isDragging && this.viewMode === "3d") {
        this.rotZ += dx * 0.5;
        this.rotX = Math.max(0, Math.min(90, this.rotX - dy * 0.5));
      }

      this.lastMouse = { x: e.clientX, y: e.clientY };
      this.draw();
    });

    window.addEventListener("mouseup", () => {
      this.isDragging = false;
      this.isPanning = false;
    });

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      this.zoom(zoomFactor, e.offsetX, e.offsetY);
    });
  }

  bindToolbarControls() {
    const btnToggle3D = document.getElementById("btnToggle3D");
    const btnIso = document.getElementById("btnIsoView");
    const btnTop = document.getElementById("btnTopView");
    const btnFront = document.getElementById("btnFrontView");

    const btnPlay = document.getElementById("btnSimPlay");
    const btnStepBack = document.getElementById("btnSimStepBack");
    const btnStepFwd = document.getElementById("btnSimStepFwd");
    const scrubber = document.getElementById("simScrubber");
    const speedSelect = document.getElementById("simSpeedSelect");

    if (btnToggle3D) {
      btnToggle3D.addEventListener("click", () => {
        this.viewMode = this.viewMode === "3d" ? "2d" : "3d";
        btnToggle3D.textContent = this.viewMode === "3d" ? "🧊 3D View" : "📐 2D View";
        btnToggle3D.classList.toggle("active", this.viewMode === "3d");
        this.autoFit();
      });
    }

    if (btnIso) btnIso.addEventListener("click", () => this.setCameraView("iso"));
    if (btnTop) btnTop.addEventListener("click", () => this.setCameraView("top"));
    if (btnFront) btnFront.addEventListener("click", () => this.setCameraView("front"));

    if (btnPlay) {
      btnPlay.addEventListener("click", () => {
        if (this.simPlaying) {
          this.pauseSimulation();
          btnPlay.textContent = "▶ Play";
        } else {
          this.playSimulation();
          btnPlay.textContent = "⏸ Pause";
        }
      });
    }

    if (btnStepBack) btnStepBack.addEventListener("click", () => this.stepBackward());
    if (btnStepFwd) btnStepFwd.addEventListener("click", () => this.stepForward());

    if (scrubber) {
      scrubber.addEventListener("input", () => {
        this.seekSimulation(parseInt(scrubber.value, 10));
      });
    }

    if (speedSelect) {
      speedSelect.addEventListener("change", () => {
        this.simSpeed = parseFloat(speedSelect.value) || 1.0;
      });
    }
  }

  setCameraView(preset) {
    if (preset === "iso") {
      this.viewMode = "3d";
      this.rotX = 35.0;
      this.rotZ = -45.0;
    } else if (preset === "top") {
      this.viewMode = "2d";
      this.rotX = 90.0;
      this.rotZ = 0.0;
    } else if (preset === "front") {
      this.viewMode = "3d";
      this.rotX = 0.0;
      this.rotZ = 0.0;
    } else if (preset === "right") {
      this.viewMode = "3d";
      this.rotX = 0.0;
      this.rotZ = -90.0;
    }
    this.autoFit();
  }

  zoom(factor, centerX = this.canvas.width / 2, centerY = this.canvas.height / 2) {
    const newScale = Math.max(0.05, Math.min(25.0, this.scale * factor));
    this.offsetX = centerX - (centerX - this.offsetX) * (newScale / this.scale);
    this.offsetY = centerY - (centerY - this.offsetY) * (newScale / this.scale);
    this.scale = newScale;
    this.draw();
  }

  toScreen(x, y, z = 0.0) {
    if (this.viewMode === "3d") {
      const radX = (this.rotX * Math.PI) / 180.0; // Elevation angle above horizontal (0 = front, 90 = top)
      const radZ = (this.rotZ * Math.PI) / 180.0; // Azimuth angle around vertical Z

      // Step 1: Rotate (X, Y) around vertical Z axis by azimuth angle radZ
      const cosZ = Math.cos(radZ);
      const sinZ = Math.sin(radZ);
      const x1 = x * cosZ - y * sinZ; // Screen horizontal component
      const y1 = x * sinZ + y * cosZ; // Depth along ground plane into screen
      const z1 = z;                   // Vertical height (CNC +Z is UP)

      // Step 2: Project along elevation angle radX (tilt above horizon)
      const cosX = Math.cos(radX);
      const sinX = Math.sin(radX);

      // Screen X
      const sx = this.offsetX + x1 * this.scale;

      // Screen Y:
      // - Higher vertical height (+Z) moves UP on screen (decreases canvas Y) -> - z1 * cosX
      // - Further depth along ground (+Y1) moves UP on screen (decreases canvas Y) -> - y1 * sinX
      const sy = this.offsetY - (y1 * sinX + z1 * cosX) * this.scale;

      // Depth for z-sorting / distance
      const depth = y1 * cosX - z1 * sinX;

      return { x: sx, y: sy, depth: depth };
    } else {
      return {
        x: this.offsetX + x * this.scale,
        y: this.offsetY - y * this.scale,
        depth: 0,
      };
    }
  }


  setData(data = {}) {
    if (Array.isArray(data)) {
      this.holes = data;
    } else {
      this.opType = data.opType || this.opType || "drilling";
      this.holes = data.holes || data.pockets || [];
      if (data.machineEnvelope) this.machineEnvelope = data.machineEnvelope;
      if (data.toolDiameter !== undefined) this.toolDiameter = data.toolDiameter;
      if (data.pocketDiameter !== undefined) this.pocketDiameter = data.pocketDiameter;
      if (data.threadNominalDia !== undefined) this.threadNominalDia = data.threadNominalDia;
      if (data.threadPitch !== undefined) this.threadPitch = data.threadPitch;
      if (data.surfacing !== undefined) this.surfacing = data.surfacing;
      if (data.engraving !== undefined) this.engraving = data.engraving;
      if (data.rectangularPocket !== undefined) this.rectangularPocket = data.rectangularPocket;
      if (data.rectangularBoss !== undefined) this.rectangularBoss = data.rectangularBoss;
    }
    this.autoFit();
  }

  autoFit() {
    if (!this.canvas) return;
    const padding = 70;
    let allX = [0];
    let allY = [0];

    if (this.gcodeToolpath && this.gcodeToolpath.length > 0) {
      for (let seg of this.gcodeToolpath) {
        allX.push(seg.x1, seg.x2);
        allY.push(seg.y1, seg.y2);
      }
    } else if (this.opType === "surfacing" && this.surfacing) {
      const s = this.surfacing;
      if (s.originMode === "center") {
        allX.push(s.originX - s.lengthX / 2, s.originX + s.lengthX / 2);
        allY.push(s.originY - s.widthY / 2, s.originY + s.widthY / 2);
      } else {
        allX.push(s.originX, s.originX + s.lengthX);
        allY.push(s.originY, s.originY + s.widthY);
      }
    }
    else if (this.opType === "engraving" && this.engraving) {
      const e = this.engraving;
      const polys = this.computeEngravingPolylines(e);
      if (polys && polys.length > 0) {
        for (let poly of polys) {
          for (let pt of poly) {
            allX.push(pt[0]);
            allY.push(pt[1]);
          }
        }
      } else if (e.layoutMode === "arc") {
        allX.push(e.centerX - e.arcRadius - 10, e.centerX + e.arcRadius + 10);
        allY.push(e.centerY - e.arcRadius - 10, e.centerY + e.arcRadius + 10);
      } else {
        allX.push(e.startX - 10, e.startX + (e.textLength || 50) + 10);
        allY.push(e.startY - 10, e.startY + (e.fontSize || 10) + 10);
      }
    } else if (this.opType === "rectangular_pocket" && this.rectangularPocket) {
      const p = this.rectangularPocket;
      const minX = p.originMode === "center" ? p.originX - p.lengthX / 2 : p.originX;
      const maxX = p.originMode === "center" ? p.originX + p.lengthX / 2 : p.originX + p.lengthX;
      const minY = p.originMode === "center" ? p.originY - p.widthY / 2 : p.originY;
      const maxY = p.originMode === "center" ? p.originY + p.widthY / 2 : p.originY + p.widthY;
      allX.push(minX - 5, maxX + 5);
      allY.push(minY - 5, maxY + 5);
    } else if (this.opType === "rectangular_boss" && this.rectangularBoss) {
      const b = this.rectangularBoss;
      allX.push(b.bossOriginX - b.stockLengthX / 2 - 5, b.bossOriginX + b.stockLengthX / 2 + 5);
      allY.push(b.bossOriginY - b.stockWidthY / 2 - 5, b.bossOriginY + b.stockWidthY / 2 + 5);
    } else if (this.holes.length > 0) {
      allX.push(...this.holes.map((h) => h[0]));
      allY.push(...this.holes.map((h) => h[1]));
    }

    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);
    const minY = Math.min(...allY);
    const maxY = Math.max(...allY);

    const spanX = Math.max(maxX - minX, 40);
    const spanY = Math.max(maxY - minY, 40);

    const scaleX = (this.canvas.width - padding * 2) / spanX;
    const scaleY = (this.canvas.height - padding * 2) / spanY;
    this.scale = Math.min(scaleX, scaleY, 2.5);

    if (this.viewMode === "3d") {
      const centerX = (minX + maxX) / 2.0;
      const centerY = (minY + maxY) / 2.0;
      const radX = (this.rotX * Math.PI) / 180.0;
      const radZ = (this.rotZ * Math.PI) / 180.0;
      const x1 = centerX * Math.cos(radZ) - centerY * Math.sin(radZ);
      const y1 = centerX * Math.sin(radZ) + centerY * Math.cos(radZ);
      const projY = y1 * Math.sin(radX);

      this.offsetX = this.canvas.width / 2.0 - x1 * this.scale;
      this.offsetY = this.canvas.height / 2.0 + projY * this.scale;
    } else {
      this.offsetX = padding - minX * this.scale;
      this.offsetY = this.canvas.height - padding + minY * this.scale;
    }

    this.draw();
  }

  loadSurfaceMesh(meshData) {
    this.surfaceMesh = meshData;
    this.draw();
  }

  clearSurfaceMesh() {
    this.surfaceMesh = null;
    this.draw();
  }

  draw() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Background & Grid
    this.drawGrid(ctx);

    // 3D Triad Axes
    this.drawAxes(ctx);

    // Machine Soft Limits Envelope Box
    if (this.machineEnvelope) {
      this.drawEnvelopeBox(ctx);
    }

    // Topographic Workpiece Surface Mesh (if active)
    if (this.surfaceMesh) {
      this.drawSurfaceMesh(ctx);
    }

    // Operation-specific Rendering (or parsed G-Code toolpath)
    if (this.gcodeToolpath && this.gcodeToolpath.length > 0) {
      this.drawGCodeToolpath(ctx);
    } else if (this.opType === "surfacing" && this.surfacing) {
      this.drawSurfacing(ctx);
    } else if (this.opType === "rectangular_pocket" && this.rectangularPocket) {
      this.drawRectangularPocket(ctx);
    } else if (this.opType === "rectangular_boss" && this.rectangularBoss) {
      this.drawRectangularBoss(ctx);
    } else if (this.opType === "pocket") {
      this.drawPockets(ctx);
    } else if (this.opType === "thread_milling") {
      this.drawThreadMilling(ctx);
    } else if (this.opType === "engraving" && this.engraving) {
      this.drawEngraving(ctx);
    } else {
      this.drawDrillHoles(ctx);
    }

    // Simulated 3D Cutter Tool
    if (this.gcodeToolpath && this.gcodeToolpath.length > 0) {
      this.drawSimulatedTool(ctx);
    }

    // View mode badge
    ctx.fillStyle = "rgba(148, 163, 184, 0.7)";
    ctx.font = "10px sans-serif";
    ctx.fillText(this.viewMode === "3d" ? "3D Isometric View (Drag to Orbit | Shift-Drag to Pan)" : "2D Plan View (Drag to Pan)", 10, this.canvas.height - 10);
  }

  drawAxes(ctx) {
    const origin = this.toScreen(0, 0, 0);
    const axisLen = 35;

    const xEnd = this.toScreen(axisLen, 0, 0);
    const yEnd = this.toScreen(0, axisLen, 0);
    const zEnd = this.toScreen(0, 0, axisLen);

    // X Axis (Red)
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(xEnd.x, xEnd.y);
    ctx.stroke();
    ctx.fillStyle = "#ef4444";
    ctx.font = "bold 10px sans-serif";
    ctx.fillText("+X", xEnd.x + 4, xEnd.y + 3);

    // Y Axis (Green)
    ctx.strokeStyle = "#10b981";
    ctx.beginPath();
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(yEnd.x, yEnd.y);
    ctx.stroke();
    ctx.fillStyle = "#10b981";
    ctx.fillText("+Y", yEnd.x + 4, yEnd.y + 3);

    // Z Axis (Blue - visible in 3D mode, points UP)
    if (this.viewMode === "3d") {
      ctx.strokeStyle = "#38bdf8";
      ctx.beginPath();
      ctx.moveTo(origin.x, origin.y);
      ctx.lineTo(zEnd.x, zEnd.y);
      ctx.stroke();
      ctx.fillStyle = "#38bdf8";
      ctx.fillText("+Z", zEnd.x + 4, zEnd.y - 2);
    }


    // Prominent WCS (0,0,0) Part Datum Crosshair Target & Badge
    ctx.save();
    // Outer target ring
    ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(origin.x, origin.y, 8, 0, 2 * Math.PI);
    ctx.stroke();

    // Crosshair ticks
    ctx.beginPath();
    ctx.moveTo(origin.x - 12, origin.y);
    ctx.lineTo(origin.x + 12, origin.y);
    ctx.moveTo(origin.x, origin.y - 12);
    ctx.lineTo(origin.x, origin.y + 12);
    ctx.stroke();

    // Center glowing core
    ctx.beginPath();
    ctx.arc(origin.x, origin.y, 3.5, 0, 2 * Math.PI);
    ctx.fillStyle = "#38bdf8";
    ctx.shadowColor = "#38bdf8";
    ctx.shadowBlur = 6;
    ctx.fill();

    // Label badge
    ctx.shadowBlur = 0;
    ctx.fillStyle = "#94a3b8";
    ctx.font = "bold 9px sans-serif";
    ctx.fillText("WCS (0,0)", origin.x + 10, origin.y + 12);
    ctx.restore();
  }


  drawEnvelopeBox(ctx) {
    const ex = this.machineEnvelope.x;
    const ey = this.machineEnvelope.y;
    const ez = this.machineEnvelope.z || 65;

    ctx.strokeStyle = "rgba(239, 68, 68, 0.4)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    const p000 = this.toScreen(0, 0, 0);
    const p100 = this.toScreen(ex, 0, 0);
    const p110 = this.toScreen(ex, ey, 0);
    const p010 = this.toScreen(0, ey, 0);

    ctx.beginPath();
    ctx.moveTo(p000.x, p000.y);
    ctx.lineTo(p100.x, p100.y);
    ctx.lineTo(p110.x, p110.y);
    ctx.lineTo(p010.x, p010.y);
    ctx.closePath();
    ctx.stroke();

    if (this.viewMode === "3d") {
      const p001 = this.toScreen(0, 0, ez);
      const p101 = this.toScreen(ex, 0, ez);
      const p111 = this.toScreen(ex, ey, ez);
      const p011 = this.toScreen(0, ey, ez);

      ctx.beginPath();
      ctx.moveTo(p001.x, p001.y);
      ctx.lineTo(p101.x, p101.y);
      ctx.lineTo(p111.x, p111.y);
      ctx.lineTo(p011.x, p011.y);
      ctx.closePath();
      ctx.stroke();

      // Vertical edges
      ctx.beginPath();
      ctx.moveTo(p000.x, p000.y); ctx.lineTo(p001.x, p001.y);
      ctx.moveTo(p100.x, p100.y); ctx.lineTo(p101.x, p101.y);
      ctx.moveTo(p110.x, p110.y); ctx.lineTo(p111.x, p111.y);
      ctx.moveTo(p010.x, p010.y); ctx.lineTo(p011.x, p011.y);
      ctx.stroke();
    }

    ctx.setLineDash([]);
  }

  clearGCode() {
    this.gcodeToolpath = null;
    this.simIndex = 0;
    const scrubber = document.getElementById("simScrubber");
    if (scrubber) {
      scrubber.max = 0;
      scrubber.value = 0;
    }
  }

  loadGCode(gcodeText) {

    if (!gcodeText) return;
    this.gcodeToolpath = this.parseGCode(gcodeText);
    this.simIndex = 0;

    const scrubber = document.getElementById("simScrubber");
    if (scrubber) {
      scrubber.max = Math.max(0, this.gcodeToolpath.length - 1);
      scrubber.value = 0;
    }

    this.autoFit();
  }

  parseGCode(gcodeText) {
    const lines = gcodeText.split("\n");
    const segments = [];
    let curX = 0, curY = 0, curZ = 5.0;
    let curMotion = "G0";
    let curFeed = 800;

    for (let idx = 0; idx < lines.length; idx++) {
      const raw = lines[idx];
      let line = raw.replace(/\(.*?\)/g, "").split(";")[0].trim().toUpperCase();
      if (!line) continue;

      const tokens = line.split(/\s+/);
      let newX = curX, newY = curY, newZ = curZ;
      let hasMove = false;

      for (let t of tokens) {
        if (t === "G0" || t === "G00") curMotion = "G0";
        else if (t === "G1" || t === "G01") curMotion = "G1";
        else if (t === "G2" || t === "G02") curMotion = "G2";
        else if (t === "G3" || t === "G03") curMotion = "G3";
        else if (t.startsWith("X")) { const v = parseFloat(t.slice(1)); if (!isNaN(v)) { newX = v; hasMove = true; } }
        else if (t.startsWith("Y")) { const v = parseFloat(t.slice(1)); if (!isNaN(v)) { newY = v; hasMove = true; } }
        else if (t.startsWith("Z")) { const v = parseFloat(t.slice(1)); if (!isNaN(v)) { newZ = v; hasMove = true; } }
        else if (t.startsWith("F")) { const v = parseFloat(t.slice(1)); if (!isNaN(v)) { curFeed = v; } }
      }


      if (hasMove) {
        segments.push({
          lineIndex: idx,
          rawLine: raw,
          type: curMotion === "G0" ? "rapid" : "feed",
          motion: curMotion,
          feed: curFeed,
          x1: curX, y1: curY, z1: curZ,
          x2: newX, y2: newY, z2: newZ,
        });
        curX = newX;
        curY = newY;
        curZ = newZ;
      }
    }

    return segments;
  }

  drawSurfaceMesh(ctx) {
    if (!this.surfaceMesh || !this.surfaceMesh.points || this.surfaceMesh.points.length === 0) return;

    const points = this.surfaceMesh.points;
    const triangles = this.surfaceMesh.triangles || [];
    const shape = (this.surfaceMesh.shape_type || "rectangle").toUpperCase();

    // Elevation extents
    const zs = points.map(p => p.z || 0.0);
    const minZ = Math.min(...zs);
    const maxZ = Math.max(...zs);
    const spanZ = Math.max(0.01, maxZ - minZ);

    function getElevationColor(z) {
      const norm = Math.max(0.0, Math.min(1.0, (z - minZ) / spanZ));
      if (norm < 0.5) {
        const t = norm * 2.0;
        const r = Math.round(56 * (1 - t) + 16 * t);
        const g = Math.round(189 * (1 - t) + 185 * t);
        const b = Math.round(248 * (1 - t) + 129 * t);
        return `rgba(${r}, ${g}, ${b}, 0.22)`;
      } else {
        const t = (norm - 0.5) * 2.0;
        const r = Math.round(16 * (1 - t) + 239 * t);
        const g = Math.round(185 * (1 - t) + 68 * t);
        const b = Math.round(129 * (1 - t) + 68 * t);
        return `rgba(${r}, ${g}, ${b}, 0.25)`;
      }
    }

    // 1. Draw 3D Triangulated Surface Facets
    if (triangles.length > 0) {
      triangles.forEach(tri => {
        const p1 = points[tri[0]];
        const p2 = points[tri[1]];
        const p3 = points[tri[2]];
        if (p1 && p2 && p3) {
          const s1 = this.toScreen(p1.x, p1.y, p1.z || 0.0);
          const s2 = this.toScreen(p2.x, p2.y, p2.z || 0.0);
          const s3 = this.toScreen(p3.x, p3.y, p3.z || 0.0);

          const avgZ = ((p1.z || 0) + (p2.z || 0) + (p3.z || 0)) / 3.0;

          ctx.beginPath();
          ctx.moveTo(s1.x, s1.y);
          ctx.lineTo(s2.x, s2.y);
          ctx.lineTo(s3.x, s3.y);
          ctx.closePath();
          ctx.fillStyle = getElevationColor(avgZ);
          ctx.fill();

          ctx.strokeStyle = "rgba(56, 189, 248, 0.25)";
          ctx.lineWidth = 1.0;
          ctx.stroke();
        }
      });
    }

    // 2. Draw Active Probe Point Nodes
    points.forEach(p => {
      if (p.active !== false) {
        const s = this.toScreen(p.x, p.y, p.z || 0.0);
        ctx.beginPath();
        ctx.arc(s.x, s.y, 3.5, 0, 2 * Math.PI);
        ctx.fillStyle = "#10b981";
        ctx.strokeStyle = "#047857";
        ctx.lineWidth = 1.0;
        ctx.fill();
        ctx.stroke();
      }
    });

    // 3. Topographic Legend Banner in 3D Mode
    ctx.fillStyle = "rgba(56, 189, 248, 0.9)";
    ctx.font = "11px sans-serif";
    ctx.fillText(`🌐 Mesh Surface: ${shape} (${points.length} pts | ΔZ: ${minZ > 0 ? "+" : ""}${minZ.toFixed(2)}mm..${maxZ > 0 ? "+" : ""}${maxZ.toFixed(2)}mm)`, 10, 20);
  }

  drawGCodeToolpath(ctx) {
    if (!this.gcodeToolpath || this.gcodeToolpath.length === 0) return;

    // 1. Draw Rapid Moves (G0) in dashed pink/red
    ctx.beginPath();
    ctx.strokeStyle = "rgba(244, 63, 94, 0.65)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 3]);

    for (let i = 0; i < this.gcodeToolpath.length; i++) {
      const seg = this.gcodeToolpath[i];
      if (seg.type === "rapid") {
        const p1 = this.toScreen(seg.x1, seg.y1, seg.z1);
        const p2 = this.toScreen(seg.x2, seg.y2, seg.z2);
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
      }
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // 2. Draw Cutting Feeds (G1) in vibrant cyan with depth gradient
    ctx.lineWidth = Math.max(1.8, Math.min(5, this.toolDiameter * this.scale * 0.75));
    ctx.lineCap = "round";

    for (let i = 0; i < this.gcodeToolpath.length; i++) {
      const seg = this.gcodeToolpath[i];
      if (seg.type === "feed") {
        const p1 = this.toScreen(seg.x1, seg.y1, seg.z1);
        const p2 = this.toScreen(seg.x2, seg.y2, seg.z2);

        // Highlight selected line
        if (seg.lineIndex === this.highlightedLine || i === this.simIndex) {
          ctx.strokeStyle = "#facc15"; // Glowing Yellow
          ctx.lineWidth = 3.5;
        } else {
          ctx.strokeStyle = seg.z2 < 0 ? "#0284c7" : "#38bdf8";
          ctx.lineWidth = 2.0;
        }

        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    }

    // 3. Plunge / Retract Entry Dots
    for (let seg of this.gcodeToolpath) {
      if (seg.type === "feed" && seg.z1 > 0 && seg.z2 <= 0) {
        const p = this.toScreen(seg.x2, seg.y2, seg.z2);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, 2 * Math.PI);
        ctx.fillStyle = "#10b981";
        ctx.fill();
      }
    }
  }

  drawSimulatedTool(ctx) {
    if (!this.gcodeToolpath || this.gcodeToolpath.length === 0) return;
    const seg = this.gcodeToolpath[Math.min(this.simIndex, this.gcodeToolpath.length - 1)];
    if (!seg) return;

    const tip = this.toScreen(seg.x2, seg.y2, seg.z2);
    const top = this.toScreen(seg.x2, seg.y2, seg.z2 + 15.0);

    // 3D Cutter Cylinder Body
    ctx.strokeStyle = "rgba(56, 189, 248, 0.9)";
    ctx.lineWidth = Math.max(3, this.toolDiameter * this.scale);
    ctx.beginPath();
    ctx.moveTo(tip.x, tip.y);
    ctx.lineTo(top.x, top.y);
    ctx.stroke();

    // Cutter Tip Dot
    ctx.beginPath();
    ctx.arc(tip.x, tip.y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = "#facc15";
    ctx.fill();
    ctx.stroke();

    // Update HUD
    const hud = document.getElementById("simHud");
    if (hud) {
      hud.textContent = `X: ${seg.x2.toFixed(2)} | Y: ${seg.y2.toFixed(2)} | Z: ${seg.z2.toFixed(2)} | F${seg.feed} | Step ${this.simIndex + 1}/${this.gcodeToolpath.length}`;
    }
  }

  // Simulation Controls
  playSimulation() {
    if (!this.gcodeToolpath || this.gcodeToolpath.length === 0) return;
    this.simPlaying = true;
    const stepInterval = Math.max(20, 150 / this.simSpeed);

    clearInterval(this.simTimer);
    this.simTimer = setInterval(() => {
      if (this.simIndex < this.gcodeToolpath.length - 1) {
        this.stepForward();
      } else {
        this.pauseSimulation();
        const btnPlay = document.getElementById("btnSimPlay");
        if (btnPlay) btnPlay.textContent = "▶ Play";
      }
    }, stepInterval);
  }

  pauseSimulation() {
    this.simPlaying = false;
    clearInterval(this.simTimer);
  }

  stepForward() {
    if (!this.gcodeToolpath || this.simIndex >= this.gcodeToolpath.length - 1) return;
    this.simIndex++;
    this.syncScrubber();
    this.draw();
  }

  stepBackward() {
    if (!this.gcodeToolpath || this.simIndex <= 0) return;
    this.simIndex--;
    this.syncScrubber();
    this.draw();
  }

  seekSimulation(index) {
    if (!this.gcodeToolpath) return;
    this.simIndex = Math.max(0, Math.min(index, this.gcodeToolpath.length - 1));
    this.syncScrubber();
    this.draw();
  }

  syncScrubber() {
    const scrubber = document.getElementById("simScrubber");
    if (scrubber) scrubber.value = this.simIndex;
    if (this.gcodeToolpath && this.gcodeToolpath[this.simIndex]) {
      this.highlightedLine = this.gcodeToolpath[this.simIndex].lineIndex;
    }
  }

  setHighlightedLine(lineIndex) {
    this.highlightedLine = lineIndex;
    if (this.gcodeToolpath) {
      const idx = this.gcodeToolpath.findIndex((s) => s.lineIndex === lineIndex);
      if (idx !== -1) {
        this.simIndex = idx;
        this.syncScrubber();
      }
    }
    this.draw();
  }

  drawGrid(ctx) {
    const gridSpacing = 50 * this.scale;
    if (gridSpacing < 8) return;

    ctx.strokeStyle = "rgba(51, 65, 85, 0.35)";
    ctx.lineWidth = 0.5;

    const startX = this.offsetX % gridSpacing;
    for (let x = startX; x < this.canvas.width; x += gridSpacing) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();
    }

    const startY = this.offsetY % gridSpacing;
    for (let y = startY; y < this.canvas.height; y += gridSpacing) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvas.width, y);
      ctx.stroke();
    }
  }

  drawDrillHoles(ctx) {
    if (!this.holes || this.holes.length === 0) return;
    const holeRadiusScreen = Math.max(3, (this.toolDiameter / 2.0) * this.scale);

    this.holes.forEach(([hx, hy], idx) => {
      const p = this.toScreen(hx, hy, 0);
      ctx.beginPath();
      ctx.arc(p.x, p.y, holeRadiusScreen, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(14, 165, 233, 0.35)";
      ctx.fill();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(p.x, p.y, 2, 0, 2 * Math.PI);
      ctx.fillStyle = "#f8fafc";
      ctx.fill();

      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px sans-serif";
      ctx.fillText(`#${idx + 1} (${hx.toFixed(1)}, ${hy.toFixed(1)})`, p.x + holeRadiusScreen + 4, p.y - 3);
    });
  }

  drawPockets(ctx) {
    if (!this.holes || this.holes.length === 0) return;
    const pocketRadiusScreen = (this.pocketDiameter / 2.0) * this.scale;

    this.holes.forEach(([hx, hy], idx) => {
      const p = this.toScreen(hx, hy, 0);
      ctx.beginPath();
      ctx.arc(p.x, p.y, pocketRadiusScreen, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(14, 165, 233, 0.15)";
      ctx.fill();
      ctx.strokeStyle = "#0ea5e9";
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }

  drawThreadMilling(ctx) {
    if (!this.holes || this.holes.length === 0) return;
    const majorRadiusScreen = (this.threadNominalDia / 2.0) * this.scale;

    this.holes.forEach(([hx, hy], idx) => {
      const p = this.toScreen(hx, hy, 0);
      ctx.beginPath();
      ctx.arc(p.x, p.y, majorRadiusScreen, 0, 2 * Math.PI);
      ctx.strokeStyle = "#a855f7";
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }

  drawSurfacing(ctx) {
    const s = this.surfacing;
    if (!s) return;
    let minX = s.originMode === "center" ? s.originX - s.lengthX / 2 : s.originX;
    let maxX = s.originMode === "center" ? s.originX + s.lengthX / 2 : s.originX + s.lengthX;
    let minY = s.originMode === "center" ? s.originY - s.widthY / 2 : s.originY;
    let maxY = s.originMode === "center" ? s.originY + s.widthY / 2 : s.originY + s.widthY;

    const p00 = this.toScreen(minX, minY, 0);
    const p10 = this.toScreen(maxX, minY, 0);
    const p11 = this.toScreen(maxX, maxY, 0);
    const p01 = this.toScreen(minX, maxY, 0);

    ctx.fillStyle = "rgba(245, 158, 11, 0.1)";
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(p00.x, p00.y);
    ctx.lineTo(p10.x, p10.y);
    ctx.lineTo(p11.x, p11.y);
    ctx.lineTo(p01.x, p01.y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  drawRectangularPocket(ctx) {
    const p = this.rectangularPocket;
    if (!p) return;
    let minX = p.originMode === "center" ? p.originX - p.lengthX / 2 : p.originX;
    let maxX = p.originMode === "center" ? p.originX + p.lengthX / 2 : p.originX + p.lengthX;
    let minY = p.originMode === "center" ? p.originY - p.widthY / 2 : p.originY;
    let maxY = p.originMode === "center" ? p.originY + p.widthY / 2 : p.originY + p.widthY;

    const p00 = this.toScreen(minX, minY, 0);
    const p10 = this.toScreen(maxX, minY, 0);
    const p11 = this.toScreen(maxX, maxY, 0);
    const p01 = this.toScreen(minX, maxY, 0);

    ctx.fillStyle = "rgba(14, 165, 233, 0.15)";
    ctx.strokeStyle = "#0ea5e9";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(p00.x, p00.y);
    ctx.lineTo(p10.x, p10.y);
    ctx.lineTo(p11.x, p11.y);
    ctx.lineTo(p01.x, p01.y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  drawRectangularBoss(ctx) {
    const b = this.rectangularBoss;
    if (!b) return;
    const minX = b.bossOriginX - b.stockLengthX / 2;
    const maxX = b.bossOriginX + b.stockLengthX / 2;
    const minY = b.bossOriginY - b.stockWidthY / 2;
    const maxY = b.bossOriginY + b.stockWidthY / 2;

    const p00 = this.toScreen(minX, minY, 0);
    const p10 = this.toScreen(maxX, minY, 0);
    const p11 = this.toScreen(maxX, maxY, 0);
    const p01 = this.toScreen(minX, maxY, 0);

    ctx.fillStyle = "rgba(245, 158, 11, 0.1)";
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(p00.x, p00.y);
    ctx.lineTo(p10.x, p10.y);
    ctx.lineTo(p11.x, p11.y);
    ctx.lineTo(p01.x, p01.y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }


  getEngravingGlyph(c, fontName = "simplex_sans") {
    if (this.engravingGlyphs) {
      const font = this.engravingGlyphs[fontName] || this.engravingGlyphs["simplex_sans"] || Object.values(this.engravingGlyphs)[0];
      if (font) {
        if (font[c]) return font[c];
        if (font[c.toUpperCase()]) return font[c.toUpperCase()];
        if (font["?"]) return font["?"];
      }
    }

    // Built-in fallback stroke vectors (grid: cap height = 10.0, baseline = 0.0)
    const C = c.toUpperCase();
    const FALLBACK_GLYPHS = {
      " ": { w: 4.0, strokes: [] },
      "-": { w: 4.0, strokes: [[[0.5, 5.0], [3.5, 5.0]]] },
      ".": { w: 2.0, strokes: [[[1.0, 0.0], [1.0, 0.5]]] },
      ":": { w: 2.0, strokes: [[[1.0, 2.0], [1.0, 2.5]], [[1.0, 6.0], [1.0, 6.5]]] },
      "/": { w: 5.0, strokes: [[[0.5, 0.0], [4.5, 10.0]]] },
      "+": { w: 6.0, strokes: [[[1.0, 5.0], [5.0, 5.0]], [[3.0, 2.0], [3.0, 8.0]]] },
      "0": { w: 6.0, strokes: [[[1.0, 0.0], [5.0, 0.0], [5.0, 10.0], [1.0, 10.0], [1.0, 0.0], [5.0, 10.0]]] },
      "1": { w: 4.0, strokes: [[[1.0, 7.0], [3.0, 10.0], [3.0, 0.0], [1.0, 0.0], [5.0, 0.0]]] },
      "2": { w: 6.0, strokes: [[[1.0, 8.0], [2.0, 10.0], [4.0, 10.0], [5.0, 8.0], [1.0, 0.0], [5.0, 0.0]]] },
      "3": { w: 6.0, strokes: [[[1.0, 9.0], [2.0, 10.0], [4.0, 10.0], [5.0, 8.0], [3.0, 5.0], [5.0, 2.0], [4.0, 0.0], [2.0, 0.0], [1.0, 1.0]]] },
      "4": { w: 6.0, strokes: [[[4.5, 0.0], [4.5, 10.0], [1.0, 3.0], [5.5, 3.0]]] },
      "5": { w: 6.0, strokes: [[[5.0, 10.0], [1.0, 10.0], [1.0, 5.0], [4.0, 5.0], [5.0, 3.0], [5.0, 1.0], [4.0, 0.0], [1.0, 0.0]]] },
      "6": { w: 6.0, strokes: [[[5.0, 9.0], [3.0, 10.0], [1.0, 6.0], [1.0, 2.0], [3.0, 0.0], [5.0, 2.0], [5.0, 4.0], [3.0, 5.0], [1.0, 4.0]]] },
      "7": { w: 6.0, strokes: [[[1.0, 10.0], [5.0, 10.0], [2.0, 0.0]]] },
      "8": { w: 6.0, strokes: [[[3.0, 5.0], [1.0, 7.0], [1.0, 9.0], [3.0, 10.0], [5.0, 9.0], [5.0, 7.0], [3.0, 5.0], [1.0, 3.0], [1.0, 1.0], [3.0, 0.0], [5.0, 1.0], [5.0, 3.0], [3.0, 5.0]]] },
      "9": { w: 6.0, strokes: [[[5.0, 5.0], [3.0, 6.0], [1.0, 6.0], [1.0, 8.0], [3.0, 10.0], [5.0, 8.0], [5.0, 2.0], [3.0, 0.0], [1.0, 1.0]]] },
      "A": { w: 6.0, strokes: [[[1.0, 0.0], [3.0, 10.0], [5.0, 0.0]], [[1.8, 4.0], [4.2, 4.0]]] },
      "B": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.0, 10.0], [5.0, 8.0], [4.0, 5.0], [1.0, 5.0]], [[4.0, 5.0], [5.0, 2.5], [4.0, 0.0], [1.0, 0.0]]] },
      "C": { w: 6.0, strokes: [[[5.0, 8.0], [4.0, 10.0], [2.0, 10.0], [1.0, 8.0], [1.0, 2.0], [2.0, 0.0], [4.0, 0.0], [5.0, 2.0]]] },
      "D": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.0, 10.0], [5.0, 7.0], [5.0, 3.0], [4.0, 0.0], [1.0, 0.0]]] },
      "E": { w: 5.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.5, 10.0]], [[1.0, 5.0], [3.5, 5.0]], [[1.0, 0.0], [4.5, 0.0]]] },
      "F": { w: 5.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.5, 10.0]], [[1.0, 5.0], [3.5, 5.0]]] },
      "G": { w: 6.0, strokes: [[[5.0, 8.0], [4.0, 10.0], [2.0, 10.0], [1.0, 8.0], [1.0, 2.0], [2.0, 0.0], [4.0, 0.0], [5.0, 2.0], [5.0, 5.0], [3.5, 5.0]]] },
      "H": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0]], [[5.0, 0.0], [5.0, 10.0]], [[1.0, 5.0], [5.0, 5.0]]] },
      "I": { w: 3.0, strokes: [[[1.5, 0.0], [1.5, 10.0]], [[0.5, 10.0], [2.5, 10.0]], [[0.5, 0.0], [2.5, 0.0]]] },
      "J": { w: 5.0, strokes: [[[3.5, 10.0], [3.5, 2.0], [2.5, 0.0], [1.0, 0.0], [0.5, 1.5]]] },
      "K": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0]], [[5.0, 10.0], [1.0, 4.5]], [[2.5, 6.0], [5.0, 0.0]]] },
      "L": { w: 5.0, strokes: [[[1.0, 10.0], [1.0, 0.0], [4.5, 0.0]]] },
      "M": { w: 7.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [3.5, 4.0], [6.0, 10.0], [6.0, 0.0]]] },
      "N": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [5.0, 0.0], [5.0, 10.0]]] },
      "O": { w: 6.0, strokes: [[[3.0, 10.0], [1.0, 8.0], [1.0, 2.0], [3.0, 0.0], [4.5, 0.0], [5.5, 2.0], [5.5, 8.0], [4.5, 10.0], [3.0, 10.0]]] },
      "P": { w: 5.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.0, 10.0], [5.0, 8.0], [4.0, 5.0], [1.0, 5.0]]] },
      "Q": { w: 6.0, strokes: [[[3.0, 10.0], [1.0, 8.0], [1.0, 2.0], [3.0, 0.0], [4.5, 0.0], [5.5, 2.0], [5.5, 8.0], [4.5, 10.0], [3.0, 10.0]], [[3.5, 3.0], [5.5, -1.0]]] },
      "R": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.0, 10.0], [5.0, 8.0], [4.0, 5.0], [1.0, 5.0]], [[3.5, 5.0], [5.0, 0.0]]] },
      "S": { w: 5.5, strokes: [[[5.0, 8.5], [4.0, 10.0], [2.0, 10.0], [1.0, 8.5], [1.0, 6.5], [4.5, 4.5], [4.5, 1.5], [3.5, 0.0], [1.5, 0.0], [0.5, 1.5]]] },
      "T": { w: 6.0, strokes: [[[3.0, 0.0], [3.0, 10.0]], [[0.5, 10.0], [5.5, 10.0]]] },
      "U": { w: 6.0, strokes: [[[1.0, 10.0], [1.0, 2.0], [2.5, 0.0], [4.5, 0.0], [5.5, 2.0], [5.5, 10.0]]] },
      "V": { w: 6.0, strokes: [[[1.0, 10.0], [3.0, 0.0], [5.0, 10.0]]] },
      "W": { w: 7.0, strokes: [[[1.0, 10.0], [2.0, 0.0], [3.5, 6.0], [5.0, 0.0], [6.0, 10.0]]] },
      "X": { w: 6.0, strokes: [[[1.0, 0.0], [5.0, 10.0]], [[1.0, 10.0], [5.0, 0.0]]] },
      "Y": { w: 6.0, strokes: [[[1.0, 10.0], [3.0, 5.0], [5.0, 10.0]], [[3.0, 5.0], [3.0, 0.0]]] },
      "Z": { w: 6.0, strokes: [[[1.0, 10.0], [5.0, 10.0], [1.0, 0.0], [5.0, 0.0]]] },
    };

    return FALLBACK_GLYPHS[C] || { w: 5.0, strokes: [[[0.5, 0.0], [0.5, 10.0], [4.5, 10.0], [4.5, 0.0], [0.5, 0.0]]] };
  }

  computeEngravingPolylines(e) {
    if (!e || !e.text) return [];
    const scale = (e.fontSize || 10.0) / 10.0;
    const letterSpacing = e.letterSpacing !== undefined ? e.letterSpacing : 1.0;
    const fontName = e.fontName || "simplex_sans";
    const polylines = [];

    if (e.layoutMode === "arc") {
      const arcRadius = e.arcRadius || 30.0;
      const startAngleRad = ((e.startAngleDeg !== undefined ? e.startAngleDeg : 90.0) * Math.PI) / 180.0;
      const isCw = (e.arcDirection !== "counter_clockwise");
      const arcText = (e.text || "").replace(/\n/g, " ").trim();
      const align = e.align || "center";

      const glyphs = [];
      let totalArcLen = 0;
      for (let c of arcText) {
        const g = this.getEngravingGlyph(c, fontName);
        glyphs.push(g);
        totalArcLen += g.w * scale + letterSpacing;
      }
      if (glyphs.length > 0) totalArcLen -= letterSpacing;

      const totalAngleRad = totalArcLen / Math.max(0.1, arcRadius);

      let baseAngleRad = startAngleRad;
      if (align === "center") {
        baseAngleRad = startAngleRad + (isCw ? totalAngleRad / 2.0 : -totalAngleRad / 2.0);
      } else if (align === "right") {
        baseAngleRad = startAngleRad + (isCw ? totalAngleRad : -totalAngleRad);
      }

      let currDist = 0.0;
      for (let i = 0; i < arcText.length; i++) {
        const g = glyphs[i];
        const charW = g.w * scale;
        const charCenterDist = currDist + (charW / 2.0);
        const charAngle = isCw
          ? baseAngleRad - (charCenterDist / arcRadius)
          : baseAngleRad + (charCenterDist / arcRadius);

        for (let stroke of g.strokes) {
          const poly = [];
          for (let pt of stroke) {
            const tOffset = (pt[0] - g.w / 2.0) * scale;
            const tAngleDelta = isCw ? (-tOffset / arcRadius) : (tOffset / arcRadius);
            const ptAngle = charAngle + tAngleDelta;
            const ptRadius = arcRadius + (pt[1] * scale);

            const px = (e.centerX || 0.0) + ptRadius * Math.cos(ptAngle);
            const py = (e.centerY || 0.0) + ptRadius * Math.sin(ptAngle);
            poly.push([px, py]);
          }
          if (poly.length > 0) polylines.push(poly);
        }
        currDist += charW + letterSpacing;
      }
    } else {
      // Linear Layout with Full Rotation and Alignment
      const radRot = ((e.rotationDeg || 0.0) * Math.PI) / 180.0;
      const cosRot = Math.cos(radRot);
      const sinRot = Math.sin(radRot);
      const lineSpacing = (e.fontSize || 10.0) * (e.lineSpacingMult || 1.4);
      const align = e.align || "left";

      const linesText = (e.text || "").split("\n");
      for (let lineIdx = 0; lineIdx < linesText.length; lineIdx++) {
        const lineStr = linesText[lineIdx];
        const glyphs = [];
        let lineWidth = 0.0;

        for (let c of lineStr) {
          const g = this.getEngravingGlyph(c, fontName);
          glyphs.push(g);
          lineWidth += g.w * scale + letterSpacing;
        }
        if (glyphs.length > 0) lineWidth -= letterSpacing;

        let alignXOffset = 0.0;
        if (align === "center") alignXOffset = -lineWidth / 2.0;
        else if (align === "right") alignXOffset = -lineWidth;

        const lineYOffset = -lineIdx * lineSpacing;

        let currCharX = 0.0;
        for (let i = 0; i < lineStr.length; i++) {
          const g = glyphs[i];
          for (let stroke of g.strokes) {
            const poly = [];
            for (let pt of stroke) {
              const lx = alignXOffset + currCharX + (pt[0] * scale);
              const ly = lineYOffset + (pt[1] * scale);

              const rx = (e.startX || 0.0) + (lx * cosRot - ly * sinRot);
              const ry = (e.startY || 0.0) + (lx * sinRot + ly * cosRot);
              poly.push([rx, ry]);
            }
            if (poly.length > 0) polylines.push(poly);
          }
          currCharX += (g.w * scale) + letterSpacing;
        }
      }
    }

    return polylines;
  }

  drawEngraving(ctx) {
    const e = this.engraving;
    if (!e || !e.text) return;

    const polylines = this.computeEngravingPolylines(e);
    if (!polylines || polylines.length === 0) return;

    // Draw reference datum/guideline
    if (e.layoutMode === "arc") {
      const centerPt = this.toScreen(e.centerX || 0, e.centerY || 0, 0);
      ctx.strokeStyle = "rgba(168, 85, 247, 0.4)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.arc(centerPt.x, centerPt.y, (e.arcRadius || 30.0) * this.scale, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
    } else {
      const startPt = this.toScreen(e.startX || 0, e.startY || 0, 0);
      ctx.fillStyle = "#f59e0b";
      ctx.beginPath();
      ctx.arc(startPt.x, startPt.y, 3.5, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Draw Vector Font Strokes in 3D
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = Math.max(1.5, Math.min(4, (this.toolDiameter || 0.5) * this.scale));
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (let poly of polylines) {
      if (poly.length < 2) continue;
      ctx.beginPath();
      const p0 = this.toScreen(poly[0][0], poly[0][1], 0);
      ctx.moveTo(p0.x, p0.y);
      for (let i = 1; i < poly.length; i++) {
        const pi = this.toScreen(poly[i][0], poly[i][1], 0);
        ctx.lineTo(pi.x, pi.y);
      }
      ctx.stroke();
    }
  }
}

