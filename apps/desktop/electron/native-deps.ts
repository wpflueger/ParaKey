import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { APP_ROOT } from "./constants";

export type NativeDepsResult = {
  ok: boolean;
  attemptedRebuild: boolean;
};

const resolveRebuildBinary = (): string | null => {
  try {
    const require = createRequire(__filename);
    return require.resolve("electron-rebuild/lib/cli.js");
  } catch {
    return null;
  }
};

const tryImportNaudiodon = async (): Promise<boolean> => {
  try {
    await import("naudiodon");
    return true;
  } catch {
    return false;
  }
};

export const ensureNativeAudioDeps = async (
  onLog?: (line: string) => void,
): Promise<NativeDepsResult> => {
  if (await tryImportNaudiodon()) {
    return { ok: true, attemptedRebuild: false };
  }

  onLog?.("Audio dependency missing. Attempting to rebuild naudiodon...");

  const rebuildPath = resolveRebuildBinary();
  if (!rebuildPath) {
    onLog?.("electron-rebuild not found. Run bun run rebuild:native manually.");
    return { ok: false, attemptedRebuild: false };
  }

  return new Promise((resolve) => {
    const child = spawn(process.execPath, [rebuildPath, "-f", "-w", "naudiodon"], {
      cwd: APP_ROOT,
      env: process.env,
      windowsHide: true,
    });

    child.stdout?.on("data", (data: Buffer) => {
      onLog?.(data.toString().trim());
    });
    child.stderr?.on("data", (data: Buffer) => {
      onLog?.(data.toString().trim());
    });

    child.on("exit", async (code) => {
      if (code === 0 && (await tryImportNaudiodon())) {
        onLog?.("naudiodon rebuild complete.");
        resolve({ ok: true, attemptedRebuild: true });
        return;
      }
      onLog?.("naudiodon rebuild failed. Try setting PYTHON to Python 3.11 or installing setuptools, then run bun run rebuild:native.");
      resolve({ ok: false, attemptedRebuild: true });
    });
  });
};
