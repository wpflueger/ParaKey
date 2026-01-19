import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("overlay", {
  onState: (callback: (payload: { text: string; mode: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: { text: string; mode: string }) =>
      callback(payload);
    ipcRenderer.on("overlay:update", handler);
    return () => ipcRenderer.removeListener("overlay:update", handler);
  },
});
