// @vitest-environment node
import { describe, expect, it, vi, beforeEach } from "vitest";
import { EventEmitter } from "node:events";

// Mock naudiodon before import
const mockInput = new EventEmitter() as EventEmitter & {
  start: ReturnType<typeof vi.fn>;
  quit: ReturnType<typeof vi.fn>;
};
mockInput.start = vi.fn();
mockInput.quit = vi.fn();

vi.mock("naudiodon", () => ({
  AudioIO: vi.fn(() => mockInput),
  SampleFormat16Bit: 8,
}));

import { createAudioStream } from "./audio";
import type { AudioFrame } from "./grpc-client";

const DEFAULT_OPTIONS = {
  sampleRateHz: 16000,
  channels: 1,
  frameMs: 20,
};

// At 16kHz mono 16-bit, 20ms = 320 samples * 2 bytes = 640 bytes per frame
const FRAME_BYTES = 640;

describe("audio buffer handling", () => {
  beforeEach(() => {
    mockInput.removeAllListeners();
    mockInput.start.mockClear();
    mockInput.quit.mockClear();
  });

  it("emits complete frames from exact-size chunks", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    // Emit exactly one frame worth of data
    mockInput.emit("data", Buffer.alloc(FRAME_BYTES, 0xaa));

    expect(frames).toHaveLength(1);
    expect(frames[0].audio.length).toBe(FRAME_BYTES);
    expect(frames[0].sample_rate_hz).toBe(16000);
    expect(frames[0].end_of_stream).toBe(false);
  });

  it("buffers partial chunks until a full frame is available", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    // Send half a frame
    mockInput.emit("data", Buffer.alloc(FRAME_BYTES / 2));
    expect(frames).toHaveLength(0);

    // Send other half — should now produce a full frame
    mockInput.emit("data", Buffer.alloc(FRAME_BYTES / 2));
    expect(frames).toHaveLength(1);
  });

  it("handles chunks larger than one frame", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    // Send 2.5 frames worth of data
    mockInput.emit("data", Buffer.alloc(FRAME_BYTES * 2 + FRAME_BYTES / 2));
    expect(frames).toHaveLength(2);

    // Send remaining half — should complete the third frame
    mockInput.emit("data", Buffer.alloc(FRAME_BYTES / 2));
    expect(frames).toHaveLength(3);
  });

  it("assigns sequential sequence numbers", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    mockInput.emit("data", Buffer.alloc(FRAME_BYTES * 3));

    expect(frames[0].sequence).toBe(BigInt(0));
    expect(frames[1].sequence).toBe(BigInt(1));
    expect(frames[2].sequence).toBe(BigInt(2));
  });

  it("flushes remainder with silence padding on stop", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    // Send partial data
    mockInput.emit("data", Buffer.alloc(100, 0xff));
    expect(frames).toHaveLength(0);

    controller.stop();

    // Should have flushed the remainder as a padded frame
    expect(frames).toHaveLength(1);
    expect(frames[0].audio.length).toBe(FRAME_BYTES);
    // First 100 bytes should be 0xff, rest should be 0x00 (silence)
    expect(frames[0].audio[0]).toBe(0xff);
    expect(frames[0].audio[99]).toBe(0xff);
    expect(frames[0].audio[100]).toBe(0x00);
    expect(mockInput.quit).toHaveBeenCalled();
  });

  it("does not flush when remainder is empty", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    // Send exact frame — no remainder
    mockInput.emit("data", Buffer.alloc(FRAME_BYTES));
    expect(frames).toHaveLength(1);

    controller.stop();

    // No additional flush frame
    expect(frames).toHaveLength(1);
  });

  it("handles many small chunks efficiently", async () => {
    const controller = await createAudioStream(DEFAULT_OPTIONS);
    const frames: AudioFrame[] = [];
    controller.onFrame((f) => frames.push(f));

    // Send 64 chunks of 10 bytes each = 640 bytes = 1 frame
    for (let i = 0; i < 64; i++) {
      mockInput.emit("data", Buffer.alloc(10));
    }

    expect(frames).toHaveLength(1);
  });
});
