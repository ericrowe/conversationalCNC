/**
 * 2D Interactive Toolpath Visualizer (Phase 2 Upgrade)
 * Supports Drilling, Peck Drilling, Helical Thread Milling, Circular Pockets, and Surfacing
 */
class ToolpathVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
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

    this.scale = 1.0;
    this.offsetX = 60;
    this.offsetY = 320;
    this.isDragging = false;
    this.lastMouse = { x: 0, y: 0 };

    this.resizeCanvas();
    window.addEventListener("resize", () => this.resizeCanvas());
    this.bindEvents();
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
      this.isDragging = true;
      this.lastMouse = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;
      const dx = e.clientX - this.lastMouse.x;
      const dy = e.clientY - this.lastMouse.y;
      this.offsetX += dx;
      this.offsetY += dy;
      this.lastMouse = { x: e.clientX, y: e.clientY };
      this.draw();
    });

    window.addEventListener("mouseup", () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      this.zoom(zoomFactor, e.offsetX, e.offsetY);
    });
  }

  zoom(factor, centerX = this.canvas.width / 2, centerY = this.canvas.height / 2) {
    const newScale = Math.max(0.05, Math.min(25.0, this.scale * factor));
    this.offsetX = centerX - (centerX - this.offsetX) * (newScale / this.scale);
    this.offsetY = centerY - (centerY - this.offsetY) * (newScale / this.scale);
    this.scale = newScale;
    this.draw();
  }

  setData(data = {}) {
    // Backward compatibility if holes passed directly as array
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

    if (this.opType === "surfacing" && this.surfacing) {
      const s = this.surfacing;
      if (s.originMode === "center") {
        allX.push(s.originX - s.lengthX / 2, s.originX + s.lengthX / 2);
        allY.push(s.originY - s.widthY / 2, s.originY + s.widthY / 2);
      } else {
        allX.push(s.originX, s.originX + s.lengthX);
        allY.push(s.originY, s.originY + s.widthY);
      }
    } else if (this.opType === "engraving" && this.engraving) {
      const e = this.engraving;
      if (e.layoutMode === "arc") {
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
    this.scale = Math.min(scaleX, scaleY, 3.5);

    this.offsetX = padding - minX * this.scale;
    this.offsetY = this.canvas.height - padding + minY * this.scale;

    this.draw();
  }

  toScreen(x, y) {
    return {
      x: this.offsetX + x * this.scale,
      y: this.offsetY - y * this.scale,
    };
  }

  draw() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Background
    ctx.fillStyle = "#080d1a";
    ctx.fillRect(0, 0, w, h);

    // Draw Grid
    this.drawGrid(ctx);

    // Draw Machine Envelope
    if (this.machineEnvelope) {
      const p0 = this.toScreen(0, 0);
      const p1 = this.toScreen(this.machineEnvelope.x, this.machineEnvelope.y);
      ctx.strokeStyle = "rgba(239, 68, 68, 0.4)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 6]);
      ctx.strokeRect(p0.x, p1.y, p1.x - p0.x, p0.y - p1.y);
      ctx.setLineDash([]);

      ctx.fillStyle = "rgba(239, 68, 68, 0.7)";
      ctx.font = "10px sans-serif";
      ctx.fillText(
        `Envelope: ${this.machineEnvelope.x} x ${this.machineEnvelope.y} mm`,
        p0.x + 5,
        p1.y + 14
      );
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




    // Draw Origin (0,0)
    const origin = this.toScreen(0, 0);
    ctx.beginPath();
    ctx.arc(origin.x, origin.y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = "#10b981";
    ctx.fill();

    // Axes
    ctx.beginPath();
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(origin.x + 35, origin.y); // +X
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(origin.x, origin.y - 35); // +Y
    ctx.stroke();

    ctx.fillStyle = "#10b981";
    ctx.font = "bold 11px sans-serif";
    ctx.fillText("X0, Y0", origin.x - 30, origin.y + 15);
    ctx.fillText("+X", origin.x + 38, origin.y + 4);
    ctx.fillText("+Y", origin.x - 6, origin.y - 38);
  }

  drawDrillHoles(ctx) {
    if (this.holes.length > 0) {
      // Traverse Rapid path
      ctx.beginPath();
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);

      let prev = this.toScreen(0, 0);
      ctx.moveTo(prev.x, prev.y);

      for (const [hx, hy] of this.holes) {
        const p = this.toScreen(hx, hy);
        ctx.lineTo(p.x, p.y);
      }
      const park = this.toScreen(0, 0);
      ctx.lineTo(park.x, park.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    this.holes.forEach(([hx, hy], idx) => {
      const p = this.toScreen(hx, hy);
      const radiusScreen = Math.max(3, (this.toolDiameter / 2) * this.scale);

      ctx.beginPath();
      ctx.arc(p.x, p.y, radiusScreen, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(56, 189, 248, 0.3)";
      ctx.fill();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Crosshair
      ctx.beginPath();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1;
      ctx.moveTo(p.x - radiusScreen - 2, p.y);
      ctx.lineTo(p.x + radiusScreen + 2, p.y);
      ctx.moveTo(p.x, p.y - radiusScreen - 2);
      ctx.lineTo(p.x, p.y + radiusScreen + 2);
      ctx.stroke();

      // Label
      ctx.fillStyle = "#f8fafc";
      ctx.font = "bold 10px sans-serif";
      ctx.fillText(`#${idx + 1} (${hx}, ${hy})`, p.x + radiusScreen + 4, p.y - 4);
    });
  }

  drawPockets(ctx) {
    // Rapid traverse
    if (this.holes.length > 0) {
      ctx.beginPath();
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      let prev = this.toScreen(0, 0);
      ctx.moveTo(prev.x, prev.y);
      for (const [cx, cy] of this.holes) {
        const p = this.toScreen(cx, cy);
        ctx.lineTo(p.x, p.y);
      }
      ctx.lineTo(prev.x, prev.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    this.holes.forEach(([cx, cy], idx) => {
      const p = this.toScreen(cx, cy);
      const pocketRadiusScreen = (this.pocketDiameter / 2) * this.scale;
      const toolRadiusScreen = (this.toolDiameter / 2) * this.scale;
      const pathRadiusScreen = Math.max(1, ((this.pocketDiameter - this.toolDiameter) / 2) * this.scale);

      // Pocket boundary
      ctx.beginPath();
      ctx.arc(p.x, p.y, pocketRadiusScreen, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(14, 165, 233, 0.15)";
      ctx.fill();
      ctx.strokeStyle = "#0ea5e9";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Tool centerpath circle (cyan dashed)
      ctx.beginPath();
      ctx.arc(p.x, p.y, pathRadiusScreen, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Center crosshair
      ctx.beginPath();
      ctx.strokeStyle = "#0ea5e9";
      ctx.lineWidth = 1;
      ctx.moveTo(p.x - 6, p.y);
      ctx.lineTo(p.x + 6, p.y);
      ctx.moveTo(p.x, p.y - 6);
      ctx.lineTo(p.x, p.y + 6);
      ctx.stroke();

      // Label
      ctx.fillStyle = "#f8fafc";
      ctx.font = "bold 10px sans-serif";
      ctx.fillText(
        `#${idx + 1} Pocket ⌀${this.pocketDiameter}mm (${cx}, ${cy})`,
        p.x + pocketRadiusScreen + 4,
        p.y - 4
      );
    });
  }

  drawThreadMilling(ctx) {
    if (this.holes.length > 0) {
      ctx.beginPath();
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      let prev = this.toScreen(0, 0);
      ctx.moveTo(prev.x, prev.y);
      for (const [hx, hy] of this.holes) {
        const p = this.toScreen(hx, hy);
        ctx.lineTo(p.x, p.y);
      }
      ctx.lineTo(prev.x, prev.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    this.holes.forEach(([hx, hy], idx) => {
      const p = this.toScreen(hx, hy);
      const majorRadiusScreen = (this.threadNominalDia / 2) * this.scale;
      const minorRadiusScreen = Math.max(1, ((this.threadNominalDia - 1.0825 * this.threadPitch) / 2) * this.scale);
      const cutRadiusScreen = Math.max(1, ((this.threadNominalDia - this.toolDiameter) / 2) * this.scale);

      // Major Thread Diameter Circle
      ctx.beginPath();
      ctx.arc(p.x, p.y, majorRadiusScreen, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(168, 85, 247, 0.15)";
      ctx.fill();
      ctx.strokeStyle = "#a855f7";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Minor Hole Circle
      ctx.beginPath();
      ctx.arc(p.x, p.y, minorRadiusScreen, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(192, 132, 252, 0.6)";
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Helical Path Circle (Cyan)
      ctx.beginPath();
      ctx.arc(p.x, p.y, cutRadiusScreen, 0, 2 * Math.PI);
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Center crosshair
      ctx.beginPath();
      ctx.strokeStyle = "#a855f7";
      ctx.lineWidth = 1;
      ctx.moveTo(p.x - 6, p.y);
      ctx.lineTo(p.x + 6, p.y);
      ctx.moveTo(p.x, p.y - 6);
      ctx.lineTo(p.x, p.y + 6);
      ctx.stroke();

      // Label
      ctx.fillStyle = "#f8fafc";
      ctx.font = "bold 10px sans-serif";
      ctx.fillText(
        `#${idx + 1} ⌀${this.threadNominalDia}x${this.threadPitch} (${hx}, ${hy})`,
        p.x + majorRadiusScreen + 4,
        p.y - 4
      );
    });
  }

  drawSurfacing(ctx) {
    const s = this.surfacing;
    let minX, maxX, minY, maxY;

    if (s.originMode === "center") {
      minX = s.originX - s.lengthX / 2;
      maxX = s.originX + s.lengthX / 2;
      minY = s.originY - s.widthY / 2;
      maxY = s.originY + s.widthY / 2;
    } else {
      minX = s.originX;
      maxX = s.originX + s.lengthX;
      minY = s.originY;
      maxY = s.originY + s.widthY;
    }

    const p0 = this.toScreen(minX, minY);
    const p1 = this.toScreen(maxX, maxY);

    // Stock boundary rectangle
    ctx.fillStyle = "rgba(245, 158, 11, 0.1)";
    ctx.fillRect(p0.x, p1.y, p1.x - p0.x, p0.y - p1.y);
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.strokeRect(p0.x, p1.y, p1.x - p0.x, p0.y - p1.y);

    // Tool raster passes
    const toolRadius = (s.toolDiameter || 25.4) / 2.0;
    const stepoverDist = (s.toolDiameter || 25.4) * ((s.stepoverPercent || 70) / 100.0);
    const overtravel = s.overtravel || 2.0;

    const xMinCut = minX - toolRadius - overtravel;
    const xMaxCut = maxX + toolRadius + overtravel;

    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 1.5;

    let currY = minY + toolRadius - stepoverDist * 0.3;
    let passIdx = 0;

    while (currY <= maxY + toolRadius) {
      const sp0 = this.toScreen(xMinCut, currY);
      const sp1 = this.toScreen(xMaxCut, currY);

      ctx.beginPath();
      if (passIdx % 2 === 0 || s.cutDirection === "climb_oneway") {
        ctx.moveTo(sp0.x, sp0.y);
        ctx.lineTo(sp1.x, sp1.y);
      } else {
        ctx.moveTo(sp1.x, sp1.y);
        ctx.lineTo(sp0.x, sp0.y);
      }
      ctx.stroke();

      currY += stepoverDist;
      passIdx++;
    }

    // Stock size label
    ctx.fillStyle = "#fbbf24";
    ctx.font = "bold 11px sans-serif";
    ctx.fillText(`Stock: ${s.lengthX} x ${s.widthY} mm`, p0.x + 8, p1.y + 18);
  }

  drawRectangularPocket(ctx) {
    const p = this.rectangularPocket;
    if (!p) return;

    let minX, maxX, minY, maxY, cx, cy;
    if (p.originMode === "center") {
      minX = p.originX - p.lengthX / 2;
      maxX = p.originX + p.lengthX / 2;
      minY = p.originY - p.widthY / 2;
      maxY = p.originY + p.widthY / 2;
      cx = p.originX;
      cy = p.originY;
    } else {
      minX = p.originX;
      maxX = p.originX + p.lengthX;
      minY = p.originY;
      maxY = p.originY + p.widthY;
      cx = minX + p.lengthX / 2;
      cy = minY + p.widthY / 2;
    }

    const p0 = this.toScreen(minX, minY);
    const p1 = this.toScreen(maxX, maxY);
    const pCenter = this.toScreen(cx, cy);

    // Draw pocket boundary with corner radius
    const r = Math.max(0, (p.cornerRadius || 0) * this.scale);
    ctx.fillStyle = "rgba(14, 165, 233, 0.12)";
    ctx.strokeStyle = "#0ea5e9";
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.roundRect(p0.x, p1.y, p1.x - p0.x, p0.y - p1.y, r);
    ctx.fill();
    ctx.stroke();

    // Draw concentric roughing rings in cyan dashed line
    const toolRad = (this.toolDiameter || 6.35) / 2.0;
    const stepover = (this.toolDiameter || 6.35) * ((p.stepoverPercent || 60) / 100.0);
    const finishAllow = p.finishPassAllowance || 0.3;

    const roughMinX = minX + toolRad + finishAllow;
    const roughMaxX = maxX - toolRad - finishAllow;
    const roughMinY = minY + toolRad + finishAllow;
    const roughMaxY = maxY - toolRad - finishAllow;

    if (roughMaxX > roughMinX && roughMaxY > roughMinY) {
      const numRings = Math.max(1, Math.ceil(Math.max(roughMaxX - cx, roughMaxY - cy) / stepover));
      ctx.strokeStyle = "rgba(56, 189, 248, 0.75)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([3, 3]);

      for (let i = 1; i <= numRings; i++) {
        const frac = i / numRings;
        const rMinX = cx - (cx - roughMinX) * frac;
        const rMaxX = cx + (roughMaxX - cx) * frac;
        const rMinY = cy - (cy - roughMinY) * frac;
        const rMaxY = cy + (roughMaxY - cy) * frac;

        const sp0 = this.toScreen(rMinX, rMinY);
        const sp1 = this.toScreen(rMaxX, rMaxY);
        const ringR = Math.max(0, (r - (toolRad + finishAllow) * this.scale) * frac);

        ctx.beginPath();
        ctx.roundRect(sp0.x, sp1.y, sp1.x - sp0.x, sp0.y - sp1.y, ringR);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }

    // Center Crosshair
    ctx.beginPath();
    ctx.strokeStyle = "#0ea5e9";
    ctx.lineWidth = 1;
    ctx.moveTo(pCenter.x - 8, pCenter.y);
    ctx.lineTo(pCenter.x + 8, pCenter.y);
    ctx.moveTo(pCenter.x, pCenter.y - 8);
    ctx.lineTo(pCenter.x, pCenter.y + 8);
    ctx.stroke();

    // Label
    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 11px sans-serif";
    ctx.fillText(`Pocket ${p.lengthX}x${p.widthY}mm (R${p.cornerRadius || 0}mm)`, p0.x + 8, p1.y + 18);
  }

  drawRectangularBoss(ctx) {
    const b = this.rectangularBoss;
    if (!b) return;

    const cx = b.bossOriginX;
    const cy = b.bossOriginY;

    const stockMinX = cx - b.stockLengthX / 2;
    const stockMaxX = cx + b.stockLengthX / 2;
    const stockMinY = cy - b.stockWidthY / 2;
    const stockMaxY = cy + b.stockWidthY / 2;

    const bossMinX = cx - b.bossLengthX / 2;
    const bossMaxX = cx + b.bossLengthX / 2;
    const bossMinY = cy - b.bossWidthY / 2;
    const bossMaxY = cy + b.bossWidthY / 2;

    const sp0 = this.toScreen(stockMinX, stockMinY);
    const sp1 = this.toScreen(stockMaxX, stockMaxY);

    const bp0 = this.toScreen(bossMinX, bossMinY);
    const bp1 = this.toScreen(bossMaxX, bossMaxY);

    // Outer Stock Boundary (Amber)
    ctx.strokeStyle = "rgba(245, 158, 11, 0.6)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(sp0.x, sp1.y, sp1.x - sp0.x, sp0.y - sp1.y);
    ctx.setLineDash([]);

    // Cleared Material Region
    ctx.fillStyle = "rgba(14, 165, 233, 0.12)";
    ctx.fillRect(sp0.x, sp1.y, sp1.x - sp0.x, sp0.y - sp1.y);

    // Inner Boss Island (Solid Teal)
    const r = Math.max(0, (b.bossCornerRadius || 0) * this.scale);
    ctx.fillStyle = "rgba(16, 185, 129, 0.35)";
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.roundRect(bp0.x, bp1.y, bp1.x - bp0.x, bp0.y - bp1.y, r);
    ctx.fill();
    ctx.stroke();

    // Labels
    ctx.fillStyle = "#fbbf24";
    ctx.font = "10px sans-serif";
    ctx.fillText(`Stock: ${b.stockLengthX}x${b.stockWidthY}mm`, sp0.x + 6, sp1.y + 14);

    ctx.fillStyle = "#10b981";
    ctx.font = "bold 11px sans-serif";
    ctx.fillText(`Boss: ${b.bossLengthX}x${b.bossWidthY}mm`, bp0.x + 6, bp1.y + 16);
  }

  drawEngraving(ctx) {

    const e = this.engraving;
    if (!e || !e.text) return;

    // Fetch or calculate vector stroke polylines
    const polylines = this.computeEngravingPolylines(e);
    if (!polylines || polylines.length === 0) return;

    const tipWidth = e.tipWidth || this.toolDiameter || 0.20;
    const strokeWidthPx = Math.max(1.5, Math.min(6, tipWidth * this.scale * 1.5));

    // 1. Draw Guides (Arc Pitch Circle or Linear Origin)
    if (e.layoutMode === "arc") {
      const center = this.toScreen(e.centerX, e.centerY);
      const radiusPx = e.arcRadius * this.scale;

      // Dashed pitch circle
      ctx.beginPath();
      ctx.arc(center.x, center.y, radiusPx, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Center crosshair
      ctx.beginPath();
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.2;
      ctx.moveTo(center.x - 7, center.y);
      ctx.lineTo(center.x + 7, center.y);
      ctx.moveTo(center.x, center.y - 7);
      ctx.lineTo(center.x, center.y + 7);
      ctx.stroke();

      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px sans-serif";
      ctx.fillText(`Center (${e.centerX}, ${e.centerY}) R${e.arcRadius}mm`, center.x + 10, center.y + 12);
    } else {
      const start = this.toScreen(e.startX, e.startY);

      // Start coordinate point
      ctx.beginPath();
      ctx.arc(start.x, start.y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = "#10b981";
      ctx.fill();

      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px sans-serif";
      ctx.fillText(`Start (${e.startX}, ${e.startY})`, start.x + 8, start.y - 6);
    }

    // 2. Draw Rapid Moves Between Strokes (G0 in dashed red/pink)
    ctx.beginPath();
    ctx.strokeStyle = "rgba(244, 63, 94, 0.75)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 3]);

    let lastPoint = null;
    polylines.forEach((poly) => {
      if (poly.length === 0) return;
      const firstPt = this.toScreen(poly[0][0], poly[0][1]);
      if (lastPoint) {
        ctx.moveTo(lastPoint.x, lastPoint.y);
        ctx.lineTo(firstPt.x, firstPt.y);
      }
      const lastVertex = poly[poly.length - 1];
      lastPoint = this.toScreen(lastVertex[0], lastVertex[1]);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // 3. Draw Cutting Feeds Along Polylines (G1 in solid bright cyan)
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = strokeWidthPx;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    polylines.forEach((poly) => {
      if (poly.length < 2) return;
      ctx.beginPath();
      const p0 = this.toScreen(poly[0][0], poly[0][1]);
      ctx.moveTo(p0.x, p0.y);
      for (let i = 1; i < poly.length; i++) {
        const pi = this.toScreen(poly[i][0], poly[i][1]);
        ctx.lineTo(pi.x, pi.y);
      }
      ctx.stroke();
    });

    // 4. Draw Plunge Points (Green) & Retract Points (Amber)
    polylines.forEach((poly) => {
      if (poly.length === 0) return;
      // Plunge dot at stroke start
      const pStart = this.toScreen(poly[0][0], poly[0][1]);
      ctx.beginPath();
      ctx.arc(pStart.x, pStart.y, 2.5, 0, 2 * Math.PI);
      ctx.fillStyle = "#10b981";
      ctx.fill();

      // Retract dot at stroke end
      const lastPt = poly[poly.length - 1];
      const pEnd = this.toScreen(lastPt[0], lastPt[1]);
      ctx.beginPath();
      ctx.arc(pEnd.x, pEnd.y, 2.5, 0, 2 * Math.PI);
      ctx.fillStyle = "#f59e0b";
      ctx.fill();
    });
  }

  computeEngravingPolylines(e) {
    const text = e.text || "";
    const scale = (e.fontSize || 10.0) / 10.0;
    const letterSpacing = e.letterSpacing !== undefined ? e.letterSpacing : 1.0;
    const fontName = e.fontName || "simplex_sans";
    const polylines = [];

    const getGlyph = (char) => {
      if (ToolpathVisualizer.FONT_GLYPHS && ToolpathVisualizer.FONT_GLYPHS[fontName] && ToolpathVisualizer.FONT_GLYPHS[fontName][char]) {
        return ToolpathVisualizer.FONT_GLYPHS[fontName][char];
      }
      if (ToolpathVisualizer.FONT_GLYPHS && ToolpathVisualizer.FONT_GLYPHS["simplex_sans"] && ToolpathVisualizer.FONT_GLYPHS["simplex_sans"][char]) {
        return ToolpathVisualizer.FONT_GLYPHS["simplex_sans"][char];
      }
      return ToolpathVisualizer.FALLBACK_SIMPLEX[char] || ToolpathVisualizer.FALLBACK_SIMPLEX["?"] || { w: 4.0, strokes: [] };
    };

    if (e.layoutMode === "arc") {
      const arcRadius = e.arcRadius || 30.0;
      if (arcRadius <= 0) return polylines;

      const arcText = text.replace(/\n/g, " ").trim();
      const glyphs = Array.from(arcText).map(getGlyph);
      const charWidths = glyphs.map((g) => g.w * scale + letterSpacing);
      const totalArcLen = charWidths.reduce((a, b) => a + b, 0);
      const totalAngleRad = totalArcLen / arcRadius;

      const startAngleRad = ((e.startAngleDeg !== undefined ? e.startAngleDeg : 90.0) * Math.PI) / 180.0;
      const isCw = e.arcDirection !== "counter_clockwise";

      let baseAngleRad = startAngleRad;
      if (e.align === "center") {
        baseAngleRad += isCw ? totalAngleRad / 2.0 : -totalAngleRad / 2.0;
      } else if (e.align === "right") {
        baseAngleRad += isCw ? totalAngleRad : -totalAngleRad;
      }

      let currDist = 0.0;
      for (let i = 0; i < arcText.length; i++) {
        const g = glyphs[i];
        const charW = g.w * scale;
        const charCenterDist = currDist + charW / 2.0;
        const charAngle = isCw
          ? baseAngleRad - charCenterDist / arcRadius
          : baseAngleRad + charCenterDist / arcRadius;

        for (const rawStroke of g.strokes) {
          const stroke = this.smoothStroke(rawStroke, e.curveSubdivisions || 4);
          const poly = [];
          for (const [gx, gy] of stroke) {
            const tOffset = (gx - g.w / 2.0) * scale;
            const tAngleDelta = !isCw ? tOffset / arcRadius : -tOffset / arcRadius;
            const ptAngle = charAngle + tAngleDelta;
            const ptRadius = arcRadius + gy * scale;

            const px = e.centerX + ptRadius * Math.cos(ptAngle);
            const py = e.centerY + ptRadius * Math.sin(ptAngle);
            poly.push([px, py]);
          }
          if (poly.length > 0) {
            polylines.push(poly);
          }
        }
        currDist += charW + letterSpacing;
      }
    } else {
      // Linear layout
      const radRot = ((e.rotationDeg || 0.0) * Math.PI) / 180.0;
      const cosRot = Math.cos(radRot);
      const sinRot = Math.sin(radRot);
      const lineSpacingMult = e.lineSpacingMult || 1.4;

      const lines = text.split("\n");
      lines.forEach((lineStr, lineIdx) => {
        const glyphs = Array.from(lineStr).map(getGlyph);
        const charWidths = glyphs.map((g) => g.w * scale + letterSpacing);
        const lineWidth = charWidths.reduce((a, b) => a + b, 0) - (charWidths.length > 0 ? letterSpacing : 0);

        let alignXOffset = 0.0;
        if (e.align === "center") {
          alignXOffset = -lineWidth / 2.0;
        } else if (e.align === "right") {
          alignXOffset = -lineWidth;
        }

        const lineYOffset = -lineIdx * (e.fontSize * lineSpacingMult);
        let currCharX = 0.0;

        for (let i = 0; i < lineStr.length; i++) {
          const g = glyphs[i];
          for (const rawStroke of g.strokes) {
            const stroke = this.smoothStroke(rawStroke, e.curveSubdivisions || 4);
            const poly = [];
            for (const [gx, gy] of stroke) {
              const lx = alignXOffset + currCharX + gx * scale;
              const ly = lineYOffset + gy * scale;

              const px = e.startX + (lx * cosRot - ly * sinRot);
              const py = e.startY + (lx * sinRot + ly * cosRot);
              poly.push([px, py]);
            }
            if (poly.length > 0) {
              polylines.push(poly);
            }
          }
          currCharX += g.w * scale + letterSpacing;
        }
      });
    }

    return polylines;
  }

  smoothStroke(poly, steps = 4, cornerThresholdDeg = 65.0) {
    if (!poly || poly.length < 3 || steps <= 1) return poly;
    const isClosed = (poly[0][0] === poly[poly.length - 1][0] && poly[0][1] === poly[poly.length - 1][1]);
    const n = poly.length;
    const result = [];

    const angleBetween = (v1, v2) => {
      const dot = v1[0] * v2[0] + v1[1] * v2[1];
      const m1 = Math.hypot(v1[0], v1[1]);
      const m2 = Math.hypot(v2[0], v2[1]);
      if (m1 === 0 || m2 === 0) return 0;
      const cosVal = Math.max(-1.0, Math.min(1.0, dot / (m1 * m2)));
      return (Math.acos(cosVal) * 180.0) / Math.PI;
    };

    for (let i = 0; i < n - 1; i++) {
      const p1 = poly[i];
      const p2 = poly[i + 1];

      let isSharp1 = false;
      let isSharp2 = false;

      if (!isClosed) {
        if (i === 0) isSharp1 = true;
        if (i + 1 === n - 1) isSharp2 = true;
      }

      if (i > 0 && !isSharp1) {
        const pPrev = poly[i - 1];
        const vIn = [p1[0] - pPrev[0], p1[1] - pPrev[1]];
        const vOut = [p2[0] - p1[0], p2[1] - p1[1]];
        if (angleBetween(vIn, vOut) > cornerThresholdDeg) isSharp1 = true;
      }

      if (i + 2 < n && !isSharp2) {
        const pNext = poly[i + 2];
        const vIn = [p2[0] - p1[0], p2[1] - p1[1]];
        const vOut = [pNext[0] - p2[0], pNext[1] - p2[1]];
        if (angleBetween(vIn, vOut) > cornerThresholdDeg) isSharp2 = true;
      }

      let p0, p3;
      if (isClosed) {
        p0 = !isSharp1 ? poly[(i - 1 + n - 1) % (n - 1)] : p1;
        p3 = !isSharp2 ? poly[(i + 2) % (n - 1)] : p2;
      } else {
        p0 = (i > 0 && !isSharp1) ? poly[i - 1] : [2 * p1[0] - p2[0], 2 * p1[1] - p2[1]];
        p3 = (i + 2 < n && !isSharp2) ? poly[i + 2] : [2 * p2[0] - p1[0], 2 * p2[1] - p1[1]];
      }

      const numPoints = (i < n - 2) ? steps : steps + 1;
      for (let s = 0; s < numPoints; s++) {
        const t = s / steps;
        const t2 = t * t;
        const t3 = t2 * t;

        const x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3);
        const y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
        result.push([x, y]);
      }
    }

    return result;
  }




  loadGCode(gcodeText) {
    if (!gcodeText) return;
    this.gcodeToolpath = this.parseGCode(gcodeText);
    this.draw();
  }

  clearGCode() {
    this.gcodeToolpath = null;
    this.draw();
  }

  parseGCode(gcodeText) {
    const lines = gcodeText.split("\n");
    const segments = [];
    let curX = 0, curY = 0, curZ = 2.0;
    let curMotion = "G0";

    for (let rawLine of lines) {
      // Strip comments
      let line = rawLine.replace(/\(.*?\)/g, "").split(";")[0].trim().toUpperCase();
      if (!line) continue;

      const tokens = line.split(/\s+/);
      let newX = curX, newY = curY, newZ = curZ;
      let hasMove = false;

      for (let t of tokens) {
        if (t === "G0" || t === "G00") { curMotion = "G0"; }
        else if (t === "G1" || t === "G01") { curMotion = "G1"; }
        else if (t === "G2" || t === "G02") { curMotion = "G2"; }
        else if (t === "G3" || t === "G03") { curMotion = "G3"; }
        else if (t.startsWith("X")) {
          const v = parseFloat(t.slice(1));
          if (!isNaN(v)) { newX = v; hasMove = true; }
        } else if (t.startsWith("Y")) {
          const v = parseFloat(t.slice(1));
          if (!isNaN(v)) { newY = v; hasMove = true; }
        } else if (t.startsWith("Z")) {
          const v = parseFloat(t.slice(1));
          if (!isNaN(v)) { newZ = v; hasMove = true; }
        }
      }

      if (hasMove) {
        segments.push({
          type: curMotion === "G0" ? "rapid" : "feed",
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

  drawGCodeToolpath(ctx) {
    if (!this.gcodeToolpath || this.gcodeToolpath.length === 0) return;

    // 1. Draw Rapid Moves (G0) in dashed pink/red
    ctx.beginPath();
    ctx.strokeStyle = "rgba(244, 63, 94, 0.75)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 3]);

    for (let seg of this.gcodeToolpath) {
      if (seg.type === "rapid") {
        const p1 = this.toScreen(seg.x1, seg.y1);
        const p2 = this.toScreen(seg.x2, seg.y2);
        if (Math.hypot(p2.x - p1.x, p2.y - p1.y) > 0.5) {
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
        }
      }
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // 2. Draw Cutting Feed Moves (G1) in vibrant solid cyan
    const tipWidth = this.engraving?.tipWidth || this.toolDiameter || 0.20;
    const strokeWidthPx = Math.max(1.8, Math.min(5, tipWidth * this.scale * 1.5));
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = strokeWidthPx;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();

    for (let seg of this.gcodeToolpath) {
      if (seg.type === "feed") {
        const p1 = this.toScreen(seg.x1, seg.y1);
        const p2 = this.toScreen(seg.x2, seg.y2);
        if (Math.hypot(p2.x - p1.x, p2.y - p1.y) > 0.1) {
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
        }
      }
    }
    ctx.stroke();

    // 3. Draw Plunge Points (green) & Retract Points (amber)
    for (let seg of this.gcodeToolpath) {
      if (seg.type === "feed" && seg.z1 > 0 && seg.z2 <= 0) {
        const p = this.toScreen(seg.x2, seg.y2);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.5, 0, 2 * Math.PI);
        ctx.fillStyle = "#10b981";
        ctx.fill();
      } else if (seg.type === "rapid" && seg.z1 <= 0 && seg.z2 > 0) {
        const p = this.toScreen(seg.x1, seg.y1);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.5, 0, 2 * Math.PI);
        ctx.fillStyle = "#f59e0b";
        ctx.fill();
      }
    }
  }

  drawGrid(ctx) {
    const gridSpacing = 50 * this.scale;
    if (gridSpacing < 8) return;

    ctx.strokeStyle = "rgba(51, 65, 85, 0.4)";
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
}

// Global Glyph Cache & Fallbacks
ToolpathVisualizer.FONT_GLYPHS = null;
ToolpathVisualizer.initGlyphs = async function() {
  try {
    const res = await fetch("/api/generate/engraving/glyphs");
    if (res.ok) {
      const data = await res.json();
      if (data && data.fonts) {
        ToolpathVisualizer.FONT_GLYPHS = data.fonts;
      }
    }
  } catch (err) {
    console.warn("Could not fetch remote glyph tables, using fallback:", err);
  }
};

// Start fetching glyph tables immediately
if (typeof window !== "undefined") {
  ToolpathVisualizer.initGlyphs();
}

ToolpathVisualizer.FALLBACK_SIMPLEX = {
  " ": { w: 4.0, strokes: [] },
  "!": { w: 2.5, strokes: [[[1.25, 10.0], [1.25, 3.0]], [[1.25, 1.0], [1.25, 0.0]]] },
  "0": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [5.0, 10.0], [5.0, 0.0], [1.0, 0.0], [5.0, 10.0]]] },
  "1": { w: 4.5, strokes: [[[1.0, 7.5], [2.5, 10.0], [2.5, 0.0]], [[1.0, 0.0], [4.0, 0.0]]] },
  "2": { w: 6.0, strokes: [[[1.0, 8.0], [2.0, 10.0], [4.5, 10.0], [5.5, 8.0], [5.5, 6.0], [1.0, 0.0], [5.5, 0.0]]] },
  "3": { w: 6.0, strokes: [[[1.0, 8.5], [2.0, 10.0], [4.5, 10.0], [5.5, 8.5], [5.5, 6.0], [3.0, 5.0], [5.5, 4.0], [5.5, 1.5], [4.5, 0.0], [2.0, 0.0], [1.0, 1.5]]] },
  "4": { w: 6.0, strokes: [[[4.5, 0.0], [4.5, 10.0], [1.0, 3.0], [5.5, 3.0]]] },
  "5": { w: 6.0, strokes: [[[5.5, 10.0], [1.0, 10.0], [1.0, 5.5], [4.5, 5.5], [5.5, 4.0], [5.5, 1.5], [4.5, 0.0], [2.0, 0.0], [1.0, 1.5]]] },
  "6": { w: 6.0, strokes: [[[5.0, 8.5], [3.0, 10.0], [1.0, 7.0], [1.0, 2.0], [2.5, 0.0], [4.5, 0.0], [5.5, 1.5], [5.5, 4.0], [4.0, 5.5], [1.0, 5.5]]] },
  "7": { w: 6.0, strokes: [[[1.0, 10.0], [5.5, 10.0], [2.5, 0.0]]] },
  "8": { w: 6.0, strokes: [[[2.5, 10.0], [1.0, 8.0], [1.0, 6.5], [2.5, 5.0], [4.5, 5.0], [5.5, 6.5], [5.5, 8.0], [4.0, 10.0], [2.5, 10.0], [2.5, 5.0], [1.0, 3.5], [1.0, 1.5], [2.5, 0.0], [4.5, 0.0], [5.5, 1.5], [5.5, 3.5], [4.5, 5.0]]] },
  "9": { w: 6.0, strokes: [[[5.0, 4.5], [2.0, 4.5], [1.0, 6.0], [1.0, 8.5], [2.5, 10.0], [4.5, 10.0], [5.5, 8.0], [5.5, 3.0], [3.5, 0.0], [1.5, 1.5]]] },
  "A": { w: 6.5, strokes: [[[0.5, 0.0], [3.25, 10.0], [6.0, 0.0]], [[1.7, 4.0], [4.8, 4.0]]] },
  "B": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.5, 10.0], [5.5, 8.5], [5.5, 6.5], [4.5, 5.0], [1.0, 5.0]], [[4.5, 5.0], [5.5, 3.5], [5.5, 1.5], [4.5, 0.0], [1.0, 0.0]]] },
  "C": { w: 6.5, strokes: [[[5.5, 8.0], [4.0, 10.0], [2.0, 10.0], [0.5, 7.5], [0.5, 2.5], [2.0, 0.0], [4.0, 0.0], [5.5, 2.0]]] },
  "D": { w: 6.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.0, 10.0], [6.0, 7.5], [6.0, 2.5], [4.0, 0.0], [1.0, 0.0]]] },
  "E": { w: 5.5, strokes: [[[5.0, 10.0], [1.0, 10.0], [1.0, 0.0], [5.0, 0.0]], [[1.0, 5.0], [4.0, 5.0]]] },
  "F": { w: 5.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [5.0, 10.0]], [[1.0, 5.0], [4.0, 5.0]]] },
  "G": { w: 6.5, strokes: [[[5.5, 8.0], [4.0, 10.0], [2.0, 10.0], [0.5, 7.5], [0.5, 2.5], [2.0, 0.0], [4.5, 0.0], [6.0, 1.5], [6.0, 5.0], [3.5, 5.0]]] },
  "H": { w: 6.5, strokes: [[[1.0, 10.0], [1.0, 0.0]], [[5.5, 10.0], [5.5, 0.0]], [[1.0, 5.0], [5.5, 5.0]]] },
  "I": { w: 3.0, strokes: [[[1.5, 10.0], [1.5, 0.0]], [[0.5, 10.0], [2.5, 10.0]], [[0.5, 0.0], [2.5, 0.0]]] },
  "J": { w: 4.5, strokes: [[[3.5, 10.0], [3.5, 2.5], [2.5, 0.0], [1.0, 0.0], [0.5, 1.5]]] },
  "K": { w: 6.0, strokes: [[[1.0, 10.0], [1.0, 0.0]], [[5.0, 10.0], [1.0, 4.0]], [[2.5, 5.5], [5.5, 0.0]]] },
  "L": { w: 5.0, strokes: [[[1.0, 10.0], [1.0, 0.0], [4.5, 0.0]]] },
  "M": { w: 7.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [3.75, 0.0], [6.5, 10.0], [6.5, 0.0]]] },
  "N": { w: 6.5, strokes: [[[1.0, 0.0], [1.0, 10.0], [5.5, 0.0], [5.5, 10.0]]] },
  "O": { w: 6.5, strokes: [[[2.0, 0.0], [0.5, 2.5], [0.5, 7.5], [2.0, 10.0], [4.5, 10.0], [6.0, 7.5], [6.0, 2.5], [4.5, 0.0], [2.0, 0.0]]] },
  "P": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.5, 10.0], [5.5, 8.5], [5.5, 6.5], [4.5, 5.0], [1.0, 5.0]]] },
  "Q": { w: 6.5, strokes: [[[2.0, 0.0], [0.5, 2.5], [0.5, 7.5], [2.0, 10.0], [4.5, 10.0], [6.0, 7.5], [6.0, 2.5], [4.5, 0.0], [2.0, 0.0]], [[4.0, 2.0], [6.5, -1.0]]] },
  "R": { w: 6.0, strokes: [[[1.0, 0.0], [1.0, 10.0], [4.5, 10.0], [5.5, 8.5], [5.5, 6.5], [4.5, 5.0], [1.0, 5.0]], [[3.5, 5.0], [5.5, 0.0]]] },
  "S": { w: 6.0, strokes: [[[5.0, 8.5], [4.0, 10.0], [2.0, 10.0], [0.5, 8.5], [0.5, 6.5], [2.0, 5.0], [4.0, 5.0], [5.5, 3.5], [5.5, 1.5], [4.0, 0.0], [2.0, 0.0], [0.5, 1.5]]] },
  "T": { w: 6.0, strokes: [[[0.5, 10.0], [5.5, 10.0]], [[3.0, 10.0], [3.0, 0.0]]] },
  "U": { w: 6.5, strokes: [[[1.0, 10.0], [1.0, 2.5], [2.5, 0.0], [4.5, 0.0], [6.0, 2.5], [6.0, 10.0]]] },
  "V": { w: 6.5, strokes: [[[0.5, 10.0], [3.25, 0.0], [6.0, 10.0]]] },
  "W": { w: 8.5, strokes: [[[0.5, 10.0], [2.5, 0.0], [4.25, 7.0], [6.0, 0.0], [8.0, 10.0]]] },
  "X": { w: 6.0, strokes: [[[0.5, 10.0], [5.5, 0.0]], [[5.5, 10.0], [0.5, 0.0]]] },
  "Y": { w: 6.0, strokes: [[[0.5, 10.0], [3.0, 5.0], [5.5, 10.0]], [[3.0, 5.0], [3.0, 0.0]]] },
  "Z": { w: 6.0, strokes: [[[0.5, 10.0], [5.5, 10.0], [0.5, 0.0], [5.5, 0.0]]] },
  "?": { w: 5.5, strokes: [[[1.0, 8.5], [2.0, 10.0], [4.0, 10.0], [5.0, 8.5], [5.0, 6.5], [2.75, 4.5], [2.75, 2.5]], [[2.75, 1.0], [2.75, 0.0]]] },
  "-": { w: 4.5, strokes: [[[0.5, 5.0], [4.0, 5.0]]] },
  ".": { w: 2.5, strokes: [[[1.25, 1.0], [1.25, 0.0]]] },
};

