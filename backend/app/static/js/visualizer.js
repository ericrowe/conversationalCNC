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
      if (data.threadType !== undefined) this.threadType = data.threadType;
      if (data.surfacing !== undefined) this.surfacing = data.surfacing;
      if (data.engraving !== undefined) this.engraving = data.engraving;
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

    // Operation-specific Rendering
    if (this.opType === "surfacing" && this.surfacing) {
      this.drawSurfacing(ctx);
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

  drawEngraving(ctx) {
    const e = this.engraving;
    if (!e || !e.text) return;

    const fontSizePx = Math.max(8, e.fontSize * this.scale);
    let fontFamily = "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace";
    let fontWeight = "600";

    if (e.fontName === "roman_serif") {
      fontFamily = '"Times New Roman", Times, Georgia, serif';
      fontWeight = "500";
    } else if (e.fontName === "cursive_script") {
      fontFamily = '"Brush Script MT", "Segoe Script", "Apple Chancery", cursive';
      fontWeight = "normal";
    } else if (e.fontName === "block_stencil") {
      fontFamily = '"Impact", "Arial Black", sans-serif';
      fontWeight = "bold";
    } else if (e.fontName === "duplex_sans") {
      fontFamily = "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace";
      fontWeight = "900";
    }

    ctx.font = `${fontWeight} ${fontSizePx}px ${fontFamily}`;
    ctx.fillStyle = "#38bdf8";
    ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
    ctx.lineWidth = e.fontName === "duplex_sans" ? 2.5 : 1.5;


    if (e.layoutMode === "arc") {
      // Arc / Circular preview
      const center = this.toScreen(e.centerX, e.centerY);
      const radiusPx = e.arcRadius * this.scale;

      // Draw dashed pitch circle
      ctx.beginPath();
      ctx.arc(center.x, center.y, radiusPx, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(148, 163, 184, 0.4)";
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw Center Crosshair
      ctx.beginPath();
      ctx.arc(center.x, center.y, 3, 0, 2 * Math.PI);
      ctx.fillStyle = "#f59e0b";
      ctx.fill();

      // Render curved characters
      const str = e.text.replace(/\n/g, " ").trim();
      const numChars = str.length;
      if (numChars === 0) return;

      const approxCharWidth = (e.fontSize * 0.6 + (e.letterSpacing || 1.0)) * this.scale;
      const totalArcLength = approxCharWidth * numChars;
      const totalAngle = totalArcLength / radiusPx;
      const isCw = e.arcDirection === "clockwise";

      let baseAngle = (e.startAngleDeg * Math.PI) / 180.0;
      if (e.align === "center") {
        baseAngle += isCw ? totalAngle / 2.0 : -totalAngle / 2.0;
      }

      ctx.save();
      for (let i = 0; i < numChars; i++) {
        const char = str[i];
        const distAlongArc = (i * approxCharWidth) + (approxCharWidth / 2.0);
        const charAngle = isCw
          ? baseAngle - (distAlongArc / radiusPx)
          : baseAngle + (distAlongArc / radiusPx);

        const charX = center.x + radiusPx * Math.cos(charAngle);
        const charY = center.y - radiusPx * Math.sin(charAngle); // Flip Y for canvas screen space

        ctx.save();
        ctx.translate(charX, charY);
        // Correct rotation angle so letters are right-side up and read left-to-right along the arc
        const rotAngle = isCw
          ? -charAngle + (Math.PI / 2)
          : -charAngle + (3 * Math.PI / 2);
        ctx.rotate(rotAngle);
        ctx.textAlign = "center";
        ctx.textBaseline = isCw ? "bottom" : "top";
        ctx.fillText(char, 0, 0);
        ctx.restore();
      }
      ctx.restore();


      ctx.fillStyle = "#94a3b8";
      ctx.font = "11px sans-serif";
      ctx.fillText(`R${e.arcRadius}mm`, center.x + 8, center.y - radiusPx - 6);

    } else {
      // Linear layout preview
      const start = this.toScreen(e.startX, e.startY);

      // Start coordinate point
      ctx.beginPath();
      ctx.arc(start.x, start.y, 3.5, 0, 2 * Math.PI);
      ctx.fillStyle = "#10b981";
      ctx.fill();

      ctx.save();
      ctx.translate(start.x, start.y);
      const rotRad = -((e.rotationDeg || 0.0) * Math.PI) / 180.0;
      ctx.rotate(rotRad);

      ctx.textAlign = e.align || "left";
      ctx.textBaseline = "bottom";

      const lines = e.text.split("\n");
      const lineStep = (e.fontSize * (e.lineSpacingMult || 1.4)) * this.scale;

      lines.forEach((line, idx) => {
        ctx.fillText(line, 0, idx * lineStep);
      });

      ctx.restore();

      ctx.fillStyle = "#94a3b8";
      ctx.font = "11px sans-serif";
      ctx.fillText(`Origin (${e.startX}, ${e.startY})`, start.x + 6, start.y - 6);
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
