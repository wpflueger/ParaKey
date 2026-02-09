// @vitest-environment node
import { describe, expect, it, vi, beforeEach } from "vitest";

let clipboardContent = "";

const { mockKeyTap } = vi.hoisted(() => ({
  mockKeyTap: vi.fn(),
}));

vi.mock("electron", () => ({
  clipboard: {
    readText: () => clipboardContent,
    writeText: (text: string) => { clipboardContent = text; },
    clear: () => { clipboardContent = ""; },
  },
}));

vi.mock("uiohook-napi", () => ({
  UiohookKey: { V: 0x56, Ctrl: 0xa2 },
  uIOhook: { keyTap: mockKeyTap },
}));

import { sanitizeText, setClipboardText, sendPaste } from "./clipboard";

describe("sanitizeText", () => {
  it("strips control characters", () => {
    expect(sanitizeText("hello\x00world")).toBe("helloworld ");
  });

  it("strips bidirectional characters", () => {
    expect(sanitizeText("hello\u200Eworld")).toBe("helloworld ");
  });

  it("normalizes line endings to CRLF", () => {
    expect(sanitizeText("a\nb")).toBe("a\r\nb ");
  });

  it("adds trailing space", () => {
    expect(sanitizeText("hello")).toBe("hello ");
  });
});

describe("sendPaste", () => {
  beforeEach(() => {
    clipboardContent = "";
    mockKeyTap.mockClear();
    vi.useFakeTimers();
  });

  it("accepts custom timing options", async () => {
    setClipboardText("test");

    const promise = sendPaste({ focusDelayMs: 10, restoreDelayMs: 20 });

    // Advance past focus delay
    await vi.advanceTimersByTimeAsync(10);
    expect(mockKeyTap).toHaveBeenCalledTimes(1);

    // Advance past restore delay
    await vi.advanceTimersByTimeAsync(20);
    await promise;
  });

  it("uses default timing when no options provided", async () => {
    setClipboardText("test");

    const promise = sendPaste();

    // Default focus delay is 50ms
    await vi.advanceTimersByTimeAsync(50);
    expect(mockKeyTap).toHaveBeenCalledTimes(1);

    // Default restore delay is 100ms
    await vi.advanceTimersByTimeAsync(100);
    await promise;
  });

  it("restores previous clipboard content", async () => {
    clipboardContent = "previous";
    setClipboardText("dictation");

    const promise = sendPaste({ focusDelayMs: 1, restoreDelayMs: 1 });
    await vi.advanceTimersByTimeAsync(1);
    await vi.advanceTimersByTimeAsync(1);
    await promise;

    expect(clipboardContent).toBe("previous");
  });

  it("clears clipboard when no previous content", async () => {
    clipboardContent = "";
    setClipboardText("dictation");

    const promise = sendPaste({ focusDelayMs: 1, restoreDelayMs: 1 });
    await vi.advanceTimersByTimeAsync(1);
    await vi.advanceTimersByTimeAsync(1);
    await promise;

    expect(clipboardContent).toBe("");
  });
});
