import { app, BrowserWindow, dialog, ipcMain, Menu, nativeImage, Tray, screen } from "electron";
import path from "node:path";
import { createDictationClient, streamAudio } from "./grpc-client";
import { createAudioStream } from "./audio";
import { ensureNativeAudioDeps } from "./native-deps";
import { registerHoldHotkey, stopHotkeyListener } from "./hotkeys";
import { addTranscript, getHistory, getLastTranscript } from "./history";
import { sanitizeText, setClipboardText, sendPaste } from "./clipboard";
import { loadSettings, saveSettings } from "./settings";
import type { AppSettings } from "./settings";
import { findPython, installBackendDeps, BackendDepsError, PythonNotFoundError } from "./python-finder";
import { startBackend } from "./backend";
import {
  APP_ROOT,
  ELECTRON_DIR,
  IS_DEV,
  PYTHON_CACHE_PATH,
  RENDERER_DEV_URL,
  RENDERER_DIST,
} from "./constants";

let mainWindow: BrowserWindow | null = null;
let overlayWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let settings = loadSettings();
let backendProcess: { kill: () => void } | null = null;
let backendReady = false;
let audioController: Awaited<ReturnType<typeof createAudioStream>> | null = null;
let dictationStream: ReturnType<typeof streamAudio> | null = null;
let dictationActive = false;

