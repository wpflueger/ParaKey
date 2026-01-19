import {
  __toESM,
  require_electron
} from "./chunk-FD56QJH3.js";

// electron/preload.ts
var import_electron = __toESM(require_electron(), 1);
import_electron.contextBridge.exposeInMainWorld("keymuse", {
  onBackendLog: (callback) => {
    const handler = (_event, line) => callback(line);
    import_electron.ipcRenderer.on("backend:log", handler);
    return () => import_electron.ipcRenderer.removeListener("backend:log", handler);
  },
  onBackendStatus: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("backend:status", handler);
    return () => import_electron.ipcRenderer.removeListener("backend:status", handler);
  },
  onDictationState: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("dictation:state", handler);
    return () => import_electron.ipcRenderer.removeListener("dictation:state", handler);
  },
  onTranscript: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("dictation:final", handler);
    return () => import_electron.ipcRenderer.removeListener("dictation:final", handler);
  },
  onInstallStatus: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("install:status", handler);
    return () => import_electron.ipcRenderer.removeListener("install:status", handler);
  },
  onStartupError: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("startup:error", handler);
    return () => import_electron.ipcRenderer.removeListener("startup:error", handler);
  },
  onCachePath: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("startup:cache", handler);
    return () => import_electron.ipcRenderer.removeListener("startup:cache", handler);
  },
  getSettings: () => import_electron.ipcRenderer.invoke("settings:get"),
  saveSettings: (settings) => import_electron.ipcRenderer.invoke("settings:save", settings),
  requestHistory: () => import_electron.ipcRenderer.invoke("history:get"),
  requestCachePath: () => import_electron.ipcRenderer.invoke("cache:get"),
  startDictation: () => import_electron.ipcRenderer.invoke("dictation:start"),
  stopDictation: () => import_electron.ipcRenderer.invoke("dictation:stop"),
  showMainWindow: () => import_electron.ipcRenderer.invoke("window:show"),
  minimizeToTray: () => import_electron.ipcRenderer.invoke("window:minimize")
});
//# sourceMappingURL=preload.js.map