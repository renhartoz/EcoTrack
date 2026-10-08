import { describe, expect, it } from "vitest";
import { calculateResizeDimensions, computeSha256Hex } from "../image";

describe("image resize and hash utilities", () => {
  it("calculates correct resize dimensions without upscaling", () => {
    expect(calculateResizeDimensions(1600, 1200)).toEqual({
      width: 1600,
      height: 1200,
    });
    expect(calculateResizeDimensions(800, 600)).toEqual({
      width: 800,
      height: 600,
    });
    expect(calculateResizeDimensions(2000, 1500)).toEqual({
      width: 2000,
      height: 1500,
    });
  });

  it("scales down landscape images so long edge is at most 2000px", () => {
    expect(calculateResizeDimensions(4000, 2000)).toEqual({
      width: 2000,
      height: 1000,
    });
    expect(calculateResizeDimensions(3000, 1500)).toEqual({
      width: 2000,
      height: 1000,
    });
  });

  it("scales down portrait images so long edge is at most 2000px", () => {
    expect(calculateResizeDimensions(2000, 4000)).toEqual({
      width: 1000,
      height: 2000,
    });
    expect(calculateResizeDimensions(1500, 3000)).toEqual({
      width: 1000,
      height: 2000,
    });
  });

  it("scales down square images to 2000x2000", () => {
    expect(calculateResizeDimensions(3000, 3000)).toEqual({
      width: 2000,
      height: 2000,
    });
  });

  it("handles non-positive dimensions gracefully", () => {
    expect(calculateResizeDimensions(0, 1000)).toEqual({
      width: 0,
      height: 0,
    });
    expect(calculateResizeDimensions(-100, -200)).toEqual({
      width: 0,
      height: 0,
    });
  });

  it("computes correct SHA-256 hex digest for empty input known vector", async () => {
    const empty = new Uint8Array(0);
    const hash = await computeSha256Hex(empty);
    expect(hash).toBe(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    );
  });

  it("computes correct SHA-256 hex digest for 'hello' string known vector", async () => {
    const encoder = new TextEncoder();
    const data = encoder.encode("hello");
    const hash = await computeSha256Hex(data);
    expect(hash).toBe(
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    );
  });

  it("computes correct SHA-256 hex digest for Blob input", async () => {
    const blob = new Blob(["hello"], { type: "text/plain" });
    const hash = await computeSha256Hex(blob);
    expect(hash).toBe(
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    );
  });
});
