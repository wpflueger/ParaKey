var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// electron/main.ts
var import_electron4 = require("electron");
var import_node_fs3 = __toESM(require("fs"), 1);
var import_node_path5 = __toESM(require("path"), 1);

// electron/grpc-client.ts
var import_grpc_js = require("@grpc/grpc-js");
var encodeJson = (payload) => Buffer.from(JSON.stringify(payload), "utf-8");
var decodeJson = (data) => {
  if (!data || data.length === 0) {
    return {};
  }
  return JSON.parse(data.toString("utf-8"));
};
var serializeAudioFrame = (frame) => encodeJson({
  audio: frame.audio.toString("base64"),
  sample_rate_hz: frame.sample_rate_hz,
  channels: frame.channels,
  sequence: frame.sequence.toString(),
  end_of_stream: frame.end_of_stream
});
var deserializeDictationEvent = (data) => {
  const payload = decodeJson(data);
  return {
    partial: typeof payload.partial === "object" && payload.partial ? { text: String(payload.partial.text ?? "") } : void 0,
    final: typeof payload.final === "object" && payload.final ? {
      text: String(payload.final.text ?? ""),
      from_cache: Boolean(payload.final.from_cache)
    } : void 0,
    status: typeof payload.status === "object" && payload.status ? {
      mode: String(payload.status.mode ?? ""),
      detail: String(payload.status.detail ?? "")
    } : void 0,
    error: typeof payload.error === "object" && payload.error ? {
      code: String(payload.error.code ?? ""),
      message: String(payload.error.message ?? "")
    } : void 0
  };
};
var deserializeHealthStatus = (data) => {
  const payload = decodeJson(data);
  return {
    ready: Boolean(payload.ready),
    mode: String(payload.mode ?? ""),
    detail: String(payload.detail ?? "")
  };
};
var createDictationClient = (host, port) => {
  const methods = {
    StreamAudio: {
      path: "/keymuse.dictation.v1.DictationService/StreamAudio",
      requestStream: true,
      responseStream: true,
      requestSerialize: serializeAudioFrame,
      requestDeserialize: () => ({}),
      responseSerialize: encodeJson,
      responseDeserialize: deserializeDictationEvent
    },
    GetHealth: {
      path: "/keymuse.dictation.v1.DictationService/GetHealth",
      requestStream: false,
      responseStream: false,
      requestSerialize: () => encodeJson({}),
      requestDeserialize: () => ({}),
      responseSerialize: encodeJson,
      responseDeserialize: deserializeHealthStatus
    }
  };
  const ClientCtor = (0, import_grpc_js.makeGenericClientConstructor)(methods, "DictationService");
  const client = new ClientCtor(`${host}:${port}`, import_grpc_js.credentials.createInsecure());
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
var streamAudio = (client, onEvent, onError) => {
  const stream = client.StreamAudio();
  stream.on("data", (event) => onEvent(event));
  stream.on("error", (error) => onError(error));
  return stream;
};

// electron/audio.ts
var createAudioStream = async (options) => {
  let portAudioModule;
  try {
    portAudioModule = await import("naudiodon");
  } catch (error) {
    throw new Error(
      "Audio capture library failed to load. Rebuild native modules (naudiodon) for Electron.",
      { cause: error }
    );
  }
  const portAudio = portAudioModule;
  const frameSamples = Math.round(options.sampleRateHz * options.frameMs / 1e3);
  const frameBytes = frameSamples * options.channels * 2;
  const input = new portAudio.AudioIO({
    inOptions: {
      channelCount: options.channels,
      sampleFormat: portAudio.SampleFormat16Bit,
      sampleRate: options.sampleRateHz,
      deviceId: options.deviceIndex ?? -1,
      closeOnError: true
    }
  });
  let sequence = BigInt(0);
  let onFrame = null;
  let buffer = Buffer.alloc(0);
  const flushBuffer = () => {
    if (buffer.length > 0 && onFrame) {
      const paddedFrame = Buffer.alloc(frameBytes);
      buffer.copy(paddedFrame, 0, 0, buffer.length);
      onFrame({
        audio: paddedFrame,
        sample_rate_hz: options.sampleRateHz,
        channels: options.channels,
        sequence: sequence++,
        end_of_stream: false
      });
      buffer = Buffer.alloc(0);
    }
  };
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
    stop: () => {
      flushBuffer();
      input.quit();
    },
    onFrame: (callback) => {
      onFrame = callback;
    }
  };
};

