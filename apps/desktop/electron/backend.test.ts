// @vitest-environment node
import { describe, expect, it, vi } from "vitest";
import { EventEmitter } from "node:events";

import { startBackend } from "./backend";
import { spawn } from "node:child_process";

vi.mock("node:child_process", () => {
  return {
    spawn: vi.fn(() => {
      const emitter = new EventEmitter() as EventEmitter & {
        stdout?: EventEmitter;
        stderr?: EventEmitter;
        killed?: boolean;
        kill: () => void;
      };
      emitter.stdout = new EventEmitter();
      emitter.stderr = new EventEmitter();
      emitter.killed = false;
      emitter.kill = () => {
        emitter.killed = true;
      };
      return emitter;
    }),
  };
});

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
});
