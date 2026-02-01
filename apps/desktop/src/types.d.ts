export type BackendStatus = {
  ready: boolean;
  detail: string;
};

export type DictationState = "IDLE" | "RECORDING" | "PROCESSING" | "INSERTING" | "ERROR";

export type HotkeyPreset = "ctrl+alt" | "ctrl+shift" | "alt+shift" | "win+alt";

export type AppSettings = {
  hotkey: {
    preset: HotkeyPreset;
    modifiers: number[];
    debounceMs: number;
  };
  audio: {
    deviceIndex: number | null;
    deviceName: string | null;
    sampleRateHz: number;
    channels: number;
    frameMs: number;
  };
  backend: {
    host: string;
    port: number;
    timeoutSeconds: number;
    autoReconnect: boolean;
  };
  overlay: {
    enabled: boolean;
    position: "top-left" | "top-right" | "bottom-left" | "bottom-right";
    xOffset: number;
    yOffset: number;
    autoHideMs: number;
  };
  startMinimized: boolean;
  showNotifications: boolean;
};

declare global {
  interface Window {
    parakey: {
      onBackendLog: (callback: (line: string) => void) => () => void;
      onBackendStatus: (callback: (payload: BackendStatus) => void) => () => void;
      onDictationState: (callback: (payload: { state: DictationState }) => void) => () => void;
      onTranscript: (callback: (payload: { text: string }) => void) => () => void;
      onInstallStatus: (callback: (payload: { status: string }) => void) => () => void;
      onStartupError: (callback: (payload: { message: string }) => void) => () => void;
      onCachePath: (callback: (payload: { path: string }) => void) => () => void;
      getSettings: () => Promise<AppSettings>;
      saveSettings: (settings: AppSettings) => Promise<void>;
      requestHistory: () => Promise<string[]>;
      requestCachePath: () => Promise<string>;
      startDictation: () => Promise<void>;
      stopDictation: () => Promise<void>;
      showMainWindow: () => Promise<void>;
      minimizeToTray: () => Promise<void>;
    };
  }
}
