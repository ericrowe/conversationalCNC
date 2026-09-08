/**
 * Client-Side Web Serial API Motion Streaming Module
 * Enables direct USB-serial streaming from the workshop client browser (laptop/tablet)
 * directly to attached CNC machine controllers (Grbl, FluidNC, TinyG).
 */

class WebSerialCNC {
  constructor() {
    this.port = null;
    this.reader = null;
    this.writer = null;
    this.isConnected = false;
    this.isStreaming = false;
    this.baudRate = 115200;
    this.buffer = "";
    this.listeners = {
      connect: [],
      disconnect: [],
      line: [],
      progress: [],
      error: []
    };
  }

  isSupported() {
    return "serial" in navigator;
  }

  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  _emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => {
        try { cb(data); } catch (e) { console.error("Error in serial listener:", e); }
      });
    }
  }

  async connect(baudRate = 115200) {
    if (!this.isSupported()) {
      throw new Error("Web Serial API is not supported in this browser. Use Chrome, Edge, or Opera.");
    }

    try {
      this.baudRate = baudRate;
      this.port = await navigator.serial.requestPort();
      await this.port.open({ baudRate: this.baudRate });
      this.isConnected = true;
      this._emit("connect", { baudRate: this.baudRate });

      this._startReadLoop();
      return true;
    } catch (err) {
      this.isConnected = false;
      this._emit("error", err);
      throw err;
    }
  }

  async disconnect() {
    this.isConnected = false;
    this.isStreaming = false;

    try {
      if (this.reader) {
        await this.reader.cancel();
        this.reader.releaseLock();
        this.reader = null;
      }
      if (this.writer) {
        this.writer.releaseLock();
        this.writer = null;
      }
      if (this.port) {
        await this.port.close();
        this.port = null;
      }
      this._emit("disconnect", {});
    } catch (err) {
      console.warn("Error disconnecting serial port:", err);
    }
  }

  async send(text) {
    if (!this.isConnected || !this.port || !this.port.writable) {
      throw new Error("Serial port not connected");
    }
    const encoder = new TextEncoder();
    const data = encoder.encode(text.endsWith("\n") ? text : text + "\n");
    const writer = this.port.writable.getWriter();
    await writer.write(data);
    writer.releaseLock();
  }

  // Realtime immediate character commands (Grbl standard)
  async softReset() {
    if (!this.isConnected || !this.port || !this.port.writable) return;
    const writer = this.port.writable.getWriter();
    await writer.write(new Uint8Array([0x18])); // Ctrl-X
    writer.releaseLock();
  }

  async feedHold() {
    if (!this.isConnected || !this.port || !this.port.writable) return;
    const writer = this.port.writable.getWriter();
    await writer.write(new Uint8Array([0x21])); // !
    writer.releaseLock();
  }

  async cycleStart() {
    if (!this.isConnected || !this.port || !this.port.writable) return;
    const writer = this.port.writable.getWriter();
    await writer.write(new Uint8Array([0x7E])); // ~
    writer.releaseLock();
  }

  async statusReport() {
    if (!this.isConnected || !this.port || !this.port.writable) return;
    const writer = this.port.writable.getWriter();
    await writer.write(new Uint8Array([0x3F])); // ?
    writer.releaseLock();
  }

  async streamGCode(gcodeText, onProgress, onComplete, onError) {
    if (!this.isConnected) {
      if (onError) onError(new Error("Serial port not connected"));
      return;
    }

    const lines = gcodeText
      .split("\n")
      .map(l => l.trim())
      .filter(l => l.length > 0 && !l.startsWith("("));

    if (lines.length === 0) {
      if (onComplete) onComplete();
      return;
    }

    this.isStreaming = true;
    let currentLine = 0;

    for (let i = 0; i < lines.length; i++) {
      if (!this.isStreaming || !this.isConnected) {
        if (onError) onError(new Error("Stream aborted by user"));
        return;
      }

      const line = lines[i];
      try {
        await this.send(line);
        currentLine = i + 1;
        const progressPct = Math.round((currentLine / lines.length) * 100);
        this._emit("progress", { current: currentLine, total: lines.length, percent: progressPct, line });
        if (onProgress) onProgress({ current: currentLine, total: lines.length, percent: progressPct, line });

        // Small pacing yield to allow device processing
        await new Promise(r => setTimeout(r, 15));
      } catch (err) {
        this.isStreaming = false;
        if (onError) onError(err);
        return;
      }
    }

    this.isStreaming = false;
    if (onComplete) onComplete();
  }

  abortStream() {
    this.isStreaming = false;
    this.feedHold();
  }

  async _startReadLoop() {
    const decoder = new TextDecoder();
    while (this.isConnected && this.port && this.port.readable) {
      try {
        this.reader = this.port.readable.getReader();
        while (true) {
          const { value, done } = await this.reader.read();
          if (done) break;
          if (value) {
            const chunk = decoder.decode(value);
            this.buffer += chunk;
            const lines = this.buffer.split("\n");
            this.buffer = lines.pop(); // Keep partial line
            for (const line of lines) {
              const cleanLine = line.trim();
              if (cleanLine) {
                this._emit("line", cleanLine);
              }
            }
          }
        }
      } catch (err) {
        if (this.isConnected) {
          console.warn("Serial read error:", err);
          this._emit("error", err);
        }
        break;
      } finally {
        if (this.reader) {
          try { this.reader.releaseLock(); } catch (e) {}
          this.reader = null;
        }
      }
    }
  }
}

// Global Singleton for Client Pages
window.WebSerialCNC = new WebSerialCNC();
