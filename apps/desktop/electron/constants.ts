import path from "node:path";

export const IS_DEV = process.env.NODE_ENV === "development";

export const APP_ROOT = path.resolve(__dirname, "..");

export const REPO_ROOT = path.resolve(APP_ROOT, "..", "..");

export const ELECTRON_DIR = path.join(APP_ROOT, "electron");
export const PYTHON_CACHE_PATH = "C:\\Users\\willp\\.cache\\huggingface\\transformers";

export const ELECTRON_DIST = path.join(APP_ROOT, "dist-electron");
export const RENDERER_DIST = path.join(APP_ROOT, "dist");
export const RENDERER_DEV_URL = "http://localhost:5173";
export const PROTO_PATH = path.join(REPO_ROOT, "shared", "proto", "dictation.proto");
