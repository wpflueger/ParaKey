import {
  __require,
  __toESM,
  require_electron
} from "./chunk-FD56QJH3.js";

// electron/main.ts
var import_electron3 = __toESM(require_electron(), 1);
import path5 from "path";

// electron/grpc-client.ts
import { loadPackageDefinition } from "@grpc/grpc-js";
import { loadSync } from "@grpc/proto-loader";

// electron/constants.ts
import path from "path";
var IS_DEV = process.env.NODE_ENV === "development";
var APP_ROOT = path.resolve(__dirname, "..");
var REPO_ROOT = path.resolve(APP_ROOT, "..", "..");
var ELECTRON_DIR = path.join(APP_ROOT, "electron");
var PYTHON_CACHE_PATH = "C:\\Users\\willp\\.cache\\huggingface\\transformers";
var RENDERER_DIST = path.join(APP_ROOT, "dist");
var RENDERER_DEV_URL = "http://localhost:5173";
var PROTO_PATH = path.join(REPO_ROOT, "shared", "proto", "dictation.proto");

// electron/grpc-client.ts
var createDictationClient = (host, port) => {
  const protoPath = PROTO_PATH;
  const packageDefinition = loadSync(protoPath, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
  });
  const grpcPackage = loadPackageDefinition(packageDefinition);
  const service = grpcPackage.keymuse.dictation.v1.DictationService;
  const client = new service(`${host}:${port}`, createInsecureCredentials());
  return {
    GetHealth: (payload) => new Promise((resolve, reject) => {
      client.GetHealth(payload, (error, response) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(response);
      });
    }),
    StreamAudio: () => client.StreamAudio()
  };
};
var createInsecureCredentials = () => {
  const grpc = __require("@grpc/grpc-js");
  return grpc.credentials.createInsecure();
};
var streamAudio = (client, onEvent, onError) => {
  const stream = client.StreamAudio();
  stream.on("data", (event) => onEvent(event));
  stream.on("error", (error) => onError(error));
  return stream;
};

// electron/audio.ts
var createAudioStream = async (options) => {
  const portAudioModule = await import("naudiodon");
  const portAudio = portAudioModule;
  const frameSamples = Math.round(options.sampleRateHz * options.frameMs / 1e3);
  const frameBytes = frameSamples * options.channels * 2;
  const input = new portAudio.AudioInput({
    channelCount: options.channels,
    sampleFormat: portAudio.SampleFormat16Bit,
    sampleRate: options.sampleRateHz,
    deviceId: options.deviceIndex ?? void 0,
    closeOnError: true
  });
  let sequence = BigInt(0);
  let onFrame = null;
  let buffer = Buffer.alloc(0);
  input.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (buffer.length >= frameBytes) {
      const frame = buffer.subarray(0, frameBytes);
      buffer = buffer.subarray(frameBytes);
      if (onFrame) {
        onFrame({
          audio: frame,
          sample_rate_hz: options.sampleRateHz,
          channels: options.channels,
          sequence: sequence++,
          end_of_stream: false
        });
      }
    }
  });
  return {
    start: () => input.start(),
    stop: () => input.stop(),
    onFrame: (callback) => {
      onFrame = callback;
    }
  };
};

// electron/hotkeys.ts
import { uIOhook } from "uiohook-napi";
var CTRL_KEYS = /* @__PURE__ */ new Set([29, 3613]);
var ALT_KEYS = /* @__PURE__ */ new Set([56, 3640]);
var registerHoldHotkey = ({ onActivate, onDeactivate }) => {
  let ctrlDown = false;
  let altDown = false;
  let active = false;
  const updateState = () => {
    const shouldBeActive = ctrlDown && altDown;
    if (shouldBeActive && !active) {
      active = true;
      onActivate();
    } else if (!shouldBeActive && active) {
      active = false;
      onDeactivate();
    }
  };
  uIOhook.on("keydown", (event) => {
    if (CTRL_KEYS.has(event.keycode)) {
      ctrlDown = true;
    }
    if (ALT_KEYS.has(event.keycode)) {
      altDown = true;
    }
    updateState();
  });
  uIOhook.on("keyup", (event) => {
    if (CTRL_KEYS.has(event.keycode)) {
      ctrlDown = false;
    }
    if (ALT_KEYS.has(event.keycode)) {
      altDown = false;
    }
    updateState();
  });
  uIOhook.start();
};
var stopHotkeyListener = () => {
  uIOhook.removeAllListeners();
  uIOhook.stop();
};

