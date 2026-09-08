// Real-Time Server Status & 7" Touchscreen Telemetry Poller
document.addEventListener("DOMContentLoaded", () => {
  let isPolling = false;

  // 1. Live Clock
  function updateClock() {
    const clockEl = document.getElementById("live-clock");
    if (clockEl) {
      const now = new Date();
      clockEl.textContent = now.toTimeString().split(" ")[0];
    }
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 2. Fullscreen Toggle (Edge-to-Edge Kiosk Mode)
  const btnFullscreen = document.getElementById("btn-fullscreen");
  const fsIcon = document.getElementById("fullscreen-icon");
  const fsText = document.getElementById("fullscreen-text");

  function isFullscreen() {
    return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement);
  }

  function updateFullscreenUI() {
    if (isFullscreen()) {
      if (fsIcon) fsIcon.textContent = "✖";
      if (fsText) fsText.textContent = "Exit Full";
      if (btnFullscreen) btnFullscreen.classList.add("hud-btn-active");
    } else {
      if (fsIcon) fsIcon.textContent = "⛶";
      if (fsText) fsText.textContent = "Fullscreen";
      if (btnFullscreen) btnFullscreen.classList.remove("hud-btn-active");
    }
  }

  if (btnFullscreen) {
    btnFullscreen.addEventListener("click", async () => {
      try {
        if (!isFullscreen()) {
          if (document.documentElement.requestFullscreen) {
            await document.documentElement.requestFullscreen();
          } else if (document.documentElement.webkitRequestFullscreen) {
            await document.documentElement.webkitRequestFullscreen();
          }
        } else {
          if (document.exitFullscreen) {
            await document.exitFullscreen();
          } else if (document.webkitExitFullscreen) {
            await document.webkitExitFullscreen();
          }
        }
      } catch (err) {
        console.warn("Fullscreen toggle error:", err);
      }
    });
  }

  document.addEventListener("fullscreenchange", updateFullscreenUI);
  document.addEventListener("webkitfullscreenchange", updateFullscreenUI);

  // 3. Poll System Status
  async function fetchSystemStatus() {
    if (isPolling) return;
    isPolling = true;

    try {
      const res = await fetch("/api/system/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderSystemStatus(data);
    } catch (err) {
      console.warn("Error fetching system status:", err);
      const statusBadge = document.getElementById("service-status");
      if (statusBadge) {
        statusBadge.textContent = "OFFLINE";
        statusBadge.className = "hud-pill";
        statusBadge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
        statusBadge.style.color = "#f87171";
      }
    } finally {
      isPolling = false;
    }
  }

  // 4. Render Status Payload
  function renderSystemStatus(data) {
    // Hostname & Platform
    const hostEl = document.getElementById("host-name");
    const ipEl = document.getElementById("primary-ip");
    const statusBadge = document.getElementById("service-status");

    if (hostEl) hostEl.textContent = data.hostname || "voltron";
    if (ipEl) {
      const ip = data.network?.primary || "127.0.0.1";
      ipEl.textContent = `IP: ${ip}`;
    }
    if (statusBadge) {
      statusBadge.textContent = "ONLINE :80";
      statusBadge.className = "hud-pill hud-pill-online";
    }

    // Hardware Telemetry
    const hw = data.hardware || {};
    
    // Core Temp (Red Lion)
    const tempVal = document.getElementById("temp-val");
    const tempBar = document.getElementById("temp-bar");
    const tempBadge = document.getElementById("temp-badge");
    const temp = hw.cpu_temp_c || 40.0;

    if (tempVal) tempVal.textContent = `${temp.toFixed(1)} °C`;
    if (tempBar) {
      tempBar.style.width = `${Math.min(100, Math.max(10, (temp / 85) * 100))}%`;
      if (temp < 60) {
        tempBar.style.background = "linear-gradient(90deg, #991b1b, #ef4444)";
        if (tempBadge) { tempBadge.textContent = "Normal"; tempBadge.style.color = "#fca5a5"; }
      } else if (temp < 75) {
        tempBar.style.background = "linear-gradient(90deg, #c2410c, #f97316)";
        if (tempBadge) { tempBadge.textContent = "Warm"; tempBadge.style.color = "#fdba74"; }
      } else {
        tempBar.style.background = "linear-gradient(90deg, #7f1d1d, #dc2626)";
        if (tempBadge) { tempBadge.textContent = "Overheat"; tempBadge.style.color = "#f87171"; }
      }
    }

    // CPU Load (Blue Lion)
    const cpuVal = document.getElementById("cpu-val");
    const cpuBar = document.getElementById("cpu-bar");
    const cpuPct = hw.cpu_percent || 0.0;
    if (cpuVal) cpuVal.textContent = `${cpuPct.toFixed(1)} %`;
    if (cpuBar) {
      cpuBar.style.width = `${Math.min(100, Math.max(5, cpuPct))}%`;
      cpuBar.style.background = cpuPct > 80 
        ? "linear-gradient(90deg, #dc2626, #ef4444)" 
        : (cpuPct > 50 ? "linear-gradient(90deg, #d97706, #f59e0b)" : "linear-gradient(90deg, #0284c7, #38bdf8)");
    }

    // RAM (Yellow Lion)
    const ramVal = document.getElementById("ram-percent");
    const ramBar = document.getElementById("ram-bar");
    const ramUsedText = document.getElementById("ram-used-text");
    const ramPct = hw.ram_percent || 0.0;
    if (ramVal) ramVal.textContent = `${ramPct.toFixed(1)} %`;
    if (ramBar) {
      ramBar.style.width = `${Math.min(100, Math.max(5, ramPct))}%`;
      ramBar.style.background = "linear-gradient(90deg, #b45309, #fbbf24)";
    }
    if (ramUsedText) ramUsedText.textContent = `${hw.ram_used_mb || 0} / ${hw.ram_total_mb || 4096} MB`;

    // Disk (Green Lion)
    const diskVal = document.getElementById("disk-percent");
    const diskBar = document.getElementById("disk-bar");
    const diskFreeText = document.getElementById("disk-free-text");
    const diskPct = hw.disk_percent || 0.0;
    if (diskVal) diskVal.textContent = `${diskPct.toFixed(1)} %`;
    if (diskBar) {
      diskBar.style.width = `${Math.min(100, Math.max(5, diskPct))}%`;
      diskBar.style.background = "linear-gradient(90deg, #047857, #34d399)";
    }
    if (diskFreeText) diskFreeText.textContent = `${hw.disk_free_gb || 0} GB Free`;

    // Database & Catalog
    const cat = data.catalog || {};
    const machinesCountBadge = document.getElementById("machines-count-badge");
    const toolsCountVal = document.getElementById("tools-count-val");
    const materialsCountVal = document.getElementById("materials-count-val");
    const dbSizeVal = document.getElementById("db-size-val");
    const uptimeVal = document.getElementById("server-uptime");

    if (machinesCountBadge) machinesCountBadge.textContent = `${cat.machines_count || 0} Machines`;
    if (toolsCountVal) toolsCountVal.textContent = cat.tools_count || 0;
    if (materialsCountVal) materialsCountVal.textContent = cat.materials_count || 0;
    if (dbSizeVal) dbSizeVal.textContent = `${cat.database_size_kb || 0} KB`;
    if (uptimeVal) uptimeVal.textContent = `Uptime: ${data.uptime_human || "--"}`;

    // Backup & Rack Sync
    const backup = data.backup || {};
    const rackBadge = document.getElementById("rack-sync-badge");

    if (rackBadge) {
      if (backup.rack_online) {
        rackBadge.textContent = "Online (pi-backup)";
        rackBadge.style.color = "#34d399";
      } else {
        rackBadge.textContent = "Standalone Local";
        rackBadge.style.color = "#94a3b8";
      }
    }

    // Machines List Rendering
    renderMachinesList(cat.machines || []);

    // Live Activity Stream Rendering
    renderActivityStream(data.recent_activity || []);
  }

  // 5. Render Machines Grid
  function renderMachinesList(machines) {
    const container = document.getElementById("machines-list-container");
    if (!container) return;

    if (machines.length === 0) {
      container.innerHTML = `<div class="text-muted-compact">No machines registered. <a href="/machines" style="color: #38bdf8;">Add machine</a></div>`;
      return;
    }

    container.innerHTML = machines.map(m => `
      <div class="machine-chip ${m.is_active ? 'machine-chip-active' : ''}">
        <div class="mach-top">
          <span class="mach-name" title="${escapeHtml(m.name)}">${m.is_active ? '<span class="mach-active-dot" title="Active Machine"></span>' : ''}${escapeHtml(m.name)}</span>
          <span class="mach-dialect">${escapeHtml(m.controller_type || m.controller_dialect || 'GRBL')}</span>
        </div>
        <div class="mach-env">
          ${Math.round(m.work_area_x || m.max_x || 0)} × ${Math.round(m.work_area_y || m.max_y || 0)} × ${Math.round(m.work_area_z || m.max_z || 0)} mm
        </div>
      </div>
    `).join('');
  }

  // 6. Render Activity Stream
  function renderActivityStream(activities) {
    const container = document.getElementById("activity-stream-container");
    const countBadge = document.getElementById("activity-count-badge");
    if (!container) return;

    if (countBadge) countBadge.textContent = `${activities.length} Events`;

    if (activities.length === 0) {
      container.innerHTML = `
        <div class="stream-empty">
          <span>Awaiting client G-code generation requests...</span>
        </div>`;
      return;
    }

    container.innerHTML = activities.map(a => `
      <div class="stream-item">
        <div class="stream-top">
          <span class="stream-op">${escapeHtml(a.operation)}</span>
          <span class="stream-time">${escapeHtml(a.timestamp.split(" ")[1] || a.timestamp)}</span>
        </div>
        <div class="stream-mid">
          <span class="stream-mach">${escapeHtml(a.machine_name || 'Standard CNC')}</span>
        </div>
        <div class="stream-bot">
          <span class="stream-ip">IP: ${escapeHtml(a.client_ip)}</span>
          <span class="stream-lines">${a.lines} lines</span>
          <span class="stream-dur">~${a.estimated_time_sec}s</span>
        </div>
      </div>
    `).join('');
  }

  // 7. Controls Menu Modal & Host Power Listeners
  const menuModal = document.getElementById("hud-menu-modal");
  const btnMenuToggle = document.getElementById("btn-menu-toggle");
  const btnMenuClose = document.getElementById("btn-menu-close");

  function openMenu() { if (menuModal) menuModal.style.display = "flex"; }
  function closeMenu() { if (menuModal) menuModal.style.display = "none"; }

  if (btnMenuToggle) btnMenuToggle.addEventListener("click", openMenu);
  if (btnMenuClose) btnMenuClose.addEventListener("click", closeMenu);
  if (menuModal) {
    menuModal.addEventListener("click", (e) => {
      if (e.target === menuModal) closeMenu();
    });
  }

  const menuBtnReload = document.getElementById("menu-btn-reload");
  if (menuBtnReload) {
    menuBtnReload.addEventListener("click", () => {
      window.location.reload();
    });
  }

  const menuBtnFullscreen = document.getElementById("menu-btn-fullscreen");
  if (menuBtnFullscreen) {
    menuBtnFullscreen.addEventListener("click", () => {
      closeMenu();
      if (btnFullscreen) btnFullscreen.click();
    });
  }

  const menuBtnBackup = document.getElementById("menu-btn-backup");
  if (menuBtnBackup) {
    menuBtnBackup.addEventListener("click", () => {
      closeMenu();
      if (btnBackup) btnBackup.click();
    });
  }

  const menuBtnRestart = document.getElementById("menu-btn-restart");
  if (menuBtnRestart) {
    menuBtnRestart.addEventListener("click", () => {
      closeMenu();
      if (btnRestart) btnRestart.click();
    });
  }

  const menuBtnReboot = document.getElementById("menu-btn-reboot");
  if (menuBtnReboot) {
    menuBtnReboot.addEventListener("click", async () => {
      if (!confirm("⚠️ REBOOT RASPBERRY PI?\n\nAre you sure you want to reboot the Raspberry Pi host (voltron)?\nThe server will be offline for ~45 seconds while restarting.")) return;
      closeMenu();
      try {
        await fetch("/api/system/reboot", { method: "POST" });
        alert("🔌 Reboot sequence initiated. The screen will disconnect and reload after boot.");
        setTimeout(() => { window.location.reload(); }, 40000);
      } catch (e) {
        alert(`Reboot error: ${e.message}`);
      }
    });
  }

  const menuBtnShutdown = document.getElementById("menu-btn-shutdown");
  if (menuBtnShutdown) {
    menuBtnShutdown.addEventListener("click", async () => {
      if (!confirm("🛑 SHUTDOWN / POWER OFF RASPBERRY PI?\n\nAre you sure you want to power down the Raspberry Pi (voltron)?\nYou will need to physically power cycle the unit to turn it back on.")) return;
      closeMenu();
      try {
        await fetch("/api/system/shutdown", { method: "POST" });
        alert("🛑 Shutdown command dispatched. The Pi is powering down safely.");
      } catch (e) {
        alert(`Shutdown error: ${e.message}`);
      }
    });
  }

  // 8. Action Button Event Listeners
  const btnRefresh = document.getElementById("btn-refresh");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      btnRefresh.disabled = true;
      btnRefresh.textContent = "⏳ Reloading...";
      window.location.reload();
    });
  }

  // Support double-tap on top header or clock to reload page
  const hudHeader = document.querySelector(".hud-header");
  if (hudHeader) {
    let lastTap = 0;
    hudHeader.addEventListener("touchend", () => {
      const now = Date.now();
      if (now - lastTap < 400) {
        window.location.reload();
      }
      lastTap = now;
    });
  }

  const btnBackup = document.getElementById("btn-trigger-backup");
  if (btnBackup) {
    btnBackup.addEventListener("click", async () => {
      btnBackup.disabled = true;
      btnBackup.textContent = "⏳ Backing up...";
      try {
        const res = await fetch("/api/system/backup", { method: "POST" });
        const data = await res.json();
        if (res.ok) {
          alert(`Backup successful: ${data.target_file}`);
          fetchSystemStatus();
        } else {
          alert(`Backup failed: ${data.message || 'Unknown error'}`);
        }
      } catch (e) {
        alert(`Backup error: ${e.message}`);
      } finally {
        btnBackup.disabled = false;
        btnBackup.textContent = "💾 Snapshot Backup";
      }
    });
  }

  const btnRestart = document.getElementById("btn-restart-app");
  if (btnRestart) {
    btnRestart.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to restart the Conversational CNC Controller service?")) return;
      btnRestart.disabled = true;
      btnRestart.textContent = "⏳ Restarting...";
      try {
        await fetch("/api/system/restart", { method: "POST" });
        setTimeout(() => {
          window.location.reload();
        }, 3000);
      } catch (e) {
        alert(`Restart error: ${e.message}`);
        btnRestart.disabled = false;
        btnRestart.textContent = "🔄 Restart";
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Start polling loop every 3 seconds
  fetchSystemStatus();
  setInterval(fetchSystemStatus, 3000);
});
