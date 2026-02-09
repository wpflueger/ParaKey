// @vitest-environment node
import { describe, expect, it, vi } from "vitest";
import { EventEmitter } from "node:events";

const pidFiles: Record<string, string> = {};

vi.mock("electron", () => ({
  app: {
    getPath: () => "/tmp/test-backend",
    isPackaged: false,
  },
}));

vi.mock("node:fs", async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>;
  return {
    ...actual,
    default: {
      ...(actual.default as Record<string, unknown>),
      writeFileSync: (path: string, content: string) => { pidFiles[path] = content; },
      unlinkSync: (path: string) => { delete pidFiles[path]; },
      existsSync: (path: string) => path in pidFiles,
      readFileSync: (path: string) => pidFiles[path] ?? "",
      mkdirSync: () => undefined,
    },
  };
});

vi.mock("node:child_process", () => {
  return {
    spawn: vi.fn(() => {
      const emitter = new EventEmitter() as EventEmitter & {
        stdout?: EventEmitter;
        stderr?: EventEmitter;
        killed?: boolean;
        kill: () => void;
        pid?: number;
      };
      emitter.stdout = new EventEmitter();
      emitter.stderr = new EventEmitter();
      emitter.killed = false;
      emitter.kill = () => {
        emitter.killed = true;
      };
      emitter.pid = 12345;
      return emitter;
    }),
  };
});

import { cleanupOrphanedBackend, startBackend } from "./backend";
import { spawn } from "node:child_process";

const pythonInfo = {
  executable: "C:/Python311/python.exe",
  version: "3.11",
  hasTorch: true,
  hasNemo: true,
  hasGrpc: true,
  hasCuda: false,
};

describe("startBackend", () => {
  it("spawns backend and streams output", () => {
    const lines: string[] = [];
    const backend = startBackend(pythonInfo, {
      host: "127.0.0.1",
      port: 50051,
      onOutput: (line) => lines.push(line),
    });

    expect(spawn).toHaveBeenCalledWith(
      pythonInfo.executable,
      ["-m", "parakey_backend.server"],
      expect.objectContaining({
        env: expect.objectContaining({
          PARAKEY_HOST: "127.0.0.1",
          PARAKEY_PORT: "50051",
          PYTHONUNBUFFERED: "1",
        }),
      }),
    );

    backend.process.stdout?.emit("data", Buffer.from("ready\n"));
    backend.process.stderr?.emit("data", Buffer.from("warn\n"));

    expect(lines).toEqual(["ready", "warn"]);
  });

  it("writes PID file on start", () => {
    startBackend(pythonInfo, { host: "127.0.0.1", port: 50051 });

    expect(pidFiles["/tmp/test-backend/backend.pid"]).toBe("12345");
  });

  it("removes PID file on process exit", () => {
    const backend = startBackend(pythonInfo, { host: "127.0.0.1", port: 50051 });

    expect(pidFiles["/tmp/test-backend/backend.pid"]).toBe("12345");

    backend.process.emit("exit", 0);

    expect(pidFiles["/tmp/test-backend/backend.pid"]).toBeUndefined();
  });
});

describe("cleanupOrphanedBackend", () => {
  it("does nothing when no PID file exists", () => {
    // Ensure no PID file
    delete pidFiles["/tmp/test-backend/backend.pid"];

    // Should not throw
    cleanupOrphanedBackend();
  });

  it("removes stale PID file for dead process", () => {
    pidFiles["/tmp/test-backend/backend.pid"] = "99999";

    // process.kill(pid, 0) will throw for non-existent process
    // cleanupOrphanedBackend catches it and removes the file
    cleanupOrphanedBackend();

    expect(pidFiles["/tmp/test-backend/backend.pid"]).toBeUndefined();
  });
});