// electron/native-deps.ts
var import_node_child_process = require("child_process");
var import_node_module = require("module");

// electron/constants.ts
var import_electron = require("electron");
var import_node_os = __toESM(require("os"), 1);
var import_node_path = __toESM(require("path"), 1);
var IS_DEV = process.env.NODE_ENV === "development";
var APP_ROOT = import_node_path.default.resolve(__dirname, "..");
var RESOURCES_ROOT = import_electron.app.isPackaged ? process.resourcesPath : import_node_path.default.resolve(APP_ROOT, "..", "..");
var BACKEND_ROOT = import_node_path.default.join(RESOURCES_ROOT, "backend");
var SHARED_ROOT = import_node_path.default.join(RESOURCES_ROOT, "shared");
var ELECTRON_DIR = import_node_path.default.join(APP_ROOT, "electron");
var PYTHON_CACHE_PATH = import_node_path.default.join(
  import_node_os.default.homedir(),
  ".cache",
  "huggingface",
  "transformers"
);
var ELECTRON_DIST = import_node_path.default.join(APP_ROOT, "dist-electron");
var RENDERER_DIST = import_node_path.default.join(APP_ROOT, "dist");
var RENDERER_DEV_URL = "http://localhost:5173";
var PROTO_PATH = import_node_path.default.join(SHARED_ROOT, "proto", "dictation.proto");

// electron/native-deps.ts
var resolveRebuildBinary = () => {
  try {
    const require2 = (0, import_node_module.createRequire)(__filename);
    return require2.resolve("electron-rebuild/lib/cli.js");
  } catch {
    return null;
  }
};
var tryImportNaudiodon = async () => {
  try {
    await import("naudiodon");
    return true;
  } catch {
    return false;
  }
};
var ensureNativeAudioDeps = async (onLog) => {
  if (await tryImportNaudiodon()) {
    return { ok: true, attemptedRebuild: false };
  }
  onLog == null ? void 0 : onLog("Audio dependency missing. Attempting to rebuild naudiodon...");
  const rebuildPath = resolveRebuildBinary();
  if (!rebuildPath) {
    onLog == null ? void 0 : onLog("electron-rebuild not found. Run bun run rebuild:native manually.");
    return { ok: false, attemptedRebuild: false };
  }
  return new Promise((resolve) => {
    var _a, _b;
    const child = (0, import_node_child_process.spawn)(process.execPath, [rebuildPath, "-f", "-w", "naudiodon"], {
      cwd: APP_ROOT,
      env: process.env,
      windowsHide: true
    });
    (_a = child.stdout) == null ? void 0 : _a.on("data", (data) => {
      onLog == null ? void 0 : onLog(data.toString().trim());
    });
    (_b = child.stderr) == null ? void 0 : _b.on("data", (data) => {
      onLog == null ? void 0 : onLog(data.toString().trim());
    });
    child.on("exit", async (code) => {
      if (code === 0 && await tryImportNaudiodon()) {
        onLog == null ? void 0 : onLog("naudiodon rebuild complete.");
        resolve({ ok: true, attemptedRebuild: true });
        return;
      }
      onLog == null ? void 0 : onLog("naudiodon rebuild failed. Try setting PYTHON to Python 3.11 or installing setuptools, then run bun run rebuild:native.");
      resolve({ ok: false, attemptedRebuild: true });
    });
  });
};

