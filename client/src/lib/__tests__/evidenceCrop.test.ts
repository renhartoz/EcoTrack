import { describe, expect, it } from "vitest";
import { calculateEvidenceCrop } from "../evidenceCrop";

describe("evidenceCrop calculation", () => {
  it("calculates correct crop styles for valid range with 1% padding", () => {
    const crop = calculateEvidenceCrop(0.3, 0.4);
    expect(crop.isValid).toBe(true);
    expect(crop.startY).toBeCloseTo(0.29, 4);
    expect(crop.endY).toBeCloseTo(0.41, 4);
    expect(crop.backgroundSize).toContain("100%");
    expect(crop.backgroundPosition).toContain("center");
  });

  it("clamps padding at edges", () => {
    const cropTop = calculateEvidenceCrop(0.005, 0.1);
    expect(cropTop.isValid).toBe(true);
    expect(cropTop.startY).toBe(0);
    expect(cropTop.endY).toBeCloseTo(0.11, 4);

    const cropBottom = calculateEvidenceCrop(0.9, 0.998);
    expect(cropBottom.isValid).toBe(true);
    expect(cropBottom.startY).toBeCloseTo(0.89, 4);
    expect(cropBottom.endY).toBe(1);
  });

  it("returns invalid for null, undefined, or NaN", () => {
    expect(calculateEvidenceCrop(null, 0.5).isValid).toBe(false);
    expect(calculateEvidenceCrop(0.2, null).isValid).toBe(false);
    expect(calculateEvidenceCrop(undefined, undefined).isValid).toBe(false);
    expect(calculateEvidenceCrop(NaN, 0.5).isValid).toBe(false);
  });

  it("returns invalid when yMin is greater than or equal to yMax", () => {
    expect(calculateEvidenceCrop(0.5, 0.5).isValid).toBe(false);
    expect(calculateEvidenceCrop(0.6, 0.4).isValid).toBe(false);
  });

  it("returns invalid when coordinates are out of [0, 1] range", () => {
    expect(calculateEvidenceCrop(-0.1, 0.5).isValid).toBe(false);
    expect(calculateEvidenceCrop(0.2, 1.2).isValid).toBe(false);
  });
});
