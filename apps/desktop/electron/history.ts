import { app } from "electron";
import fs from "node:fs";
import path from "node:path";

const MAX_HISTORY = 10;

let history: string[] | null = null;

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
      return (parsed as string[]).slice(-MAX_HISTORY);
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
  } catch {
    // Silently ignore write errors
  }
};

const ensureLoaded = (): void => {
  if (history === null) {
    history = loadHistory();
  }
};

export const addTranscript = (text: string): void => {
  ensureLoaded();
  history = [...(history as string[]), text].slice(-MAX_HISTORY);
  persistHistory();
};

export const getHistory = (): string[] => {
  ensureLoaded();
  return [...(history as string[])];
};

export const getLastTranscript = (): string | null => {
  ensureLoaded();
  if ((history as string[]).length === 0) {
    return null;
  }
  return (history as string[])[(history as string[]).length - 1];
};

export const clearHistory = (): void => {
  history = [];
  persistHistory();
};
