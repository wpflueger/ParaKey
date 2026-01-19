import { contextBridge, ipcRenderer } from "electron";
import type { AppSettings } from "./settings";

contextBridge.exposeInMainWorld("keymuse", {
  onBackendLog: (callback: (line: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, line: string) => callback(line);
    ipcRenderer.on("backend:log", handler);
    return () => ipcRenderer.removeListener("backend:log", handler);
  },
  onBackendStatus: (callback: (payload: { ready: boolean; detail: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { ready: boolean; detail: string }) =>
      callback(payload);
    ipcRenderer.on("backend:status", handler);
    return () => ipcRenderer.removeListener("backend:status", handler);
  },
  onDictationState: (callback: (payload: { state: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { state: string }) => callback(payload);
    ipcRenderer.on("dictation:state", handler);
    return () => ipcRenderer.removeListener("dictation:state", handler);
  },
  onTranscript: (callback: (payload: { text: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { text: string }) => callback(payload);
    ipcRenderer.on("dictation:final", handler);
    return () => ipcRenderer.removeListener("dictation:final", handler);
  },
  onInstallStatus: (callback: (payload: { status: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { status: string }) => callback(payload);
    ipcRenderer.on("install:status", handler);
    return () => ipcRenderer.removeListener("install:status", handler);
  },
  onStartupError: (callback: (payload: { message: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { message: string }) => callback(payload);
    ipcRenderer.on("startup:error", handler);
    return () => ipcRenderer.removeListener("startup:error", handler);
  },
  onCachePath: (callback: (payload: { path: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { path: string }) => callback(payload);
    ipcRenderer.on("startup:cache", handler);
    return () => ipcRenderer.removeListener("startup:cache", handler);
  },
  getSettings: () => ipcRenderer.invoke("settings:get") as Promise<AppSettings>,
  saveSettings: (settings: AppSettings) => ipcRenderer.invoke("settings:save", settings),
  requestHistory: () => ipcRenderer.invoke("history:get") as Promise<string[]>,
  requestCachePath: () => ipcRenderer.invoke("cache:get") as Promise<string>,
  startDictation: () => ipcRenderer.invoke("dictation:start"),
  stopDictation: () => ipcRenderer.invoke("dictation:stop"),
  showMainWindow: () => ipcRenderer.invoke("window:show"),
  minimizeToTray: () => ipcRenderer.invoke("window:minimize"),
});
