import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { app } from "electron";
import { BackendDepsError } from "./python-finder";
import type { PythonInfo } from "./python-finder";
import { BACKEND_ROOT, SHARED_ROOT } from "./constants";

const getPidFilePath = (): string => path.join(app.getPath("userData"), "backend.pid");

const writePidFile = (pid: number): void => {
  fs.writeFileSync(getPidFilePath(), String(pid), "utf-8");
};

const removePidFile = (): void => {
  try {
    fs.unlinkSync(getPidFilePath());
  } catch {
    // File may not exist
  }
};

/**
 * Kill any orphaned backend process from a previous non-graceful exit.
 * Reads the PID file and sends SIGTERM if the process is still alive.
 */
export const cleanupOrphanedBackend = (): void => {
  const pidFile = getPidFilePath();
  if (!fs.existsSync(pidFile)) {
    return;
  }
  try {
    const pid = parseInt(fs.readFileSync(pidFile, "utf-8").trim(), 10);
    if (!Number.isNaN(pid)) {
      // Check if process is still alive
      process.kill(pid, 0);
      // If we get here, process exists — kill it
      console.log(`Killing orphaned backend process (PID ${pid})`);
      process.kill(pid, "SIGTERM");
    }
  } catch {
    // Process doesn't exist or we can't kill it — either way, clean up
  }
  removePidFile();
};

export type BackendStartOptions = {
  host: string;
  port: number;
  mode?: string;
  device?: string;
  model?: string;
  onOutput?: (line: string) => void;
};

export type BackendProcess = {
  process: ReturnType<typeof spawn>;
  kill: () => void;
};

const buildPythonPath = (): string => {
  const paths = [
    path.join(SHARED_ROOT, "src"),
    path.join(BACKEND_ROOT, "src"),
  ];
  const existing = process.env.PYTHONPATH;
  if (existing) {
    paths.push(existing);
  }
  return paths.join(path.delimiter);
};

export const startBackend = (
  python: PythonInfo,
  options: BackendStartOptions,
): BackendProcess => {
  const env: Record<string, string> = {
    ...process.env,
    PYTHONPATH: buildPythonPath(),
    PARAKEY_HOST: options.host,
    PARAKEY_PORT: String(options.port),
    PYTHONUNBUFFERED: "1",
  };

  if (options.mode) {
    env.PARAKEY_MODE = options.mode;
  }
  if (options.device) {
    env.PARAKEY_DEVICE = options.device;
  }
  if (options.model) {
    env.PARAKEY_MODEL = options.model;
  }

  const cmd = ["-m", "parakey_backend.server"];
  const child = spawn(python.executable, cmd, {
    env,
    windowsHide: true,
  });

  const handleOutput = (data: Buffer) => {
    const text = data.toString();
    for (const line of text.split(/\r?\n/)) {
      if (!line.trim()) {
        continue;
      }
      options.onOutput?.(line.trim());
    }
  };

  child.stdout?.on("data", handleOutput);
  child.stderr?.on("data", handleOutput);

  // Track the PID so orphaned processes can be cleaned up on next launch
  if (child.pid != null) {
    writePidFile(child.pid);
  }
  child.on("exit", () => removePidFile());

  return {
    process: child,
    kill: () => {
      if (!child.killed) {
        child.kill();
      }
    },
  };
};

export const ensureBackendDeps = (python: PythonInfo): void => {
  if (!python.hasTorch || !python.hasNemo || !python.hasGrpc) {
    const missing = [
      !python.hasTorch && "torch",
      !python.hasNemo && "nemo",
      !python.hasGrpc && "grpc",
    ]
      .filter(Boolean)
      .join(", ");
    throw new BackendDepsError(
      `Python found but missing backend dependencies: ${missing}.`,
      python.executable,
    );
  }
};
