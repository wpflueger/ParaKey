// @vitest-environment node
import { describe, expect, it, vi, beforeEach } from "vitest";

let mockFiles: Record<string, string> = {};

vi.mock("electron", () => ({
  app: {
    getPath: () => "/tmp/test-settings",
  },
}));

vi.mock("node:fs", () => ({
  default: {
    existsSync: (path: string) => path in mockFiles,
    readFileSync: (path: string) => mockFiles[path] ?? "",
    writeFileSync: (path: string, content: string) => { mockFiles[path] = content; },
    mkdirSync: () => undefined,
  },
}));

import { loadSettings, getDefaultSettings } from "./settings";

describe("settings", () => {
  beforeEach(() => {
    mockFiles = {};
  });

  describe("default settings", () => {
    it("includes maxDurationSeconds in audio defaults", () => {
      const defaults = getDefaultSettings();
      expect(defaults.audio.maxDurationSeconds).toBe(60);
    });

    it("includes paste settings with timing defaults", () => {
      const defaults = getDefaultSettings();
      expect(defaults.paste).toEqual({
        focusDelayMs: 50,
        restoreDelayMs: 100,
      });
    });

    it("includes all expected top-level keys", () => {
      const defaults = getDefaultSettings();
      expect(defaults).toHaveProperty("hotkey");
      expect(defaults).toHaveProperty("audio");
      expect(defaults).toHaveProperty("backend");
      expect(defaults).toHaveProperty("overlay");
      expect(defaults).toHaveProperty("paste");
      expect(defaults).toHaveProperty("startMinimized");
      expect(defaults).toHaveProperty("showNotifications");
    });
  });

  describe("loadSettings", () => {
    it("returns defaults when no file exists", () => {
      const settings = loadSettings();
      expect(settings.audio.maxDurationSeconds).toBe(60);
      expect(settings.paste.focusDelayMs).toBe(50);
    });

    it("merges partial settings with defaults", () => {
      mockFiles["/tmp/test-settings/settings.json"] = JSON.stringify({
        audio: { sampleRateHz: 44100 },
      });

      const settings = loadSettings();
      // Custom value preserved
      expect(settings.audio.sampleRateHz).toBe(44100);
      // New defaults still present
      expect(settings.audio.maxDurationSeconds).toBe(60);
    });

    it("merges paste settings with defaults", () => {
      mockFiles["/tmp/test-settings/settings.json"] = JSON.stringify({
        paste: { focusDelayMs: 200 },
      });

      const settings = loadSettings();
      expect(settings.paste.focusDelayMs).toBe(200);
      // restoreDelayMs gets default
      expect(settings.paste.restoreDelayMs).toBe(100);
    });

    it("handles missing paste section in saved settings", () => {
      mockFiles["/tmp/test-settings/settings.json"] = JSON.stringify({
        hotkey: { preset: "alt+shift" },
      });

      const settings = loadSettings();
      expect(settings.paste).toEqual({
        focusDelayMs: 50,
        restoreDelayMs: 100,
      });
    });

    it("handles corrupted settings file", () => {
      mockFiles["/tmp/test-settings/settings.json"] = "not json";

      const settings = loadSettings();
      expect(settings.audio.maxDurationSeconds).toBe(60);
      expect(settings.paste.focusDelayMs).toBe(50);
    });
  });
});
