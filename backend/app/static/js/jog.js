document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("jogModal");
  const openBtn = document.getElementById("openJogModalBtn");
  const closeBtn = document.getElementById("closeJogModalBtn");

  if (!modal || !openBtn) return;

  // DRO elements
  const droPosX = document.getElementById("droPosX");
  const droPosY = document.getElementById("droPosY");
  const droPosZ = document.getElementById("droPosZ");
  const jogStatusBadge = document.getElementById("jogStatusBadge");
  const jogLastCmd = document.getElementById("jogLastCmd");

  // Setting elements
  const stepButtons = modal.querySelectorAll(".step-btn");
  const feedSlider = document.getElementById("jogFeedSlider");
  const feedLabel = document.getElementById("jogFeedLabel");

  // Zero & Origin buttons
  const btnZeroAllWcs = document.getElementById("btnZeroAllWcs");
  const btnZeroZOnly = document.getElementById("btnZeroZOnly");
  const btnZeroXYCenter = document.getElementById("btnZeroXYCenter");
  const btnGotoOrigin = document.getElementById("btnGotoOrigin");

  // Spindle elements
  const btnToggleSpindle = document.getElementById("btnToggleSpindle");
  const jogSpindleRpm = document.getElementById("jogSpindleRpm");

  // State
  let currentStep = 10.0;
  let currentFeed = 1200.0;
  let currentX = 0.0;
  let currentY = 0.0;
  let currentZ = 0.0;
  let spindleOn = false;

  function updateDRO() {
    droPosX.textContent = currentX.toFixed(3);
    droPosY.textContent = currentY.toFixed(3);
    droPosZ.textContent = currentZ.toFixed(3);
  }

  function setStatus(statusText, isJogging = false) {
    if (isJogging) {
      jogStatusBadge.textContent = "JOGGING...";
      jogStatusBadge.style.background = "rgba(56, 189, 248, 0.2)";
      jogStatusBadge.style.color = "#38bdf8";
      jogStatusBadge.style.borderColor = "#38bdf8";
    } else {
      jogStatusBadge.textContent = statusText || "IDLE (G54)";
      jogStatusBadge.style.background = "rgba(16, 185, 129, 0.2)";
      jogStatusBadge.style.color = "#10b981";
      jogStatusBadge.style.borderColor = "#10b981";
    }
  }

  // Step button selection
  stepButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      stepButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentStep = parseFloat(btn.dataset.step) || 10.0;
    });
  });

  // Feed slider
  feedSlider.addEventListener("input", () => {
    currentFeed = parseFloat(feedSlider.value) || 1200.0;
    feedLabel.textContent = `${currentFeed} mm/min`;
  });

  // Modal open / close
  openBtn.addEventListener("click", () => {
    modal.style.display = "flex";
  });

  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });

  // Execute Jog Step
  async function doJog(axis, dirMultiplier = 1, customStep = null) {
    const dist = (customStep !== null ? customStep : currentStep) * dirMultiplier;
    setStatus("JOGGING...", true);

    try {
      const res = await API.jogStep({
        axis: axis,
        distance: dist,
        feed_rate: currentFeed,
        units: "mm",
      });

      if (res && res.data) {
        jogLastCmd.textContent = res.data.gcode;

        // Update simulated DRO
        if (axis === "X") currentX += dist;
        else if (axis === "Y") currentY += dist;
        else if (axis === "Z") currentZ += dist;
        else if (axis === "XY") { currentX += Math.abs(dist); currentY += Math.abs(dist); }
        else if (axis === "-XY") { currentX -= Math.abs(dist); currentY += Math.abs(dist); }
        else if (axis === "X-Y") { currentX += Math.abs(dist); currentY -= Math.abs(dist); }
        else if (axis === "-X-Y") { currentX -= Math.abs(dist); currentY -= Math.abs(dist); }
        updateDRO();
      }
    } catch (err) {
      jogLastCmd.textContent = `Error: ${err.message}`;
    } finally {
      setTimeout(() => setStatus("IDLE (G54)", false), 350);
    }
  }

  // Wire up Jog Buttons
  const jogButtons = modal.querySelectorAll(".jog-btn");
  jogButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const axis = btn.dataset.axis;
      const dir = parseFloat(btn.dataset.dir) || 1;
      doJog(axis, dir);
    });
  });

  // Zero Actions
  btnZeroAllWcs.addEventListener("click", async () => {
    try {
      const res = await API.jogZero({ axes: ["X", "Y", "Z"], wcs_slot: 1 });
      currentX = 0.0;
      currentY = 0.0;
      currentZ = 0.0;
      updateDRO();
      jogLastCmd.textContent = res.data.gcode;
    } catch (e) {
      alert("Zero failed: " + e.message);
    }
  });

  btnZeroZOnly.addEventListener("click", async () => {
    try {
      const res = await API.jogZero({ axes: ["Z"], wcs_slot: 1 });
      currentZ = 0.0;
      updateDRO();
      jogLastCmd.textContent = res.data.gcode;
    } catch (e) {
      alert("Zero Z failed: " + e.message);
    }
  });

  btnZeroXYCenter.addEventListener("click", async () => {
    try {
      const res = await API.jogZero({ axes: ["X", "Y"], wcs_slot: 1 });
      currentX = 0.0;
      currentY = 0.0;
      updateDRO();
      jogLastCmd.textContent = res.data.gcode;
    } catch (e) {
      alert("Zero XY failed: " + e.message);
    }
  });

  btnGotoOrigin.addEventListener("click", async () => {
    try {
      const res = await API.jogGotoOrigin({ safe_z_retract: 5.0, units: "mm" });
      currentX = 0.0;
      currentY = 0.0;
      currentZ = 5.0;
      updateDRO();
      jogLastCmd.textContent = res.data.gcode.replace(/\n/g, " | ");
    } catch (e) {
      alert("Go to origin failed: " + e.message);
    }
  });

  // Spindle Toggle
  btnToggleSpindle.addEventListener("click", async () => {
    spindleOn = !spindleOn;
    const rpm = parseInt(jogSpindleRpm.value, 10) || 16000;

    try {
      const res = await API.jogSpindle({ state: spindleOn, rpm: rpm, clockwise: true });
      jogLastCmd.textContent = res.data.gcode;

      if (spindleOn) {
        btnToggleSpindle.textContent = `⚡ Spindle: ON (${rpm} RPM)`;
        btnToggleSpindle.classList.add("btn-danger");
        btnToggleSpindle.classList.remove("btn-secondary");
      } else {
        btnToggleSpindle.textContent = `⚡ Spindle: OFF`;
        btnToggleSpindle.classList.remove("btn-danger");
        btnToggleSpindle.classList.add("btn-secondary");
      }
    } catch (e) {
      alert("Spindle control failed: " + e.message);
      spindleOn = !spindleOn;
    }
  });

  // Global Keyboard Navigation
  window.addEventListener("keydown", (e) => {
    // Open modal on 'J' if not in an input field
    if ((e.key === "j" || e.key === "J") && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      if (modal.style.display !== "flex") {
        e.preventDefault();
        modal.style.display = "flex";
        return;
      }
    }

    if (modal.style.display !== "flex") return;
    if (document.activeElement.tagName === "INPUT") return;

    let stepToUse = currentStep;
    if (e.shiftKey) stepToUse *= 5.0;

    if (e.key === "ArrowLeft") {
      e.preventDefault();
      doJog("X", -1, stepToUse);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      doJog("X", 1, stepToUse);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      doJog("Y", 1, stepToUse);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      doJog("Y", -1, stepToUse);
    } else if (e.key === "PageUp") {
      e.preventDefault();
      doJog("Z", 1, stepToUse);
    } else if (e.key === "PageDown") {
      e.preventDefault();
      doJog("Z", -1, stepToUse);
    } else if (e.key === "Escape") {
      modal.style.display = "none";
    }
  });
});