// electron/history.ts
var MAX_HISTORY = 10;
var history = [];
var addTranscript = (text) => {
  history = [...history, text].slice(-MAX_HISTORY);
};
var getHistory = () => [...history];
var getLastTranscript = () => {
  if (history.length === 0) {
    return null;
  }
  return history[history.length - 1];
};

// electron/clipboard.ts
var import_electron = __toESM(require_electron(), 1);
var CONTROL_PATTERN = /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g;
var BIDI_PATTERN = new RegExp("[\\u200E\\u200F\\u202A-\\u202E\\u2066-\\u2069]", "g");
var sanitizeText = (text) => {
  let sanitized = text.replace(CONTROL_PATTERN, "").replace(BIDI_PATTERN, "");
  sanitized = sanitized.normalize("NFC");
  sanitized = sanitized.replace(/\r\n/g, "\n").replace(/\r/g, "\n").replace(/\n/g, "\r\n");
  return sanitized;
};
var setClipboardText = (text) => {
  import_electron.clipboard.writeText(text);
};
var sendPaste = () => {
};

// electron/settings.ts
var import_electron2 = __toESM(require_electron(), 1);
import fs from "fs";
import path2 from "path";
var DEFAULT_SETTINGS = {
  hotkey: {
    modifiers: [162, 164],
    debounceMs: 40
  },
  audio: {
    deviceIndex: null,
    deviceName: null,
    sampleRateHz: 16e3,
    channels: 1,
    frameMs: 20
  },
  backend: {
    host: "127.0.0.1",
    port: 50051,
    timeoutSeconds: 30,
    autoReconnect: true
  },
  overlay: {
    enabled: true,
    position: "top-right",
    xOffset: 20,
    yOffset: 20,
    autoHideMs: 2e3
  },
  startMinimized: true,
  showNotifications: true
};
var SETTINGS_FILE = "settings.json";
var getSettingsPath = () => path2.join(import_electron2.app.getPath("userData"), SETTINGS_FILE);
var loadSettings = () => {
  const filePath = getSettingsPath();
  try {
    if (!fs.existsSync(filePath)) {
      return { ...DEFAULT_SETTINGS };
    }
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      hotkey: { ...DEFAULT_SETTINGS.hotkey, ...parsed.hotkey },
      audio: { ...DEFAULT_SETTINGS.audio, ...parsed.audio },
      backend: { ...DEFAULT_SETTINGS.backend, ...parsed.backend },
      overlay: { ...DEFAULT_SETTINGS.overlay, ...parsed.overlay }
    };
  } catch (error) {
    console.warn("Failed to load settings, using defaults", error);
    return { ...DEFAULT_SETTINGS };
  }
};
var saveSettings = (settings2) => {
  const filePath = getSettingsPath();
  const payload = JSON.stringify(settings2, null, 2);
  fs.mkdirSync(path2.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, payload, "utf-8");
};

