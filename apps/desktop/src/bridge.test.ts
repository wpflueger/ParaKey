import { describe, expect, it } from "vitest";
import { getBridge } from "./bridge";

describe("getBridge", () => {
  it("returns a fallback bridge when preload is missing", async () => {
    const bridge = getBridge();
    expect(typeof bridge.onBackendLog).toBe("function");
    await expect(bridge.getSettings()).resolves.toBeDefined();
    await expect(bridge.requestHistory()).resolves.toEqual([]);
  });
});
