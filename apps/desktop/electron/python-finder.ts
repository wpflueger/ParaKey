import path from "node:path";
import { execFileSync, spawn, spawnSync } from "node:child_process";
import fs from "node:fs";

export type PythonInfo = {
  executable: string;
  version: string;
  hasTorch: boolean;
  hasNemo: boolean;
  hasGrpc: boolean;
  hasCuda: boolean;
};

export class PythonNotFoundError extends Error {}

export class BackendDepsError extends Error {
  public readonly pythonPath: string;

  constructor(message: string, pythonPath: string) {
    super(message);
    this.pythonPath = pythonPath;
  }
}

const runPythonCheck = (pythonPath: string, code: string): string | null => {
  try {
    const result = spawnSync(pythonPath, ["-c", code], {
      encoding: "utf-8",
      timeout: 30000,
      windowsHide: true,
    });
    if (result.status === 0) {
      return result.stdout.trim();
    }
    return null;
  } catch {
    return null;
  }
};

type PythonCheckResult = {
  version: string;
  hasTorch: boolean;
  hasNemo: boolean;
  hasGrpc: boolean;
  hasCuda: boolean;
};

const getAllPythonInfo = (pythonPath: string): PythonCheckResult | null => {
  const script = [
    "import sys, json",
    "info = {'version': f'{sys.version_info.major}.{sys.version_info.minor}', 'hasTorch': False, 'hasNemo': False, 'hasGrpc': False, 'hasCuda': False}",
    "try:",
    "    import torch",
    "    info['hasTorch'] = True",
    "    try:",
    "        info['hasCuda'] = torch.cuda.is_available()",
    "    except Exception:",
    "        pass",
    "except Exception:",
    "    pass",
    "try:",
    "    import nemo; info['hasNemo'] = True",
    "except Exception: pass",
    "try:",
    "    import grpc; info['hasGrpc'] = True",
    "except Exception: pass",
    "print(json.dumps(info))",
  ].join("\n");

  const output = runPythonCheck(pythonPath, script);
  if (!output) {
    return null;
  }
  try {
    return JSON.parse(output) as PythonCheckResult;
  } catch {
    return null;
  }
};

const isValidPython = (version: string | null): boolean => {
  if (!version) {
    return false;
  }
  const [major, minor] = version.split(".").map((part) => Number(part));
  if (!Number.isFinite(major) || !Number.isFinite(minor)) {
    return false;
  }
  return major === 3 && (minor === 11 || minor === 12);
};

const getPythonInfo = (pythonPath: string, checkDeps: boolean): PythonInfo | null => {
  if (!fs.existsSync(pythonPath)) {
    return null;
  }

  if (!checkDeps) {
    // Quick check: just version
    const version = runPythonCheck(pythonPath, "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')");
    if (!isValidPython(version)) {
      return null;
    }
    return {
      executable: pythonPath,
      version: version ?? "",
      hasTorch: false,
      hasNemo: false,
      hasGrpc: false,
      hasCuda: false,
    };
  }

  // Full check: version + all deps in one call
  const result = getAllPythonInfo(pythonPath);
  if (!result || !isValidPython(result.version)) {
    return null;
  }
  return {
    executable: pythonPath,
    version: result.version,
    hasTorch: result.hasTorch,
    hasNemo: result.hasNemo,
    hasGrpc: result.hasGrpc,
    hasCuda: result.hasCuda,
  };
};

export const getPythonInfoForExecutable = (
  pythonPath: string,
  checkDeps: boolean,
): PythonInfo | null => getPythonInfo(pythonPath, checkDeps);

export const resolveVenvPython = (venvRoot: string): string => {
  return process.platform === "win32"
    ? path.join(venvRoot, "Scripts", "python.exe")
    : path.join(venvRoot, "bin", "python");
};

export const ensureVenv = (pythonPath: string, venvRoot: string): string => {
  const venvPython = resolveVenvPython(venvRoot);
  if (!fs.existsSync(venvPython)) {
    execFileSync(pythonPath, ["-m", "venv", venvRoot], { stdio: "inherit" });
  }
  return venvPython;
};

const findEnvPython = (): string | null => {
  const envPython = process.env.PARAKEY_PYTHON;
  if (envPython && fs.existsSync(envPython)) {
    return envPython;
  }
  return null;
};

const findVenvPython = (appRoot: string): string | null => {
  const searchPaths = [
    path.join(appRoot, ".venv", "Scripts", "python.exe"),
    path.join(appRoot, "..", ".venv", "Scripts", "python.exe"),
    path.join(appRoot, "..", "..", ".venv", "Scripts", "python.exe"),
  ];
  for (const candidate of searchPaths) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
};

const findPathPython = (): string | null => {
  const command = process.platform === "win32" ? "where" : "which";
  try {
    const output = execFileSync(command, ["python"], { encoding: "utf-8" }).trim();
    const first = output.split(/\r?\n/)[0];
    if (first && fs.existsSync(first)) {
      return first;
    }
  } catch {
    return null;
  }
  return null;
};

