import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["electron/main.ts", "electron/preload.ts", "electron/overlay-preload.ts"],
  format: ["cjs"],
  platform: "node",
  target: "node16",
  outDir: "dist-electron",
  sourcemap: true,
  external: [
    "electron",
    "@grpc/grpc-js",
    "@grpc/proto-loader",
    "naudiodon",
    "uiohook-napi",
    "electron-rebuild",
    "electron-updater",
  ],
});
