/**
 * Conversational CNC Controller API Client
 */
const API = {
  async getHealth() {
    const res = await fetch("/api/health");
    return await res.json();
  },

  async getMachines() {
    const res = await fetch("/api/machines");
    return await res.json();
  },

  async getActiveMachine() {
    const res = await fetch("/api/machines/active");
    if (!res.ok) return null;
    return await res.json();
  },

  async activateMachine(id) {
    const res = await fetch(`/api/machines/${id}/activate`, {
      method: "POST",
    });
    return await res.json();
  },

  async createMachine(data) {
    const res = await fetch("/api/machines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return await res.json();
  },

  async updateMachine(id, data) {
    const res = await fetch(`/api/machines/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || "Update failed");
    return json;
  },

  async deleteMachine(id) {
    const res = await fetch(`/api/machines/${id}`, {
      method: "DELETE",
    });
    return await res.json();
  },

  async getTools() {
    const res = await fetch("/api/tools");
    return await res.json();
  },

  async createTool(data) {
    const res = await fetch("/api/tools", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return await res.json();
  },

  async deleteTool(id) {
    const res = await fetch(`/api/tools/${id}`, {
      method: "DELETE",
    });
    return await res.json();
  },

  async createMaterialPreset(toolId, data) {
    const res = await fetch(`/api/materials/tool/${toolId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return await res.json();
  },

  async deleteMaterialPreset(id) {
    const res = await fetch(`/api/materials/${id}`, {
      method: "DELETE",
    });
    return await res.json();
  },

  async generateStraightPlunge(payload) {
    const res = await fetch("/api/generate/drilling/straight-plunge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.error || "Generation failed");
    }
    return data;
  },

  async generatePeckDrilling(payload) {
    const res = await fetch("/api/generate/drilling/peck", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.error || "Generation failed");
    }
    return data;
  },

  async getThreadStandards() {
    const res = await fetch("/api/generate/thread-standards");
    return await res.json();
  },

  async generateThreadMilling(payload) {
    const res = await fetch("/api/generate/thread-milling", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.error || "Generation failed");
    }
    return data;
  },

  async generateCircularPocket(payload) {
    const res = await fetch("/api/generate/pocket/circular", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.error || "Generation failed");
    }
    return data;
  },

  async generateSurfacing(payload) {
    const res = await fetch("/api/generate/surfacing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.error || "Generation failed");
    }
    return data;
  },

  async getEngravingFonts() {
    const res = await fetch("/api/generate/engraving/fonts");
    return await res.json();
  },

  async generateTextEngraving(payload) {
    const res = await fetch("/api/generate/engraving/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.error || "Generation failed");
    }
    return data;
  }
};



