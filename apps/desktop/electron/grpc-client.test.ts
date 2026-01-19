// @vitest-environment node
import { describe, expect, it, vi } from "vitest";
import { makeGenericClientConstructor } from "@grpc/grpc-js";

const handlers: Record<string, (payload: unknown) => void> = {};

vi.mock("@grpc/grpc-js", () => ({
  makeGenericClientConstructor: vi.fn(),
  credentials: {
    createInsecure: vi.fn(() => ({})),
  },
}));

import { createDictationClient, streamAudio } from "./grpc-client";

const buildFakeClient = () => {
  const stream = {
    on: (event: string, handler: (payload: unknown) => void) => {
      handlers[event] = handler;
      return stream;
    },
    emit: (event: string, payload: unknown) => {
      handlers[event]?.(payload);
    },
  };

  return class FakeService {
    GetHealth(_payload: Record<string, never>, cb: (error: Error | null, response: unknown) => void) {
      cb(null, { ready: true, detail: "ok", mode: "mock" });
    }

    StreamAudio() {
      return stream;
    }
  };
};
describe("grpc client", () => {
  it("wraps GetHealth into a promise", async () => {
    (vi.mocked(makeGenericClientConstructor) as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(
      () => buildFakeClient(),
    );

    const client = createDictationClient("127.0.0.1", 50051);
    const health = await client.GetHealth({});

    expect(health.ready).toBe(true);
    expect(health.detail).toBe("ok");
  });

  it("streams events from gRPC", () => {
    (vi.mocked(makeGenericClientConstructor) as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(
      () => buildFakeClient(),
    );

    const client = createDictationClient("127.0.0.1", 50051);
    const received: string[] = [];

    const stream = streamAudio(
      client,
      (event) => {
        if (event.final?.text) {
          received.push(event.final.text);
        }
      },
      () => undefined,
    );

    (stream as { emit?: (event: string, payload: unknown) => void }).emit?.(
      "data",
      { final: { text: "hello", from_cache: false } },
    );

    expect(received).toEqual(["hello"]);
  });
});