// electron/python-finder.ts
import path3 from "path";
import { execFileSync, spawnSync } from "child_process";
import fs2 from "fs";
var PythonNotFoundError = class extends Error {
};
var BackendDepsError = class extends Error {
  pythonPath;
  constructor(message, pythonPath) {
    super(message);
    this.pythonPath = pythonPath;
  }
};
var runPythonCheck = (pythonPath, code) => {
  try {
    const result = spawnSync(pythonPath, ["-c", code], {
      encoding: "utf-8",
      timeout: 3e4,
      windowsHide: true
    });
    if (result.status === 0) {
      return result.stdout.trim();
    }
    return null;
  } catch {
    return null;
  }
};
var checkPythonVersion = (pythonPath) => runPythonCheck(pythonPath, "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')");
var checkTorch = (pythonPath) => runPythonCheck(pythonPath, "import torch; print('ok')") === "ok";
var checkNemo = (pythonPath) => runPythonCheck(pythonPath, "import nemo; print('ok')") === "ok";
var checkCuda = (pythonPath) => runPythonCheck(pythonPath, "import torch; print('ok' if torch.cuda.is_available() else 'no')") === "ok";
var isValidPython = (version) => {
  if (!version) {
    return false;
  }
  const [major, minor] = version.split(".").map((part) => Number(part));
  if (!Number.isFinite(major) || !Number.isFinite(minor)) {
    return false;
  }
  return major > 3 || major === 3 && minor >= 11;
};
var getPythonInfo = (pythonPath, checkDeps) => {
  if (!fs2.existsSync(pythonPath)) {
    return null;
  }
  const version = checkPythonVersion(pythonPath);
  if (!isValidPython(version)) {
    return null;
  }
  const info = {
    executable: pythonPath,
    version: version ?? "",
    hasTorch: false,
    hasNemo: false,
    hasCuda: false
  };
  if (checkDeps) {
    info.hasTorch = checkTorch(pythonPath);
    info.hasNemo = checkNemo(pythonPath);
    if (info.hasTorch) {
      info.hasCuda = checkCuda(pythonPath);
    }
  }
  return info;
};
var findEnvPython = () => {
  const envPython = process.env.KEYMUSE_PYTHON;
  if (envPython && fs2.existsSync(envPython)) {
    return envPython;
  }
  return null;
};
var findVenvPython = (appRoot) => {
  const searchPaths = [
    path3.join(appRoot, ".venv", "Scripts", "python.exe"),
    path3.join(appRoot, "..", ".venv", "Scripts", "python.exe"),
    path3.join(appRoot, "..", "..", ".venv", "Scripts", "python.exe")
  ];
  for (const candidate of searchPaths) {
    if (fs2.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
};
var findPathPython = () => {
  const command = process.platform === "win32" ? "where" : "which";
  try {
    const output = execFileSync(command, ["python"], { encoding: "utf-8" }).trim();
    const first = output.split(/\r?\n/)[0];
    if (first && fs2.existsSync(first)) {
      return first;
    }
  } catch {
    return null;
  }
  return null;
};
var findPyLauncher = () => {
  if (process.platform !== "win32") {
    return null;
  }
  for (const version of ["3.12", "3.11"]) {
    try {
      const output = execFileSync("py", [`-${version}`, "-c", "import sys; print(sys.executable)"], {
        encoding: "utf-8",
        windowsHide: true
      }).trim();
      if (output && fs2.existsSync(output)) {
        return output;
      }
    } catch {
      continue;
    }
  }
  return null;
};
var findCommonInstall = () => {
  if (process.platform !== "win32") {
    return null;
  }
  const localAppData = process.env.LOCALAPPDATA ?? "";
  const candidates = [
    localAppData && path3.join(localAppData, "Programs", "Python"),
    "C:/Python312",
    "C:/Python311",
    "C:/Program Files/Python312",
    "C:/Program Files/Python311"
  ].filter(Boolean);
  for (const base of candidates) {
    if (!fs2.existsSync(base)) {
      continue;
    }
    const direct = path3.join(base, "python.exe");
    if (fs2.existsSync(direct)) {
      return direct;
    }
    try {
      const subdirs = fs2.readdirSync(base, { withFileTypes: true });
      for (const sub of subdirs) {
        if (sub.isDirectory() && sub.name.startsWith("Python")) {
          const candidate = path3.join(base, sub.name, "python.exe");
          if (fs2.existsSync(candidate)) {
            return candidate;
          }
        }
      }
    } catch {
      continue;
    }
  }
  return null;
};
var findPython = (appRoot, checkDeps = true) => {
  const finders = [
    findEnvPython,
    () => findVenvPython(appRoot),
    findPathPython,
    findPyLauncher,
    findCommonInstall
  ];
  let found = null;
  for (const finder of finders) {
    const candidate = finder();
    if (!candidate) {
      continue;
    }
    const info = getPythonInfo(candidate, checkDeps);
    if (!info) {
      continue;
    }
    if (!checkDeps || info.hasTorch && info.hasNemo) {
      return info;
    }
    if (!found) {
      found = info;
    }
  }
  if (found) {
    const missing = [!found.hasTorch && "torch", !found.hasNemo && "nemo"].filter(Boolean).join(", ");
    throw new BackendDepsError(
      `Python found but missing backend dependencies: ${missing}.`,
      found.executable
    );
  }
  throw new PythonNotFoundError(
    "Python 3.11+ not found. Install Python or set KEYMUSE_PYTHON to your Python executable."
  );
};
var installBackendDeps = (pythonPath, repoRoot) => {
  const requirements = path3.join(repoRoot, "backend", "requirements.txt");
  execFileSync(pythonPath, ["-m", "pip", "install", "-r", requirements], {
    stdio: "inherit"
  });
};

// electron/backend.ts
import { spawn } from "child_process";
import path4 from "path";
var buildPythonPath = (repoRoot) => {
  const paths = [
    path4.join(repoRoot, "shared", "src"),
    path4.join(repoRoot, "backend", "src"),
    path4.join(repoRoot, "client", "src")
  ];
  const existing = process.env.PYTHONPATH;
  if (existing) {
    paths.push(existing);
  }
  return paths.join(path4.delimiter);
};
var startBackend = (python, options) => {
  var _a, _b;
  const env = {
    ...process.env,
    PYTHONPATH: buildPythonPath(REPO_ROOT),
    KEYMUSE_HOST: options.host,
    KEYMUSE_PORT: String(options.port),
    PYTHONUNBUFFERED: "1"
  };
  if (options.mode) {
    env.KEYMUSE_MODE = options.mode;
  }
  if (options.device) {
    env.KEYMUSE_DEVICE = options.device;
  }
  if (options.model) {
    env.KEYMUSE_MODEL = options.model;
  }
  const cmd = ["-m", "keymuse_backend.server"];
  const child = spawn(python.executable, cmd, {
    env,
    windowsHide: true
  });
  const handleOutput = (data) => {
    var _a2;
    const text = data.toString();
    for (const line of text.split(/\r?\n/)) {
      if (!line.trim()) {
        continue;
      }
      (_a2 = options.onOutput) == null ? void 0 : _a2.call(options, line.trim());
    }
  };
  (_a = child.stdout) == null ? void 0 : _a.on("data", handleOutput);
  (_b = child.stderr) == null ? void 0 : _b.on("data", handleOutput);
  return {
    process: child,
    kill: () => {
      if (!child.killed) {
        child.kill();
      }
    }
  };
};

// electron/main.ts
var mainWindow = null;
var overlayWindow = null;
var tray = null;
var settings = loadSettings();
var backendProcess = null;
var audioController = null;
var dictationStream = null;
var dictationActive = false;
var createMainWindow = () => {
  mainWindow = new import_electron3.BrowserWindow({
    width: 420,
    height: 620,
    minWidth: 380,
    minHeight: 520,
    show: !settings.startMinimized,
    backgroundColor: "#f3ede3",
    webPreferences: {
      preload: path5.join(APP_ROOT, "dist-electron", "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  if (IS_DEV) {
    mainWindow.loadURL(RENDERER_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path5.join(RENDERER_DIST, "index.html"));
  }
  mainWindow.on("close", (event) => {
    if (tray) {
      event.preventDefault();
      mainWindow == null ? void 0 : mainWindow.hide();
    }
  });
};
var createOverlayWindow = () => {
  overlayWindow = new import_electron3.BrowserWindow({
    width: 260,
    height: 50,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    show: false,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: path5.join(APP_ROOT, "dist-electron", "overlay-preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  overlayWindow.setIgnoreMouseEvents(true);
  overlayWindow.loadFile(path5.join(ELECTRON_DIR, "overlay.html"));
};
var positionOverlay = (mode) => {
  if (!overlayWindow) {
    return;
  }
  const { xOffset, yOffset } = settings.overlay;
  const { width, height } = overlayWindow.getBounds();
  const { width: screenW, height: screenH } = import_electron3.screen.getPrimaryDisplay().workAreaSize;
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
var showOverlay = (text, mode) => {
  if (!settings.overlay.enabled || !overlayWindow) {
    return;
  }
  positionOverlay(settings.overlay.position);
  overlayWindow.showInactive();
  overlayWindow.webContents.send("overlay:update", { text, mode });
  if (mode !== "listening" && settings.overlay.autoHideMs > 0) {
    setTimeout(() => overlayWindow == null ? void 0 : overlayWindow.hide(), settings.overlay.autoHideMs);
  }
};
var hideOverlay = () => {
  overlayWindow == null ? void 0 : overlayWindow.hide();
};
var createTray = () => {
  tray = new import_electron3.Tray(import_electron3.nativeImage.createEmpty());
  const contextMenu = import_electron3.Menu.buildFromTemplate([
    {
      label: "Show Window",
      click: () => mainWindow == null ? void 0 : mainWindow.show()
    },
    {
      label: "Copy Last Transcript",
      click: () => {
        const last = getLastTranscript();
        if (last) {
          setClipboardText(last);
        }
      }
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => import_electron3.app.quit()
    }
  ]);
  tray.setToolTip("KeyMuse - Press Ctrl+Alt to dictate");
  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => mainWindow == null ? void 0 : mainWindow.show());
};
var ensureBackend = async () => {
  const updateStatus = (payload) => {
    mainWindow == null ? void 0 : mainWindow.webContents.send("install:status", payload);
    mainWindow == null ? void 0 : mainWindow.webContents.send("backend:status", { ready: false, detail: payload.status });
    mainWindow == null ? void 0 : mainWindow.webContents.send("backend:log", payload.status);
  };
  try {
    const python = findPython(APP_ROOT, true);
    return python;
  } catch (error) {
    if (error instanceof BackendDepsError) {
      import_electron3.dialog.showMessageBox({
        type: "info",
        title: "Installing Dependencies",
        message: "Python dependencies are missing. KeyMuse will install the required packages now."
      });
      updateStatus({ status: "Missing Python dependencies. Installing..." });
      installBackendDeps(error.pythonPath, path5.resolve(APP_ROOT, "..", ".."));
      return findPython(APP_ROOT, true);
    }
    if (error instanceof PythonNotFoundError) {
      import_electron3.dialog.showErrorBox(
        "Python Required",
        "Python 3.11+ is required to run the speech model. Install Python and restart KeyMuse."
      );
      mainWindow == null ? void 0 : mainWindow.webContents.send("startup:error", {
        message: "Python 3.11+ not found. Install Python and restart KeyMuse."
      });
    }
    throw error;
  }
};
var startBackendProcess = async () => {
  const python = await ensureBackend();
  const backend = startBackend(python, {
    host: settings.backend.host,
    port: settings.backend.port,
    onOutput: (line) => {
      mainWindow == null ? void 0 : mainWindow.webContents.send("backend:log", line);
      mainWindow == null ? void 0 : mainWindow.webContents.send("backend:status", {
        ready: false,
        detail: line
      });
    }
  });
  backendProcess = backend;
  const grpc = createDictationClient(settings.backend.host, settings.backend.port);
  let ready = false;
  let attempts = 0;
  while (!ready) {
    try {
      const health = await grpc.GetHealth({});
      mainWindow == null ? void 0 : mainWindow.webContents.send("backend:status", { ready: health.ready, detail: health.detail });
      ready = health.ready;
      if (!ready) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    } catch {
      attempts += 1;
      const message = attempts === 1 ? "Waiting for backend..." : `Waiting for backend... (${attempts})`;
      mainWindow == null ? void 0 : mainWindow.webContents.send("backend:status", {
        ready: false,
        detail: message
      });
      mainWindow == null ? void 0 : mainWindow.webContents.send("backend:log", message);
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
};
var startDictation = async () => {
  if (dictationActive) {
    return;
  }
  dictationActive = true;
  mainWindow == null ? void 0 : mainWindow.webContents.send("dictation:state", { state: "RECORDING" });
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
        mainWindow == null ? void 0 : mainWindow.webContents.send("dictation:final", { text: sanitized });
        setClipboardText(sanitized);
        sendPaste();
        showOverlay(`Inserted: ${sanitized.slice(0, 30)}`, "inserted");
      }
      if (event.error) {
        mainWindow == null ? void 0 : mainWindow.webContents.send("dictation:state", { state: "ERROR" });
        showOverlay(event.error.message, "error");
      }
    },
    (error) => {
      mainWindow == null ? void 0 : mainWindow.webContents.send("dictation:state", { state: "ERROR" });
      showOverlay(error.message, "error");
    }
  );
  dictationStream = stream;
  audioController = await createAudioStream({
    sampleRateHz: settings.audio.sampleRateHz,
    channels: settings.audio.channels,
    frameMs: settings.audio.frameMs,
    deviceIndex: settings.audio.deviceIndex
  });
  audioController.onFrame((frame) => {
    dictationStream == null ? void 0 : dictationStream.write(frame);
  });
  audioController.start();
};
var stopDictation = async () => {
  if (!dictationActive) {
    return;
  }
  dictationActive = false;
  mainWindow == null ? void 0 : mainWindow.webContents.send("dictation:state", { state: "PROCESSING" });
  showOverlay("Processing...", "processing");
  audioController == null ? void 0 : audioController.stop();
  dictationStream == null ? void 0 : dictationStream.write({
    audio: Buffer.alloc(0),
    sample_rate_hz: settings.audio.sampleRateHz,
    channels: settings.audio.channels,
    sequence: BigInt(0),
    end_of_stream: true
  });
  dictationStream == null ? void 0 : dictationStream.end();
  dictationStream = null;
  await new Promise((resolve) => setTimeout(resolve, 200));
  hideOverlay();
  mainWindow == null ? void 0 : mainWindow.webContents.send("dictation:state", { state: "IDLE" });
};
var wireIpc = () => {
  import_electron3.ipcMain.handle("settings:get", () => settings);
  import_electron3.ipcMain.handle("settings:save", (_event, next) => {
    settings = next;
    saveSettings(settings);
    return true;
  });
  import_electron3.ipcMain.handle("history:get", () => getHistory());
  import_electron3.ipcMain.handle("cache:get", () => PYTHON_CACHE_PATH);
  import_electron3.ipcMain.handle("dictation:start", () => startDictation());
  import_electron3.ipcMain.handle("dictation:stop", () => stopDictation());
  import_electron3.ipcMain.handle("window:show", () => mainWindow == null ? void 0 : mainWindow.show());
  import_electron3.ipcMain.handle("window:minimize", () => mainWindow == null ? void 0 : mainWindow.hide());
};
var waitForRenderer = () => new Promise((resolve) => {
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
var startApp = async () => {
  createMainWindow();
  createOverlayWindow();
  createTray();
  wireIpc();
  await waitForRenderer();
  mainWindow == null ? void 0 : mainWindow.webContents.send("startup:cache", { path: PYTHON_CACHE_PATH });
  mainWindow == null ? void 0 : mainWindow.webContents.send("backend:status", { ready: false, detail: "Initializing..." });
  mainWindow == null ? void 0 : mainWindow.webContents.send("backend:log", "Initializing backend...");
  await startBackendProcess();
  registerHoldHotkey({
    onActivate: startDictation,
    onDeactivate: stopDictation
  });
};
import_electron3.app.whenReady().then(startApp);
import_electron3.app.on("window-all-closed", () => {
});
import_electron3.app.on("before-quit", () => {
  stopHotkeyListener();
  backendProcess == null ? void 0 : backendProcess.kill();
  tray == null ? void 0 : tray.destroy();
});
//# sourceMappingURL=main.js.map