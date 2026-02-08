import { app } from "electron";
import fs from "node:fs";
import path from "node:path";

const MAX_HISTORY = 10;

let history: string[] = [];
let loaded = false;

const getHistoryPath = (): string =>
  path.join(app.getPath("userData"), "history.json");

const loadHistory = (): string[] => {
  try {
    const data = fs.readFileSync(getHistoryPath(), "utf-8");
    const parsed: unknown = JSON.parse(data);
    if (
      Array.isArray(parsed) &&
      parsed.every((item) => typeof item === "string")
    ) {
      return parsed.slice(-MAX_HISTORY);
    }
    return [];
  } catch {
    return [];
  }
};

const persistHistory = (): void => {
  try {
    const filePath = getHistoryPath();
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(history), "utf-8");
  } catch (error) {
    console.warn("Failed to persist history:", error);
  }
};

const ensureLoaded = (): void => {
  if (!loaded) {
    history = loadHistory();
    loaded = true;
  }
};

export const addTranscript = (text: string): void => {
  ensureLoaded();
  history = [...history, text].slice(-MAX_HISTORY);
  persistHistory();
};

export const getHistory = (): string[] => {
  ensureLoaded();
  return [...history];
};

export const getLastTranscript = (): string | null => {
  ensureLoaded();
  if (history.length === 0) {
    return null;
  }
  return history[history.length - 1];
};

export const clearHistory = (): void => {
  history = [];
  loaded = true;
  persistHistory();
};