const createMainWindow = () => {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 620,
    minWidth: 380,
    minHeight: 520,
    show: !settings.startMinimized,
    backgroundColor: "#f3ede3",
    webPreferences: {
      preload: path.join(APP_ROOT, "dist-electron", "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (IS_DEV) {
    mainWindow.loadURL(RENDERER_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(RENDERER_DIST, "index.html"));
  }

  mainWindow.on("close", (event) => {
    if (tray) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
};

const createOverlayWindow = () => {
  overlayWindow = new BrowserWindow({
    width: 260,
    height: 50,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    show: false,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: path.join(APP_ROOT, "dist-electron", "overlay-preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  overlayWindow.setIgnoreMouseEvents(true);
  overlayWindow.loadFile(path.join(ELECTRON_DIR, "overlay.html"));
};

const positionOverlay = (mode: AppSettings["overlay"]["position"]) => {
  if (!overlayWindow) {
    return;
  }
  const { xOffset, yOffset } = settings.overlay;
  const { width, height } = overlayWindow.getBounds();
  const { width: screenW, height: screenH } = screen.getPrimaryDisplay().workAreaSize;
  let x = xOffset;
  let y = yOffset;
  if (mode.includes("right")) {
    x = screenW - width - xOffset;
  }
  if (mode.includes("bottom")) {
    y = screenH - height - yOffset;
  }
  overlayWindow.setPosition(x, y, false);
};

const showOverlay = (text: string, mode: "listening" | "processing" | "inserted" | "error") => {
  if (!settings.overlay.enabled || !overlayWindow) {
    return;
  }
  positionOverlay(settings.overlay.position);
  overlayWindow.showInactive();
  overlayWindow.webContents.send("overlay:update", { text, mode });
  if (mode !== "listening" && settings.overlay.autoHideMs > 0) {
    setTimeout(() => overlayWindow?.hide(), settings.overlay.autoHideMs);
  }
};

const hideOverlay = () => {
  overlayWindow?.hide();
};

const createTray = () => {
  tray = new Tray(nativeImage.createEmpty());
  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Show Window",
      click: () => mainWindow?.show(),
    },
    {
      label: "Copy Last Transcript",
      click: () => {
        const last = getLastTranscript();
        if (last) {
          setClipboardText(last);
        }
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => app.quit(),
    },
  ]);
  tray.setToolTip("KeyMuse - Press Ctrl+Alt to dictate");
  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => mainWindow?.show());
};

const ensureBackend = async () => {
  const updateStatus = (payload: { status: string }) => {
    mainWindow?.webContents.send("install:status", payload);
    mainWindow?.webContents.send("backend:status", { ready: false, detail: payload.status });
    mainWindow?.webContents.send("backend:log", payload.status);
  };

  try {
    const python = findPython(APP_ROOT, true);
    return python;
  } catch (error) {
    if (error instanceof BackendDepsError) {
      dialog.showMessageBox({
        type: "info",
        title: "Installing Dependencies",
        message:
          "Python dependencies are missing. KeyMuse will install the required packages now.",
      });
      updateStatus({ status: "Missing Python dependencies. Installing..." });
      installBackendDeps(error.pythonPath, path.resolve(APP_ROOT, "..", ".."));
      return findPython(APP_ROOT, true);
    }
    if (error instanceof PythonNotFoundError) {
      dialog.showErrorBox(
        "Python Required",
        "Python 3.11+ is required to run the speech model. Install Python and restart KeyMuse.",
      );
      mainWindow?.webContents.send("startup:error", {
        message: "Python 3.11+ not found. Install Python and restart KeyMuse.",
      });
    }
    throw error;
  }
};

const startBackendProcess = async () => {
  const nativeDeps = await ensureNativeAudioDeps((line) => {
    mainWindow?.webContents.send("backend:log", line);
  });
  if (!nativeDeps.ok) {
    mainWindow?.webContents.send(
      "backend:log",
      "Audio capture will be unavailable until native modules rebuild successfully.",
    );
    mainWindow?.webContents.send(
      "backend:log",
      "Tip: set PYTHON to Python 3.11 or install setuptools for your Python 3.12 runtime.",
    );
  }

  const python = await ensureBackend();

  const backend = startBackend(python, {
    host: settings.backend.host,
    port: settings.backend.port,
    onOutput: (line) => {
      mainWindow?.webContents.send("backend:log", line);
      // Only send status updates before the backend is ready
      if (!backendReady) {
        mainWindow?.webContents.send("backend:status", {
          ready: false,
          detail: line,
        });
      }
    },
  });
  backendProcess = backend;

  const grpc = createDictationClient(settings.backend.host, settings.backend.port);
  let ready = false;
  let attempts = 0;
  while (!ready) {
    try {
      const health = await grpc.GetHealth({});
      mainWindow?.webContents.send("backend:status", { ready: health.ready, detail: health.detail });
      ready = health.ready;
      backendReady = health.ready;
      if (!ready) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    } catch (error) {
      attempts += 1;
      const message = "Waiting for backend...";
      mainWindow?.webContents.send("backend:status", {
        ready: false,
        detail: message,
      });
      if (attempts === 1) {
        const errorMessage = error instanceof Error ? error.message : "Health check failed";
        mainWindow?.webContents.send("backend:log", `Health check failed: ${errorMessage}`);
      } else if (attempts % 5 === 0) {
        mainWindow?.webContents.send("backend:log", `${message} (${attempts})`);
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
};

const startDictation = async () => {
  if (dictationActive) {
    return;
  }
  dictationActive = true;
  mainWindow?.webContents.send("dictation:state", { state: "RECORDING" });
  showOverlay("Listening...", "listening");

  const grpc = createDictationClient(settings.backend.host, settings.backend.port);
  const stream = streamAudio(
    grpc,
    (event) => {
      if (event.partial) {
        showOverlay(event.partial.text || "Listening...", "listening");
      }
      if (event.final) {
        const sanitized = sanitizeText(event.final.text);
        addTranscript(sanitized);
        mainWindow?.webContents.send("dictation:final", { text: sanitized });
        setClipboardText(sanitized);
        sendPaste();
        showOverlay(`Inserted: ${sanitized.slice(0, 30)}`, "inserted");
      }
      if (event.error) {
        mainWindow?.webContents.send("dictation:state", { state: "ERROR" });
        showOverlay(event.error.message, "error");
      }
    },
    (error) => {
      mainWindow?.webContents.send("dictation:state", { state: "ERROR" });
      showOverlay(error.message, "error");
    },
  );
  dictationStream = stream;

  try {
    audioController = await createAudioStream({
      sampleRateHz: settings.audio.sampleRateHz,
      channels: settings.audio.channels,
      frameMs: settings.audio.frameMs,
      deviceIndex: settings.audio.deviceIndex,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Audio capture failed.";
    mainWindow?.webContents.send("backend:log", message);
    mainWindow?.webContents.send("dictation:state", { state: "ERROR" });
    showOverlay(message, "error");
    return;
  }

  audioController.onFrame((frame) => {
    dictationStream?.write(frame);
  });
  audioController.start();
};

const stopDictation = async () => {
  if (!dictationActive) {
    return;
  }
  dictationActive = false;
  mainWindow?.webContents.send("dictation:state", { state: "PROCESSING" });
  showOverlay("Processing...", "processing");

  // Brief delay to capture any trailing audio still being spoken
  await new Promise((resolve) => setTimeout(resolve, 150));

  audioController?.stop();

  // Send end_of_stream frame and close the write side only
  // Keep the stream open to receive the transcription response
  dictationStream?.write({
    audio: Buffer.alloc(0),
    sample_rate_hz: settings.audio.sampleRateHz,
    channels: settings.audio.channels,
    sequence: BigInt(0),
    end_of_stream: true,
  });
  dictationStream?.end();

  // Wait for the stream to complete (final event received or timeout)
  // The stream event handlers will process the response
  const stream = dictationStream;
  if (stream) {
    await new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        mainWindow?.webContents.send("backend:log", "Transcription timeout");
        resolve();
      }, 30000);

      stream.on("end", () => {
        clearTimeout(timeout);
        resolve();
      });
      stream.on("error", () => {
        clearTimeout(timeout);
        resolve();
      });
    });
  }

  dictationStream = null;
  hideOverlay();
  mainWindow?.webContents.send("dictation:state", { state: "IDLE" });
};

const wireIpc = () => {
  ipcMain.handle("settings:get", () => settings);
  ipcMain.handle("settings:save", (_event, next: AppSettings) => {
    settings = next;
    saveSettings(settings);
    return true;
  });
  ipcMain.handle("history:get", () => getHistory());
  ipcMain.handle("cache:get", () => PYTHON_CACHE_PATH);
  ipcMain.handle("dictation:start", () => startDictation());
  ipcMain.handle("dictation:stop", () => stopDictation());
  ipcMain.handle("window:show", () => mainWindow?.show());
  ipcMain.handle("window:minimize", () => mainWindow?.hide());
};

const waitForRenderer = (): Promise<void> =>
  new Promise((resolve) => {
    if (!mainWindow) {
      resolve();
      return;
    }
    if (mainWindow.webContents.isLoading()) {
      mainWindow.webContents.once("did-finish-load", () => resolve());
    } else {
      resolve();
    }
  });

const startApp = async () => {
  createMainWindow();
  createOverlayWindow();
  createTray();
  wireIpc();
  await waitForRenderer();
  mainWindow?.webContents.send("startup:cache", { path: PYTHON_CACHE_PATH });
  mainWindow?.webContents.send("backend:status", { ready: false, detail: "Initializing..." });
  mainWindow?.webContents.send("backend:log", "Initializing backend...");
  await startBackendProcess();

  registerHoldHotkey({
    onActivate: startDictation,
    onDeactivate: stopDictation,
  });
};

process.on("unhandledRejection", (reason) => {
  const message = reason instanceof Error ? reason.message : "Unhandled rejection";
  mainWindow?.webContents.send("backend:log", `Unhandled: ${message}`);
});

app.whenReady().then(startApp);

app.on("window-all-closed", () => {
  // Keep the app running in the tray on Windows.
});

app.on("before-quit", () => {
  stopHotkeyListener();
  backendProcess?.kill();
  tray?.destroy();
});
