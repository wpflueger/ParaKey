import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

const stubBridge = () => ({
  onBackendLog: () => () => {},
  onBackendStatus: () => () => {},
  onDictationState: () => () => {},
  onTranscript: () => () => {},
  onInstallStatus: () => () => {},
  onStartupError: () => () => {},
  onCachePath: () => () => {},
  getSettings: async () => ({
    hotkey: { preset: "ctrl+alt", modifiers: [0xa2, 0xa4], debounceMs: 40 },
    audio: { deviceIndex: null, deviceName: null, sampleRateHz: 16000, channels: 1, frameMs: 20 },
    backend: { host: "127.0.0.1", port: 50051, timeoutSeconds: 30, autoReconnect: true },
    overlay: { enabled: true, position: "top-right", xOffset: 20, yOffset: 20, autoHideMs: 2000 },
    startMinimized: false,
    showNotifications: true,
  }),
  saveSettings: async () => undefined,
  requestHistory: async () => [],
  requestCachePath: async () => "",
  startDictation: async () => undefined,
  stopDictation: async () => undefined,
  showMainWindow: async () => undefined,
  minimizeToTray: async () => undefined,
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).keymuse = stubBridge();

describe("App", () => {
  it("renders startup view without crashing", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Preparing your dictation engine")).toBeInTheDocument();
    });
  });
});
