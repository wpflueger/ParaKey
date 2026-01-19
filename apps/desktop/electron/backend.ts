import { spawn } from "node:child_process";
import path from "node:path";
import { BackendDepsError } from "./python-finder";
import type { PythonInfo } from "./python-finder";
import { BACKEND_ROOT, SHARED_ROOT } from "./constants";

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
    KEYMUSE_HOST: options.host,
    KEYMUSE_PORT: String(options.port),
    PYTHONUNBUFFERED: "1",
  };

  if (options.mode) {
    env.KEYMUSE_MODE = options.mode;
  }
  if (options.device) {
    env.KEYMUSE_DEVICE = options.device;
  }
  if (options.model) {
    env.KEYMUSE_MODEL = options.model;
  }

  const cmd = ["-m", "keymuse_backend.server"];
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
