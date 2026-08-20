document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("probingModal");
  const openBtn = document.getElementById("openProbingModalBtn");
  const closeBtn = document.getElementById("closeProbingModalBtn");

  if (!modal || !openBtn) return;

  const tabs = modal.querySelectorAll(".pattern-tab");
  const panes = modal.querySelectorAll(".ptab-pane");

  const zProbeThickness = document.getElementById("zProbeThickness");
  const zProbeRetract = document.getElementById("zProbeRetract");
  const zProbeFastFeed = document.getElementById("zProbeFastFeed");
  const zProbeSlowFeed = document.getElementById("zProbeSlowFeed");
  const btnGenZProbe = document.getElementById("btnGenZProbe");

  const cornerToolDia = document.getElementById("cornerToolDia");
  const cornerPlateZ = document.getElementById("cornerPlateZ");
  const cornerLipX = document.getElementById("cornerLipX");
  const cornerLipY = document.getElementById("cornerLipY");
  const btnGenCornerProbe = document.getElementById("btnGenCornerProbe");

  const btnGenHoming = document.getElementById("btnGenHoming");

  const macroOutput = document.getElementById("probeMacroOutput");
  const copyBtn = document.getElementById("copyProbeMacroBtn");
  const downloadBtn = document.getElementById("downloadProbeMacroBtn");

  let currentMacroGCode = "";
  let currentMacroFilename = "z_probe_macro.nc";

  // Tab switching
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.ptab;

      panes.forEach((p) => (p.style.display = "none"));
      if (target === "zprobe") document.getElementById("ptabContentZProbe").style.display = "block";
      else if (target === "corner") document.getElementById("ptabContentCorner").style.display = "block";
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
