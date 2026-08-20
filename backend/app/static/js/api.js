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

  async getEngravingGlyphs() {
    const res = await fetch("/api/generate/engraving/glyphs");
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
  },

  async generateRectangularPocket(payload) {
    const res = await fetch("/api/generate/pocket/rectangular", {
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

  async generateRectangularBoss(payload) {
    const res = await fetch("/api/generate/boss/rectangular", {
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

  async generateLinearSlot(payload) {
    const res = await fetch("/api/generate/slotting/linear", {
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

  async generateRectangularChamfer(payload) {
    const res = await fetch("/api/generate/chamfering/rectangular", {
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

  async transformShift(payload) {
    const res = await fetch("/api/transform/shift", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Shift failed");
    return data;
  },

  async transformRotate(payload) {
    const res = await fetch("/api/transform/rotate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Rotate failed");
    return data;
  },

  async transformMirror(payload) {
    const res = await fetch("/api/transform/mirror", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Mirror failed");
    return data;
  },

  async transformOverrideFeeds(payload) {
    const res = await fetch("/api/transform/feed-speed-override", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Override failed");
    return data;
  },

  async transformSplitTools(payload) {
    const res = await fetch("/api/transform/split-tools", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Split failed");
    return data;
  },

  async generateZProbeMacro(payload) {
    const res = await fetch("/api/probing/z-touch-plate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Z-probe generation failed");
    return data;
  },

  async generateCornerXYZMacro(payload) {
    const res = await fetch("/api/probing/corner-xyz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Corner probe generation failed");
    return data;
  },

  async generateHomingMacro() {
    const res = await fetch("/api/probing/homing", { method: "GET" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Homing macro failed");
    return data;
  },

  async jogStep(payload) {
    const res = await fetch("/api/jog/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Jog failed");
    return data;
  },

  async jogZero(payload) {
    const res = await fetch("/api/jog/zero", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Zero failed");
    return data;
  },

  async jogGotoOrigin(payload) {
    const res = await fetch("/api/jog/goto-origin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Go to origin failed");
    return data;
  },

  async jogSpindle(payload) {
    const res = await fetch("/api/jog/spindle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Spindle command failed");
    return data;
  },

  async generateJobSequence(payload) {
    const res = await fetch("/api/generate/job-sequence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Job sequence generation failed");
    return data;
  },

  async generateContourMilling(payload) {
    const res = await fetch("/api/generate/milling/contour", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Contour milling generation failed");
    return data;
  },

  async generateStepAndRepeatGrid(payload) {
    const res = await fetch("/api/generate/nesting/grid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Step-and-repeat generation failed");
    return data;
  },

  async generateSoftJawFixture(payload) {
    const res = await fetch("/api/generate/nesting/soft-jaw", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "Soft jaw fixture generation failed");
    return data;
  },

  async parseDXF(payload) {
    const res = await fetch("/api/generate/dxf/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "DXF Parsing failed");
    return data;
  },

  async generateDXFToolpath(payload) {
    const res = await fetch("/api/generate/dxf/toolpath", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.error || "DXF Toolpath generation failed");
    return data;
  }
};












