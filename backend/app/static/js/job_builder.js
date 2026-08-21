/**
 * Multi-Operation Job Program Sequencer / Builder Client Controller
 */
document.addEventListener("DOMContentLoaded", () => {
  const drawer = document.getElementById("jobBuilderDrawer");
  const openBtn = document.getElementById("openJobDrawerBtn");
  const closeBtn = document.getElementById("closeJobDrawerBtn");
  const navCountBadge = document.getElementById("navJobQueueCount");

  const jobQueueList = document.getElementById("jobQueueList");
  const jobQueueEmptyState = document.getElementById("jobQueueEmptyState");
  const jobQueueHeaderCount = document.getElementById("jobQueueHeaderCount");
  const btnClearJobQueue = document.getElementById("btnClearJobQueue");

  const jobProgramName = document.getElementById("jobProgramName");
  const jobSafeZ = document.getElementById("jobSafeZ");
  const jobOptimizeTools = document.getElementById("jobOptimizeTools");

  // Mesh Leveling Controls
  const jobApplyMeshLeveling = document.getElementById("jobApplyMeshLeveling");
  const jobOpenMeshModalBtn = document.getElementById("jobOpenMeshModalBtn");
  const jobMeshStatusBadge = document.getElementById("jobMeshStatusBadge");

  const btnGenerateFullJob = document.getElementById("btnGenerateFullJob");
  const btnCopyJobGcode = document.getElementById("btnCopyJobGcode");
  const btnDownloadJobGcode = document.getElementById("btnDownloadJobGcode");

  const jobOutputContainer = document.getElementById("jobOutputContainer");
  const jobGcodeOutput = document.getElementById("jobGcodeOutput");
  const jobStatLines = document.getElementById("jobStatLines");
  const jobStatToolChanges = document.getElementById("jobStatToolChanges");
  const jobStatTools = document.getElementById("jobStatTools");

  const STORAGE_KEY = "conversational_cnc_job_queue";
  const MESH_STORAGE_KEY = "conversational_cnc_active_mesh";

  function getQueue() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch (e) {
      return [];
    }
  }

  function saveQueue(queue) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    renderQueue();
  }

  function getActiveMesh() {
    try {
      return JSON.parse(localStorage.getItem(MESH_STORAGE_KEY)) || null;
    } catch (e) {
      return null;
    }
  }

  function updateMeshStatusUI() {
    const mesh = getActiveMesh();
    if (!jobMeshStatusBadge) return;

    if (mesh && mesh.points && mesh.points.length > 0) {
      const activeCount = mesh.points.filter(p => p.active !== false).length;
      const zs = mesh.points.map(p => p.z || 0.0);
      const minZ = Math.min(...zs).toFixed(2);
      const maxZ = Math.max(...zs).toFixed(2);
      const shape = (mesh.shape_type || "Rectangle").toUpperCase();

      jobMeshStatusBadge.innerHTML = `🟢 <strong>${shape} Mesh Active:</strong> ${activeCount} pts (ΔZ: ${minZ > 0 ? "+" : ""}${minZ}mm to ${maxZ > 0 ? "+" : ""}${maxZ}mm)`;
      jobMeshStatusBadge.style.color = "#34d399";
    } else {
      jobMeshStatusBadge.innerHTML = `○ No Active Mesh. Click "Mesh Mapper" to sample or configure.`;
      jobMeshStatusBadge.style.color = "#94a3b8";
    }
  }

  window.addEventListener("mesh-updated", () => {
    updateMeshStatusUI();
  });

  if (jobOpenMeshModalBtn) {
    jobOpenMeshModalBtn.addEventListener("click", () => {
      const probeModal = document.getElementById("probingModal");
      if (probeModal) {
        probeModal.style.display = "flex";
        const meshTab = probeModal.querySelector('.pattern-tab[data-ptab="mesh"]');
        if (meshTab) meshTab.click();
      }
    });
  }

  function updateBadgeCounts(count) {
    if (navCountBadge) {
      navCountBadge.textContent = count;
      navCountBadge.style.display = count > 0 ? "inline-block" : "none";
    }
    if (jobQueueHeaderCount) {
      jobQueueHeaderCount.textContent = `${count} Op${count === 1 ? "" : "s"}`;
    }
  }

  function renderQueue() {
    const queue = getQueue();
    updateBadgeCounts(queue.length);
    updateMeshStatusUI();

    if (queue.length === 0) {
      jobQueueEmptyState.style.display = "block";
      jobQueueList.innerHTML = "";
      btnGenerateFullJob.disabled = true;
      return;
    }

    jobQueueEmptyState.style.display = "none";
    btnGenerateFullJob.disabled = false;
    jobQueueList.innerHTML = "";

    queue.forEach((op, index) => {
      const item = document.createElement("div");
      item.className = "card";
      item.style.padding = "0.6rem 0.75rem";
      item.style.background = "#0f172a";
      item.style.border = "1px solid #1e293b";
      item.style.display = "flex";
      item.style.alignItems = "center";
      item.style.justifyContent = "space-between";
      item.style.gap = "0.5rem";

      const opType = (op.op_type || "drilling").toUpperCase();
      const tNum = op.tool_number || 1;
      const tName = op.tool_name || `Tool T${tNum}`;
      const tDia = op.tool_diameter ? `${op.tool_diameter}mm` : "";

      item.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 0.2rem; flex: 1;">
          <div style="font-size: 0.85rem; font-weight: 600; color: #f8fafc; display: flex; align-items: center; gap: 0.4rem;">
            <span style="color: #38bdf8;">${index + 1}.</span>
            <span>${op.op_name || "Operation"}</span>
            <span class="badge" style="font-size: 0.65rem; background: #334155; color: #94a3b8; padding: 0.1rem 0.35rem;">${opType}</span>
          </div>
          <div style="font-size: 0.7rem; color: #64748b;">
            <span>🔧 T${tNum} (${tName} ${tDia})</span> | <span>⚡ ${op.spindle_speed || 16000} RPM</span>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.25rem;">
          <button type="button" class="btn btn-secondary btn-sm btn-move-up" data-idx="${index}" title="Move Up" ${index === 0 ? "disabled" : ""} style="padding: 0.15rem 0.4rem; font-size: 0.7rem;">▲</button>
          <button type="button" class="btn btn-secondary btn-sm btn-move-dn" data-idx="${index}" title="Move Down" ${index === queue.length - 1 ? "disabled" : ""} style="padding: 0.15rem 0.4rem; font-size: 0.7rem;">▼</button>
          <button type="button" class="btn btn-secondary btn-sm btn-del-op" data-idx="${index}" title="Remove Operation" style="padding: 0.15rem 0.4rem; font-size: 0.7rem; color: #ef4444;">✕</button>
        </div>
      `;
      jobQueueList.appendChild(item);
    });

    // Wire reorder & delete buttons
    jobQueueList.querySelectorAll(".btn-move-up").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.idx, 10);
        if (idx > 0) {
          const q = getQueue();
          const temp = q[idx];
          q[idx] = q[idx - 1];
          q[idx - 1] = temp;
          saveQueue(q);
        }
      });
    });

    jobQueueList.querySelectorAll(".btn-move-dn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.idx, 10);
        const q = getQueue();
        if (idx < q.length - 1) {
          const temp = q[idx];
          q[idx] = q[idx + 1];
          q[idx + 1] = temp;
          saveQueue(q);
        }
      });
    });

    jobQueueList.querySelectorAll(".btn-del-op").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.idx, 10);
        const q = getQueue();
        q.splice(idx, 1);
        saveQueue(q);
      });
    });
  }

  // Open / Close Drawer
  if (openBtn && drawer) {
    openBtn.addEventListener("click", () => {
      drawer.style.display = "flex";
      renderQueue();
    });
  }

  if (closeBtn && drawer) {
    closeBtn.addEventListener("click", () => {
      drawer.style.display = "none";
    });
  }

  window.addEventListener("click", (e) => {
    if (e.target === drawer) drawer.style.display = "none";
  });

  // Clear Queue
  btnClearJobQueue.addEventListener("click", () => {
    if (confirm("Are you sure you want to clear all queued operations?")) {
      saveQueue([]);
      jobOutputContainer.style.display = "none";
    }
  });

  // Generate Full Program
  btnGenerateFullJob.addEventListener("click", async () => {
    const queue = getQueue();
    if (queue.length === 0) return;

    btnGenerateFullJob.disabled = true;
    btnGenerateFullJob.textContent = "Generating Full Program...";

    try {
      const activeMesh = getActiveMesh();
      const payload = {
        job_name: jobProgramName.value.trim() || "Part_Machining_Job",
        operations: queue,
        safe_z_retract: parseFloat(jobSafeZ.value) || 5.0,
        optimize_tool_order: jobOptimizeTools.checked,
        units: "mm",
        apply_mesh_leveling: jobApplyMeshLeveling ? jobApplyMeshLeveling.checked : false,
        mesh_data: activeMesh,
      };

      const res = await API.generateJobSequence(payload);
      if (res && res.data) {
        const data = res.data;
        jobGcodeOutput.value = data.gcode;
        jobStatLines.textContent = `Lines: ${data.line_count}`;
        jobStatToolChanges.textContent = `Tool Changes: ${data.tool_change_count}`;
        jobStatTools.textContent = `Tools: ${data.tools_used.length}`;
        jobOutputContainer.style.display = "block";

        btnCopyJobGcode.disabled = false;
        btnDownloadJobGcode.disabled = false;

        // If Visualizer is on page, render combined toolpath
        if (window.visualizer) {
          window.visualizer.loadGCode(data.gcode);
          if (data.mesh_leveling_applied && activeMesh) {
            window.visualizer.loadSurfaceMesh(activeMesh);
          }
        }
      }
    } catch (err) {
      alert("Job sequence generation error: " + err.message);
    } finally {
      btnGenerateFullJob.disabled = false;
      btnGenerateFullJob.textContent = "⚡ Generate Unified Program (.nc)";
    }
  });

  // Copy Program
  btnCopyJobGcode.addEventListener("click", () => {
    if (!jobGcodeOutput.value) return;
    navigator.clipboard.writeText(jobGcodeOutput.value);
    const orig = btnCopyJobGcode.textContent;
    btnCopyJobGcode.textContent = "✅ Copied!";
    setTimeout(() => (btnCopyJobGcode.textContent = orig), 2000);
  });

  // Download .nc
  btnDownloadJobGcode.addEventListener("click", () => {
    if (!jobGcodeOutput.value) return;
    const blob = new Blob([jobGcodeOutput.value], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${jobProgramName.value.trim() || "Part_Job"}.nc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Public Global API for Operation Pages
  window.JobBuilder = {
    addOperation(op) {
      const queue = getQueue();
      queue.push(op);
      saveQueue(queue);

      // Flash feedback
      if (openBtn) {
        openBtn.classList.add("btn-primary");
        setTimeout(() => openBtn.classList.remove("btn-primary"), 800);
      }
    },
    open() {
      if (drawer) {
        drawer.style.display = "flex";
        renderQueue();
      }
    },
    getActiveMesh,
  };

  // Initial UI sync
  updateMeshStatusUI();
});
