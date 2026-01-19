import type { AppSettings } from "./types";

const DEFAULT_SETTINGS: AppSettings = {
  hotkey: { modifiers: [0xa2, 0xa4], debounceMs: 40 },
  audio: { deviceIndex: null, deviceName: null, sampleRateHz: 16000, channels: 1, frameMs: 20 },
  backend: { host: "127.0.0.1", port: 50051, timeoutSeconds: 30, autoReconnect: true },
  overlay: {
    enabled: true,
    position: "top-right",
    xOffset: 20,
    yOffset: 20,
    autoHideMs: 2000,
  },
  startMinimized: false,
  showNotifications: true,
};

const noop = () => () => {};

export const getBridge = () => {
  if (typeof window !== "undefined" && window.keymuse) {
    return window.keymuse;
  }

  return {
    onBackendLog: noop,
    onBackendStatus: noop,
    onDictationState: noop,
    onTranscript: noop,
    onInstallStatus: noop,
    onStartupError: noop,
    onCachePath: noop,
    getSettings: async () => DEFAULT_SETTINGS,
    saveSettings: async () => undefined,
    requestHistory: async () => [],
    requestCachePath: async () => "C:\\Users\\willp\\.cache\\huggingface\\transformers",
    startDictation: async () => undefined,
    stopDictation: async () => undefined,
    showMainWindow: async () => undefined,
    minimizeToTray: async () => undefined,
  } as const;
};
