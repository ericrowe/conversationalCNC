/**
 * Tool Library & Material Presets Manager
 */
document.addEventListener("DOMContentLoaded", async () => {
  const toolsTableBody = document.getElementById("toolsTableBody");
  const saveToolBtn = document.getElementById("saveToolBtn");
  const newToolForm = document.getElementById("newToolForm");

  async function loadTools() {
    try {
      const tools = await API.getTools();
      toolsTableBody.innerHTML = "";

      tools.forEach((t) => {
        const tr = document.createElement("tr");
        const presetsHtml = (t.material_presets || [])
          .map(
            (p) =>
              `<span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; margin: 2px;">
                ${p.material_name} (${p.spindle_speed} RPM / ${p.plunge_rate_z} Fz)
                <span style="cursor:pointer; color: #ef4444; margin-left: 4px;" onclick="deletePreset(${p.id})">&times;</span>
              </span>`
          )
          .join(" ");

        tr.innerHTML = `
          <td><strong>T${t.tool_number}</strong></td>
          <td>${t.name}</td>
          <td>${t.tool_type}</td>
          <td>${t.diameter} mm</td>
          <td>
            ${presetsHtml || '<span style="color:var(--text-muted); font-size:0.75rem;">No presets</span>'}
            <button class="btn btn-secondary btn-sm" style="margin-left: 6px; padding: 2px 6px; font-size: 0.75rem;" onclick="promptAddPreset(${t.id})">+ Preset</button>
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" style="color: var(--accent-red);" onclick="deleteTool(${t.id})">Delete</button>
          </td>
        `;
        toolsTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Failed to load tools:", err);
    }
  }

  window.deleteTool = async (id) => {
    if (!confirm("Are you sure you want to delete this tool?")) return;
    try {
      await API.deleteTool(id);
      await loadTools();
    } catch (err) {
      alert("Error deleting tool: " + err.message);
    }
  };

  window.deletePreset = async (id) => {
    if (!confirm("Delete this material preset?")) return;
    try {
      await API.deleteMaterialPreset(id);
      await loadTools();
    } catch (err) {
      alert("Error deleting preset: " + err.message);
    }
  };

  window.promptAddPreset = async (toolId) => {
    const name = prompt("Material Name (e.g. Acrylic, MDF, Aluminum):");
    if (!name) return;
    const rpm = parseInt(prompt("Spindle Speed (RPM):", "16000"), 10);
    if (!rpm) return;
    const plunge = parseFloat(prompt("Plunge Feed Rate (mm/min):", "300"));
    if (!plunge) return;

    try {
      await API.createMaterialPreset(toolId, {
        material_name: name,
        spindle_speed: rpm,
        feed_rate_xy: 1000.0,
        plunge_rate_z: plunge,
        pass_depth: 2.0,
      });
      await loadTools();
    } catch (err) {
      alert("Error adding preset: " + err.message);
    }
  };

  saveToolBtn?.addEventListener("click", async () => {
    const payload = {
      tool_number: parseInt(document.getElementById("toolNumber").value, 10),
      name: document.getElementById("toolName").value,
      tool_type: document.getElementById("toolType").value || "endmill",
      diameter: parseFloat(document.getElementById("toolDiameter").value),
      flute_length: parseFloat(document.getElementById("toolFluteLength").value) || null,
      notes: document.getElementById("toolNotes").value,
    };

    if (!payload.tool_number || !payload.name || !payload.diameter) {
      alert("Please fill required fields (Tool #, Name, Diameter).");
      return;
    }

    try {
      await API.createTool(payload);
      newToolForm.reset();
      await loadTools();
    } catch (err) {
      alert("Failed to add tool: " + err.message);
    }
  });

  await loadTools();
});