// electron/hotkeys.ts
var import_uiohook_napi = require("uiohook-napi");
var MODIFIER_VARIANTS = {
  29: /* @__PURE__ */ new Set([29, 3613]),
  // Ctrl (left: 29, right: 3613)
  42: /* @__PURE__ */ new Set([42, 3638]),
  // Shift (left: 42, right: 3638)
  56: /* @__PURE__ */ new Set([56, 3640]),
  // Alt (left: 56, right: 3640)
  3675: /* @__PURE__ */ new Set([3675, 3676])
  // Win (left: 3675, right: 3676)
};
var key1Codes = /* @__PURE__ */ new Set();
var key2Codes = /* @__PURE__ */ new Set();
var updateHotkeyConfig = (preset) => {
  switch (preset) {
    case "ctrl+alt":
      key1Codes = MODIFIER_VARIANTS[29];
      key2Codes = MODIFIER_VARIANTS[56];
      break;
    case "ctrl+shift":
      key1Codes = MODIFIER_VARIANTS[29];
      key2Codes = MODIFIER_VARIANTS[42];
      break;
    case "alt+shift":
      key1Codes = MODIFIER_VARIANTS[56];
      key2Codes = MODIFIER_VARIANTS[42];
      break;
    case "win+alt":
      key1Codes = MODIFIER_VARIANTS[3675];
      key2Codes = MODIFIER_VARIANTS[56];
      break;
  }
};
var registerHoldHotkey = ({ onActivate, onDeactivate }, preset = "ctrl+alt") => {
  updateHotkeyConfig(preset);
  let key1Down = false;
  let key2Down = false;
  let active = false;
  const updateState = () => {
    const shouldBeActive = key1Down && key2Down;
    if (shouldBeActive && !active) {
      active = true;
      onActivate();
    } else if (!shouldBeActive && active) {
      active = false;
      onDeactivate();
    }
  };
  import_uiohook_napi.uIOhook.on("keydown", (event) => {
    if (key1Codes.has(event.keycode)) {
      key1Down = true;
    }
    if (key2Codes.has(event.keycode)) {
      key2Down = true;
    }
    updateState();
  });
  import_uiohook_napi.uIOhook.on("keyup", (event) => {
    if (key1Codes.has(event.keycode)) {
      key1Down = false;
    }
    if (key2Codes.has(event.keycode)) {
      key2Down = false;
    }
    updateState();
  });
  import_uiohook_napi.uIOhook.start();
};
var stopHotkeyListener = () => {
  import_uiohook_napi.uIOhook.removeAllListeners();
  import_uiohook_napi.uIOhook.stop();
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
var import_electron2 = require("electron");
var import_uiohook_napi2 = require("uiohook-napi");
var CONTROL_PATTERN = /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g;
var BIDI_PATTERN = new RegExp("[\\u200E\\u200F\\u202A-\\u202E\\u2066-\\u2069]", "g");
var previousClipboardText = null;
var sanitizeText = (text) => {
  let sanitized = text.replace(CONTROL_PATTERN, "").replace(BIDI_PATTERN, "");
  sanitized = sanitized.normalize("NFC");
  sanitized = sanitized.replace(/\r\n/g, "\n").replace(/\r/g, "\n").replace(/\n/g, "\r\n");
  sanitized = sanitized.trimEnd() + " ";
  return sanitized;
};
var setClipboardText = (text) => {
  previousClipboardText = import_electron2.clipboard.readText();
  import_electron2.clipboard.writeText(text);
};
var sendPaste = () => {
  setTimeout(() => {
    import_uiohook_napi2.uIOhook.keyTap(import_uiohook_napi2.UiohookKey.V, [import_uiohook_napi2.UiohookKey.Ctrl]);
    setTimeout(() => {
      if (previousClipboardText !== null) {
        import_electron2.clipboard.writeText(previousClipboardText);
        previousClipboardText = null;
      } else {
        import_electron2.clipboard.clear();
      }
    }, 100);
  }, 50);
};

// electron/settings.ts
var import_electron3 = require("electron");
var import_node_fs = __toESM(require("fs"), 1);
var import_node_path2 = __toESM(require("path"), 1);
var HOTKEY_PRESETS = {
  "ctrl+alt": [29, 56],
  // Ctrl + Alt
  "ctrl+shift": [29, 42],
  // Ctrl + Shift
  "alt+shift": [56, 42],
  // Alt + Shift
  "win+alt": [3675, 56]
  // Win + Alt
};
var DEFAULT_SETTINGS = {
  hotkey: {
    preset: "ctrl+alt",
    modifiers: HOTKEY_PRESETS["ctrl+alt"],
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
var getSettingsPath = () => import_node_path2.default.join(import_electron3.app.getPath("userData"), SETTINGS_FILE);
var loadSettings = () => {
  const filePath = getSettingsPath();
  try {
    if (!import_node_fs.default.existsSync(filePath)) {
      return { ...DEFAULT_SETTINGS };
    }
    const raw = import_node_fs.default.readFileSync(filePath, "utf-8");
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
  import_node_fs.default.mkdirSync(import_node_path2.default.dirname(filePath), { recursive: true });
  import_node_fs.default.writeFileSync(filePath, payload, "utf-8");
};

// electron/python-finder.ts
var import_node_path3 = __toESM(require("path"), 1);
var import_node_child_process2 = require("child_process");
var import_node_fs2 = __toESM(require("fs"), 1);
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
    const result = (0, import_node_child_process2.spawnSync)(pythonPath, ["-c", code], {
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
var checkGrpc = (pythonPath) => runPythonCheck(pythonPath, "import grpc; print('ok')") === "ok";
var checkCuda = (pythonPath) => runPythonCheck(pythonPath, "import torch; print('ok' if torch.cuda.is_available() else 'no')") === "ok";
var isValidPython = (version) => {
  if (!version) {
    return false;
  }
  const [major, minor] = version.split(".").map((part) => Number(part));
  if (!Number.isFinite(major) || !Number.isFinite(minor)) {
    return false;
  }
  return major === 3 && (minor === 11 || minor === 12);
};
var getPythonInfo = (pythonPath, checkDeps) => {
  if (!import_node_fs2.default.existsSync(pythonPath)) {
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
    hasGrpc: false,
    hasCuda: false
  };
  if (checkDeps) {
    info.hasTorch = checkTorch(pythonPath);
    info.hasNemo = checkNemo(pythonPath);
    info.hasGrpc = checkGrpc(pythonPath);
    if (info.hasTorch) {
      info.hasCuda = checkCuda(pythonPath);
    }
  }
  return info;
};
var getPythonInfoForExecutable = (pythonPath, checkDeps) => getPythonInfo(pythonPath, checkDeps);
var resolveVenvPython = (venvRoot) => {
  return process.platform === "win32" ? import_node_path3.default.join(venvRoot, "Scripts", "python.exe") : import_node_path3.default.join(venvRoot, "bin", "python");
};
var ensureVenv = (pythonPath, venvRoot) => {
  const venvPython = resolveVenvPython(venvRoot);
  if (!import_node_fs2.default.existsSync(venvPython)) {
    (0, import_node_child_process2.execFileSync)(pythonPath, ["-m", "venv", venvRoot], { stdio: "inherit" });
  }
  return venvPython;
};
var findEnvPython = () => {
  const envPython = process.env.KEYMUSE_PYTHON;
  if (envPython && import_node_fs2.default.existsSync(envPython)) {
    return envPython;
  }
  return null;
};
var findVenvPython = (appRoot) => {
  const searchPaths = [
    import_node_path3.default.join(appRoot, ".venv", "Scripts", "python.exe"),
    import_node_path3.default.join(appRoot, "..", ".venv", "Scripts", "python.exe"),
    import_node_path3.default.join(appRoot, "..", "..", ".venv", "Scripts", "python.exe")
  ];
  for (const candidate of searchPaths) {
    if (import_node_fs2.default.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
};
var findPathPython = () => {
  const command = process.platform === "win32" ? "where" : "which";
  try {
    const output = (0, import_node_child_process2.execFileSync)(command, ["python"], { encoding: "utf-8" }).trim();
    const first = output.split(/\r?\n/)[0];
    if (first && import_node_fs2.default.existsSync(first)) {
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
      const output = (0, import_node_child_process2.execFileSync)("py", [`-${version}`, "-c", "import sys; print(sys.executable)"], {
        encoding: "utf-8",
        windowsHide: true
      }).trim();
      if (output && import_node_fs2.default.existsSync(output)) {
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
    localAppData && import_node_path3.default.join(localAppData, "Programs", "Python"),
    "C:/Python312",
    "C:/Python311",
    "C:/Program Files/Python312",
    "C:/Program Files/Python311"
  ].filter(Boolean);
  for (const base of candidates) {
    if (!import_node_fs2.default.existsSync(base)) {
      continue;
    }
    const direct = import_node_path3.default.join(base, "python.exe");
    if (import_node_fs2.default.existsSync(direct)) {
      return direct;
    }
    try {
      const subdirs = import_node_fs2.default.readdirSync(base, { withFileTypes: true });
      for (const sub of subdirs) {
        if (sub.isDirectory() && sub.name.startsWith("Python")) {
          const candidate = import_node_path3.default.join(base, sub.name, "python.exe");
          if (import_node_fs2.default.existsSync(candidate)) {
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
    if (!checkDeps || info.hasTorch && info.hasNemo && info.hasGrpc) {
      return info;
    }
    if (!found) {
      found = info;
    }
  }
  if (found) {
    const missing = [
      !found.hasTorch && "torch",
      !found.hasNemo && "nemo",
      !found.hasGrpc && "grpc"
    ].filter(Boolean).join(", ");
    throw new BackendDepsError(
      `Python found but missing backend dependencies: ${missing}.`,
      found.executable
    );
  }
  throw new PythonNotFoundError(
    "Python 3.11+ not found. Install Python or set KEYMUSE_PYTHON to your Python executable."
  );
};
var runPipInstall = (pythonPath, args, tempDir, onOutput) => {
  return new Promise((resolve, reject) => {
    var _a, _b;
    const child = (0, import_node_child_process2.spawn)(pythonPath, ["-m", "pip", "install", ...args], {
      windowsHide: true,
      env: {
        ...process.env,
        ...tempDir ? { TEMP: tempDir, TMP: tempDir } : {},
        PIP_DISABLE_PIP_VERSION_CHECK: "1"
      }
    });
    const handleOutput = (data) => {
      const text = data.toString();
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) {
          continue;
        }
        onOutput == null ? void 0 : onOutput(line.trim());
      }
    };
    (_a = child.stdout) == null ? void 0 : _a.on("data", handleOutput);
    (_b = child.stderr) == null ? void 0 : _b.on("data", handleOutput);
    child.on("error", (error) => reject(error));
    child.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`pip install exited with code ${code}`));
      }
    });
  });
};
var installBackendDepsAsync = async (pythonPath, backendRoot, tempDir, onOutput) => {
  const requirements = import_node_path3.default.join(backendRoot, "requirements.txt");
  if (tempDir) {
    import_node_fs2.default.mkdirSync(tempDir, { recursive: true });
  }
  await runPipInstall(pythonPath, ["-r", requirements], tempDir, onOutput);
  onOutput == null ? void 0 : onOutput("Ensuring numpy compatibility...");
  await runPipInstall(pythonPath, ["numpy>=1.26.0,<2", "--force-reinstall"], tempDir, onOutput);
};

// electron/backend.ts
var import_node_child_process3 = require("child_process");
var import_node_path4 = __toESM(require("path"), 1);
var buildPythonPath = () => {
  const paths = [
    import_node_path4.default.join(SHARED_ROOT, "src"),
    import_node_path4.default.join(BACKEND_ROOT, "src")
  ];
  const existing = process.env.PYTHONPATH;
  if (existing) {
    paths.push(existing);
  }
  return paths.join(import_node_path4.default.delimiter);
};
var startBackend = (python, options) => {
  var _a, _b;
  const env = {
    ...process.env,
    PYTHONPATH: buildPythonPath(),
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
  const child = (0, import_node_child_process3.spawn)(python.executable, cmd, {
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
var backendReady = false;
var audioController = null;
var dictationStream = null;
var dictationActive = false;
var isQuitting = false;
var sendToMain = (channel, ...args) => {
  try {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(channel, ...args);
    }
  } catch {
  }
};
var getIconPath = () => {
  return IS_DEV ? import_node_path5.default.join(APP_ROOT, "public", "icons", "app.ico") : import_node_path5.default.join(RENDERER_DIST, "icons", "app.ico");
};
var getTrayIconPath = () => {
  const trayFile = "tray-32.png";
  return IS_DEV ? import_node_path5.default.join(APP_ROOT, "public", "icons", trayFile) : import_node_path5.default.join(RENDERER_DIST, "icons", trayFile);
};
var createMainWindow = () => {
  const iconPath = getIconPath();
  mainWindow = new import_electron4.BrowserWindow({
    width: 420,
    height: 620,
    minWidth: 380,
    minHeight: 520,
    show: !settings.startMinimized,
    backgroundColor: "#f8f4ed",
    icon: iconPath,
    webPreferences: {
      preload: import_node_path5.default.join(APP_ROOT, "dist-electron", "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  if (IS_DEV) {
    mainWindow.loadURL(RENDERER_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(import_node_path5.default.join(RENDERER_DIST, "index.html"));
  }
  mainWindow.on("close", (event) => {
    if (tray && !isQuitting) {
      event.preventDefault();
      mainWindow == null ? void 0 : mainWindow.hide();
    }
  });
};
var createOverlayWindow = () => {
  overlayWindow = new import_electron4.BrowserWindow({
    width: 260,
    height: 50,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    show: false,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: import_node_path5.default.join(APP_ROOT, "dist-electron", "overlay-preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  overlayWindow.setIgnoreMouseEvents(true);
  overlayWindow.loadFile(import_node_path5.default.join(ELECTRON_DIST, "overlay.html"));
};
var positionOverlay = (mode) => {
  if (!overlayWindow) {
    return;
  }
  const { xOffset, yOffset } = settings.overlay;
  const { width, height } = overlayWindow.getBounds();
  const { width: screenW, height: screenH } = import_electron4.screen.getPrimaryDisplay().workAreaSize;
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
  const iconPath = getTrayIconPath();
  console.log("Loading tray icon from:", iconPath);
  const trayImage = import_electron4.nativeImage.createFromPath(iconPath);
  if (trayImage.isEmpty()) {
    console.warn("Tray icon could not be loaded from:", iconPath);
    try {
      tray = new import_electron4.Tray(import_electron4.nativeImage.createEmpty());
    } catch {
      console.error("Failed to create tray");
      return;
    }
  } else {
    tray = new import_electron4.Tray(trayImage);
  }
  const contextMenu = import_electron4.Menu.buildFromTemplate([
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
      click: () => import_electron4.app.quit()
    }
  ]);
  tray.setToolTip("KeyMuse - Press Ctrl+Alt to dictate");
  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => mainWindow == null ? void 0 : mainWindow.show());
};
var ensureBackend = async () => {
  const updateStatus = (payload) => {
    sendToMain("install:status", payload);
    sendToMain("backend:status", { ready: false, detail: payload.status });
    sendToMain("backend:log", payload.status);
  };
  const pipTempDir = import_node_path5.default.join(import_electron4.app.getPath("userData"), "pip-temp");
  try {
    const venvRoot = import_node_path5.default.join(import_electron4.app.getPath("userData"), "python", ".venv");
    const venvPython = resolveVenvPython(venvRoot);
    const venvInfo = getPythonInfoForExecutable(venvPython, true);
    if (venvInfo) {
      return venvInfo;
    }
    if (import_node_fs3.default.existsSync(venvPython)) {
      sendToMain(
        "backend:log",
        "Existing Python environment uses an unsupported version. Recreating..."
      );
      import_node_fs3.default.rmSync(venvRoot, { recursive: true, force: true });
    }
    const basePython = findPython(APP_ROOT, false);
    const venvExecutable = ensureVenv(basePython.executable, venvRoot);
    updateStatus({ status: "Preparing Python environment..." });
    await installBackendDepsAsync(venvExecutable, BACKEND_ROOT, pipTempDir, (line) => {
      sendToMain("backend:log", line);
    });
    const ready = getPythonInfoForExecutable(venvExecutable, true);
    if (ready) {
      return ready;
    }
    throw new BackendDepsError(
      "Python environment created but backend dependencies failed to install.",
      venvExecutable
    );
  } catch (error) {
    if (error instanceof BackendDepsError) {
      import_electron4.dialog.showMessageBox({
        type: "info",
        title: "Installing Dependencies",
        message: "Python dependencies are missing. KeyMuse will install the required packages now."
      });
      updateStatus({ status: "Missing Python dependencies. Installing..." });
      await installBackendDepsAsync(error.pythonPath, BACKEND_ROOT, pipTempDir, (line) => {
        sendToMain("backend:log", line);
      });
      const venvInfo = getPythonInfoForExecutable(error.pythonPath, true);
      if (venvInfo) {
        return venvInfo;
      }
      return findPython(APP_ROOT, true);
    }
    if (error instanceof PythonNotFoundError) {
      import_electron4.dialog.showErrorBox(
        "Python Required",
        "Python 3.11+ is required to run the speech model. Install Python and restart KeyMuse."
      );
      sendToMain("startup:error", {
        message: "Python 3.11+ not found. Install Python and restart KeyMuse."
      });
    }
    throw error;
  }
};
var startBackendProcess = async () => {
  const nativeDeps = await ensureNativeAudioDeps((line) => {
    sendToMain("backend:log", line);
  });
  if (!nativeDeps.ok) {
    sendToMain(
      "backend:log",
      "Audio capture will be unavailable until native modules rebuild successfully."
    );
    sendToMain(
      "backend:log",
      "Tip: set PYTHON to Python 3.11 or install setuptools for your Python 3.12 runtime."
    );
  }
  const python = await ensureBackend();
  sendToMain("backend:log", `Using Python: ${python.executable}`);
  const backend = startBackend(python, {
    host: settings.backend.host,
    port: settings.backend.port,
    onOutput: (line) => {
      sendToMain("backend:log", line);
      if (!backendReady) {
        sendToMain("backend:status", {
          ready: false,
          detail: line
        });
      }
    }
  });
  backendProcess = backend;
  let backendExited = false;
  backend.process.on("exit", (code) => {
    backendExited = true;
    const message = `Backend exited with code ${code ?? "unknown"}.`;
    sendToMain("backend:log", message);
    sendToMain("backend:status", { ready: false, detail: message });
  });
  const grpc = createDictationClient(settings.backend.host, settings.backend.port);
  let ready = false;
  let attempts = 0;
  while (!ready) {
    try {
      const health = await grpc.GetHealth({});
      sendToMain("backend:status", { ready: health.ready, detail: health.detail });
      ready = health.ready;
      backendReady = health.ready;
      if (!ready) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    } catch (error) {
      if (backendExited) {
        throw error;
      }
      attempts += 1;
      const message = "Waiting for backend...";
      sendToMain("backend:status", {
        ready: false,
        detail: message
      });
      if (attempts === 1) {
        const errorMessage = error instanceof Error ? error.message : "Health check failed";
        sendToMain("backend:log", `Health check failed: ${errorMessage}`);
      } else if (attempts % 5 === 0) {
        sendToMain("backend:log", `${message} (${attempts})`);
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
};
var startDictation = async () => {
  if (dictationActive) {
    return;
  }
  dictationActive = true;
  sendToMain("dictation:state", { state: "RECORDING" });
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
        sendToMain("dictation:final", { text: sanitized });
        setClipboardText(sanitized);
        sendPaste();
        showOverlay(`Inserted: ${sanitized.slice(0, 30)}`, "inserted");
      }
      if (event.error) {
        sendToMain("dictation:state", { state: "ERROR" });
        showOverlay(event.error.message, "error");
      }
    },
    (error) => {
      sendToMain("dictation:state", { state: "ERROR" });
      showOverlay(error.message, "error");
    }
  );
  dictationStream = stream;
  try {
    audioController = await createAudioStream({
      sampleRateHz: settings.audio.sampleRateHz,
      channels: settings.audio.channels,
      frameMs: settings.audio.frameMs,
      deviceIndex: settings.audio.deviceIndex
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Audio capture failed.";
    sendToMain("backend:log", message);
    sendToMain("dictation:state", { state: "ERROR" });
    showOverlay(message, "error");
    return;
  }
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
  sendToMain("dictation:state", { state: "PROCESSING" });
  showOverlay("Processing...", "processing");
  await new Promise((resolve) => setTimeout(resolve, 150));
  audioController == null ? void 0 : audioController.stop();
  dictationStream == null ? void 0 : dictationStream.write({
    audio: Buffer.alloc(0),
    sample_rate_hz: settings.audio.sampleRateHz,
    channels: settings.audio.channels,
    sequence: BigInt(0),
    end_of_stream: true
  });
  dictationStream == null ? void 0 : dictationStream.end();
  const stream = dictationStream;
  if (stream) {
    await new Promise((resolve) => {
      const timeout = setTimeout(() => {
        sendToMain("backend:log", "Transcription timeout");
        resolve();
      }, 3e4);
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
  sendToMain("dictation:state", { state: "IDLE" });
};
var wireIpc = () => {
  import_electron4.ipcMain.handle("settings:get", () => settings);
  import_electron4.ipcMain.handle("settings:save", (_event, next) => {
    settings = next;
    saveSettings(settings);
    return true;
  });
  import_electron4.ipcMain.handle("history:get", () => getHistory());
  import_electron4.ipcMain.handle("cache:get", () => PYTHON_CACHE_PATH);
  import_electron4.ipcMain.handle("dictation:start", () => startDictation());
  import_electron4.ipcMain.handle("dictation:stop", () => stopDictation());
  import_electron4.ipcMain.handle("window:show", () => mainWindow == null ? void 0 : mainWindow.show());
  import_electron4.ipcMain.handle("window:minimize", () => mainWindow == null ? void 0 : mainWindow.hide());
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
  import_electron4.Menu.setApplicationMenu(null);
  createMainWindow();
  createOverlayWindow();
  createTray();
  wireIpc();
  await waitForRenderer();
  sendToMain("startup:cache", { path: PYTHON_CACHE_PATH });
  sendToMain("backend:status", { ready: false, detail: "Initializing..." });
  sendToMain("backend:log", "Initializing backend...");
  await startBackendProcess();
  registerHoldHotkey(
    {
      onActivate: startDictation,
      onDeactivate: stopDictation
    },
    settings.hotkey.preset
  );
};
process.on("unhandledRejection", (reason) => {
  const message = reason instanceof Error ? reason.message : "Unhandled rejection";
  sendToMain("backend:log", `Unhandled: ${message}`);
});
import_electron4.app.whenReady().then(startApp);
import_electron4.app.on("window-all-closed", () => {
});
import_electron4.app.on("before-quit", () => {
  isQuitting = true;
  stopHotkeyListener();
  backendProcess == null ? void 0 : backendProcess.kill();
  tray == null ? void 0 : tray.destroy();
});
//# sourceMappingURL=main.cjs.map