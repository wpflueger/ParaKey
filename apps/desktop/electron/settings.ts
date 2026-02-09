import { app } from "electron";
import fs from "node:fs";
import path from "node:path";

export type HotkeyPreset = "ctrl+alt" | "ctrl+shift" | "alt+shift" | "win+alt";

export type HotkeySettings = {
  preset: HotkeyPreset;
  modifiers: number[];
  debounceMs: number;
};

// uIOhook keycodes for modifier keys
export const HOTKEY_PRESETS: Record<HotkeyPreset, number[]> = {
  "ctrl+alt": [29, 56],      // Ctrl + Alt
  "ctrl+shift": [29, 42],    // Ctrl + Shift
  "alt+shift": [56, 42],     // Alt + Shift
  "win+alt": [3675, 56],     // Win + Alt
};

export type AudioSettings = {
  deviceIndex: number | null;
  deviceName: string | null;
  sampleRateHz: number;
  channels: number;
  frameMs: number;
  maxDurationSeconds: number;
};

export type BackendSettings = {
  host: string;
  port: number;
  timeoutSeconds: number;
  autoReconnect: boolean;
};

export type OverlaySettings = {
  enabled: boolean;
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right";
  xOffset: number;
  yOffset: number;
  autoHideMs: number;
};

export type PasteSettings = {
  focusDelayMs: number;
  restoreDelayMs: number;
};

export type AppSettings = {
  hotkey: HotkeySettings;
  audio: AudioSettings;
  backend: BackendSettings;
  overlay: OverlaySettings;
  paste: PasteSettings;
  startMinimized: boolean;
  showNotifications: boolean;
};

const DEFAULT_SETTINGS: AppSettings = {
  hotkey: {
    preset: "ctrl+alt",
    modifiers: HOTKEY_PRESETS["ctrl+alt"],
    debounceMs: 40,
  },
  audio: {
    deviceIndex: null,
    deviceName: null,
    sampleRateHz: 16000,
    channels: 1,
    frameMs: 20,
    maxDurationSeconds: 60,
  },
  backend: {
    host: "127.0.0.1",
    port: 50051,
    timeoutSeconds: 30,
    autoReconnect: true,
  },
  overlay: {
    enabled: true,
    position: "top-right",
    xOffset: 20,
    yOffset: 20,
    autoHideMs: 2000,
  },
  paste: {
    focusDelayMs: 50,
    restoreDelayMs: 100,
  },
  startMinimized: true,
  showNotifications: true,
};

const SETTINGS_FILE = "settings.json";

const getSettingsPath = () => path.join(app.getPath("userData"), SETTINGS_FILE);

export const loadSettings = (): AppSettings => {
  const filePath = getSettingsPath();
  try {
    if (!fs.existsSync(filePath)) {
      return { ...DEFAULT_SETTINGS };
    }
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      hotkey: { ...DEFAULT_SETTINGS.hotkey, ...parsed.hotkey },
      audio: { ...DEFAULT_SETTINGS.audio, ...parsed.audio },
      backend: { ...DEFAULT_SETTINGS.backend, ...parsed.backend },
      overlay: { ...DEFAULT_SETTINGS.overlay, ...parsed.overlay },
      paste: { ...DEFAULT_SETTINGS.paste, ...parsed.paste },
    };
  } catch (error) {
    console.warn("Failed to load settings, using defaults", error);
    return { ...DEFAULT_SETTINGS };
  }
};

export const saveSettings = (settings: AppSettings): void => {
  const filePath = getSettingsPath();
  const payload = JSON.stringify(settings, null, 2);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, payload, "utf-8");
};

export const resetSettings = (): AppSettings => {
  const settings = { ...DEFAULT_SETTINGS };
  saveSettings(settings);
  return settings;
};

export const getDefaultSettings = (): AppSettings => ({ ...DEFAULT_SETTINGS });
