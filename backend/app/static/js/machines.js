/**
 * Machine Profiles Manager
 */
document.addEventListener("DOMContentLoaded", async () => {
  const machinesList = document.getElementById("machinesList");
  const newMachineForm = document.getElementById("newMachineForm");
  const saveMachineBtn = document.getElementById("saveMachineBtn");
  const cancelEditBtn = document.getElementById("cancelEditBtn");
  const formTitle = document.getElementById("formTitle");
  const editMachineIdInput = document.getElementById("editMachineId");
  const machineFormCard = document.getElementById("machineFormCard");

  const spindleTypeSelect = document.getElementById("spindleType");
  const routerModelRow = document.getElementById("routerModelRow");

  let machinesCache = [];

  function resetForm() {
    newMachineForm.reset();
    editMachineIdInput.value = "";
    formTitle.textContent = "Add New Machine Profile";
    saveMachineBtn.textContent = "➕ Save Machine Profile";
    cancelEditBtn.style.display = "none";
    if (routerModelRow) {
      routerModelRow.style.display = "flex";
    }
  }

  async function loadMachines() {
    try {
      machinesCache = await API.getMachines();
      machinesList.innerHTML = "";

      machinesCache.forEach((m) => {
        const card = document.createElement("div");
        card.className = "card";
        const spindleDesc = m.spindle_type === "router"
          ? `DeWalt/Trim Router (${m.router_model || "Manual Dial"}) [${m.min_spindle_rpm}-${m.max_spindle_rpm} RPM]`
          : `VFD/PWM Spindle [${m.min_spindle_rpm}-${m.max_spindle_rpm} RPM]`;

        card.innerHTML = `
          <div class="card-title">
            <span>${m.name}</span>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              ${
                m.is_active
                  ? '<span class="badge badge-active">Active Machine</span>'
                  : `<button class="btn btn-secondary btn-sm" onclick="activateMachineProfile(${m.id})">Set Active</button>`
              }
              <button class="btn btn-secondary btn-sm" onclick="editMachineProfile(${m.id})">✏️ Edit</button>
            </div>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
            <strong>Dialect:</strong> ${m.controller_dialect.toUpperCase()} | 
            <strong>Spindle:</strong> ${spindleDesc} |
            <strong>Work Envelope:</strong> ${m.work_area_x} x ${m.work_area_y} x ${m.work_area_z} mm | 
            <strong>Rapid Rate:</strong> ${m.rapid_feed_rate} mm/min |
            <strong>Probe Thickness:</strong> ${m.z_probe_thickness} mm |
            <strong>Safe Retract:</strong> ${m.safe_z_retract} mm
          </div>
          <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.75rem;">
            ${m.notes || "No notes"}
          </div>
          <div>
            ${
              !m.is_active
                ? `<button class="btn btn-secondary btn-sm" style="color: var(--accent-red);" onclick="deleteMachineProfile(${m.id})">Delete</button>`
                : ""
            }
          </div>
        `;
        machinesList.appendChild(card);
      });
    } catch (err) {
      console.error("Failed to load machines:", err);
    }
  }

  // Toggle router model visibility on spindle type change
  spindleTypeSelect?.addEventListener("change", () => {
    if (routerModelRow) {
      routerModelRow.style.display = spindleTypeSelect.value === "router" ? "flex" : "none";
    }
  });

  window.editMachineProfile = (id) => {
    const machine = machinesCache.find((m) => m.id === id);
    if (!machine) return;

    editMachineIdInput.value = machine.id;
    document.getElementById("machineName").value = machine.name || "";
    document.getElementById("machineDialect").value = machine.controller_dialect || "grbl";
    document.getElementById("spindleType").value = machine.spindle_type || "router";
    
    if (routerModelRow) {
      routerModelRow.style.display = machine.spindle_type === "router" ? "flex" : "none";
    }
    if (machine.router_model) {
      document.getElementById("routerModel").value = machine.router_model;
    }

    document.getElementById("workX").value = machine.work_area_x;
    document.getElementById("workY").value = machine.work_area_y;
    document.getElementById("workZ").value = machine.work_area_z;
    document.getElementById("rapidRate").value = machine.rapid_feed_rate;
    document.getElementById("safeZ").value = machine.safe_z_retract;
    document.getElementById("probeThick").value = machine.z_probe_thickness;
    document.getElementById("machineNotes").value = machine.notes || "";

    formTitle.textContent = `Edit Profile: ${machine.name}`;
    saveMachineBtn.textContent = "💾 Update Profile";
    cancelEditBtn.style.display = "block";

    machineFormCard.scrollIntoView({ behavior: "smooth" });
  };

  cancelEditBtn?.addEventListener("click", () => {
    resetForm();
  });

  window.activateMachineProfile = async (id) => {
    try {
      await API.activateMachine(id);
      await loadMachines();
    } catch (err) {
      alert("Error activating machine: " + err.message);
    }
  };

  window.deleteMachineProfile = async (id) => {
    if (!confirm("Are you sure you want to delete this machine profile?")) return;
    try {
      await API.deleteMachine(id);
      await loadMachines();
    } catch (err) {
      alert("Error deleting machine: " + err.message);
    }
  };

  saveMachineBtn?.addEventListener("click", async () => {
    const editId = editMachineIdInput.value ? parseInt(editMachineIdInput.value, 10) : null;
    const spindleType = document.getElementById("spindleType").value || "router";
    const routerModel = spindleType === "router" ? (document.getElementById("routerModel").value || "dewalt_611") : null;
    const minRpm = spindleType === "router" ? (routerModel === "dewalt_611" ? 16000 : 10000) : 6000;
    const maxRpm = spindleType === "router" ? (routerModel === "dewalt_611" ? 27000 : 30000) : 24000;

    const payload = {
      name: document.getElementById("machineName").value,
      controller_dialect: document.getElementById("machineDialect").value || "grbl",
      spindle_type: spindleType,
      router_model: routerModel,
      min_spindle_rpm: minRpm,
      max_spindle_rpm: maxRpm,
      work_area_x: parseFloat(document.getElementById("workX").value) || 750,
      work_area_y: parseFloat(document.getElementById("workY").value) || 750,
      work_area_z: parseFloat(document.getElementById("workZ").value) || 65,
      rapid_feed_rate: parseFloat(document.getElementById("rapidRate").value) || 5000,
      safe_z_retract: parseFloat(document.getElementById("safeZ").value) || 5,
      z_probe_thickness: parseFloat(document.getElementById("probeThick").value) || 14.85,
      notes: document.getElementById("machineNotes").value,
    };

    if (!payload.name) {
      alert("Please specify a machine name.");
      return;
    }

    try {
      if (editId) {
        await API.updateMachine(editId, payload);
      } else {
        payload.is_active = false;
        await API.createMachine(payload);
      }
      resetForm();
      await loadMachines();
    } catch (err) {
      alert("Failed to save machine profile: " + err.message);
    }
  });

  await loadMachines();
});
