// electron/overlay-preload.ts
var import_electron = require("electron");
import_electron.contextBridge.exposeInMainWorld("overlay", {
  onState: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("overlay:update", handler);
    return () => import_electron.ipcRenderer.removeListener("overlay:update", handler);
  }
});
//# sourceMappingURL=overlay-preload.cjs.map