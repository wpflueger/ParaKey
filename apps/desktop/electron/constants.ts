import { app } from "electron";
import os from "node:os";
import path from "node:path";

export const IS_DEV = process.env.NODE_ENV === "development";

export const APP_ROOT = path.resolve(__dirname, "..");

export const RESOURCES_ROOT = app.isPackaged
	? process.resourcesPath
	: path.resolve(APP_ROOT, "..", "..");

export const BACKEND_ROOT = path.join(RESOURCES_ROOT, "backend");
export const SHARED_ROOT = path.join(RESOURCES_ROOT, "shared");

export const ELECTRON_DIR = path.join(APP_ROOT, "electron");
export const PYTHON_CACHE_PATH = path.join(
	os.homedir(),
	".cache",
	"huggingface",
	"transformers",
);

export const ELECTRON_DIST = path.join(APP_ROOT, "dist-electron");
export const RENDERER_DIST = path.join(APP_ROOT, "dist");
export const RENDERER_DEV_URL = "http://localhost:5173";
export const PROTO_PATH = path.join(SHARED_ROOT, "proto", "dictation.proto");
