import {
  __toESM,
  require_electron
} from "./chunk-FD56QJH3.js";

// electron/overlay-preload.ts
var import_electron = __toESM(require_electron(), 1);
import_electron.contextBridge.exposeInMainWorld("overlay", {
  onState: (callback) => {
    const handler = (_event, payload) => callback(payload);
    import_electron.ipcRenderer.on("overlay:update", handler);
    return () => import_electron.ipcRenderer.removeListener("overlay:update", handler);
  }
});
//# sourceMappingURL=overlay-preload.js.map