const findPyLauncher = (): string | null => {
  if (process.platform !== "win32") {
    return null;
  }
  for (const version of ["3.12", "3.11"]) {
    try {
      const output = execFileSync("py", [`-${version}`, "-c", "import sys; print(sys.executable)"] , {
        encoding: "utf-8",
        windowsHide: true,
      }).trim();
      if (output && fs.existsSync(output)) {
        return output;
      }
    } catch {
      continue;
    }
  }
  return null;
};

const findCommonInstall = (): string | null => {
  if (process.platform !== "win32") {
    return null;
  }
  const localAppData = process.env.LOCALAPPDATA ?? "";
  const candidates = [
    localAppData && path.join(localAppData, "Programs", "Python"),
    "C:/Python312",
    "C:/Python311",
    "C:/Program Files/Python312",
    "C:/Program Files/Python311",
  ].filter(Boolean) as string[];

  for (const base of candidates) {
    if (!fs.existsSync(base)) {
      continue;
    }
    const direct = path.join(base, "python.exe");
    if (fs.existsSync(direct)) {
      return direct;
    }
    try {
      const subdirs = fs.readdirSync(base, { withFileTypes: true });
      for (const sub of subdirs) {
        if (sub.isDirectory() && sub.name.startsWith("Python")) {
          const candidate = path.join(base, sub.name, "python.exe");
          if (fs.existsSync(candidate)) {
            return candidate;
          }
        }
      }
    } catch {
      continue;
    }
  }
  return null;
};

export const findPython = (appRoot: string, checkDeps = true): PythonInfo => {
  const finders = [
    findEnvPython,
    () => findVenvPython(appRoot),
    findPathPython,
    findPyLauncher,
    findCommonInstall,
  ];

  let found: PythonInfo | null = null;

  for (const finder of finders) {
    const candidate = finder();
    if (!candidate) {
      continue;
    }
    const info = getPythonInfo(candidate, checkDeps);
    if (!info) {
      continue;
    }
    if (!checkDeps || (info.hasTorch && info.hasNemo && info.hasGrpc)) {
      return info;
    }
    if (!found) {
      found = info;
    }
  }

  if (found) {
    const missing = [
      !found.hasTorch && "torch",
      !found.hasNemo && "nemo",
      !found.hasGrpc && "grpc",
    ]
      .filter(Boolean)
      .join(", ");
    throw new BackendDepsError(
      `Python found but missing backend dependencies: ${missing}.`,
      found.executable,
    );
  }

  throw new PythonNotFoundError(
    "Python 3.11+ not found. Install Python or set PARAKEY_PYTHON to your Python executable.",
  );
};

export const installBackendDeps = (
  pythonPath: string,
  backendRoot: string,
  tempDir?: string,
): void => {
  const requirements = path.join(backendRoot, "requirements.txt");
  if (tempDir) {
    fs.mkdirSync(tempDir, { recursive: true });
  }
  execFileSync(pythonPath, ["-m", "pip", "install", "-r", requirements], {
    stdio: "inherit",
    env: {
      ...process.env,
      ...(tempDir ? { TEMP: tempDir, TMP: tempDir } : {}),
      PIP_DISABLE_PIP_VERSION_CHECK: "1",
    },
  });
};

const runPipInstall = (
  pythonPath: string,
  args: string[],
  tempDir?: string,
  onOutput?: (line: string) => void,
): Promise<void> => {
  return new Promise((resolve, reject) => {
    const child = spawn(pythonPath, ["-m", "pip", "install", ...args], {
      windowsHide: true,
      env: {
        ...process.env,
        ...(tempDir ? { TEMP: tempDir, TMP: tempDir } : {}),
        PIP_DISABLE_PIP_VERSION_CHECK: "1",
      },
    });

    const handleOutput = (data: Buffer) => {
      const text = data.toString();
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) {
          continue;
        }
        onOutput?.(line.trim());
      }
    };

    child.stdout?.on("data", handleOutput);
    child.stderr?.on("data", handleOutput);

    child.on("error", (error) => reject(error));
    child.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`pip install exited with code ${code}`));
      }
    });
  });
};

export const installBackendDepsAsync = async (
  pythonPath: string,
  backendRoot: string,
  tempDir?: string,
  onOutput?: (line: string) => void,
): Promise<void> => {
  const requirements = path.join(backendRoot, "requirements.txt");
  if (tempDir) {
    fs.mkdirSync(tempDir, { recursive: true });
  }

  // Install main requirements
  await runPipInstall(pythonPath, ["-r", requirements], tempDir, onOutput);

  // Force numpy <2 to fix compatibility with torch/nemo compiled against numpy 1.x
  onOutput?.("Ensuring numpy compatibility...");
  await runPipInstall(pythonPath, ["numpy>=1.26.0,<2", "--force-reinstall"], tempDir, onOutput);
};
