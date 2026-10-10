import { describe, expect, it } from "vitest";
import { formatDate, formatWeight } from "../format";

describe("format helpers", () => {
  it("formats weight with 3 decimal digits and kg unit", () => {
    expect(formatWeight("2.500")).toBe("2,500 kg");
    expect(formatWeight(2.5)).toBe("2,500 kg");
    expect(formatWeight("1234.500")).toBe("1.234,500 kg");
    expect(formatWeight("2.500", false)).toBe("2,500");
  });

  it("returns dash for empty, null, or invalid weights", () => {
    expect(formatWeight(null)).toBe("-");
    expect(formatWeight(undefined)).toBe("-");
    expect(formatWeight("")).toBe("-");
    expect(formatWeight("invalid")).toBe("-");
  });

  it("formats valid ISO date into Indonesian locale", () => {
    const formatted = formatDate("2026-09-12");
    expect(formatted).toContain("2026");
    expect(formatted).toContain("12");
  });

  it("handles empty or invalid dates gracefully", () => {
    expect(formatDate(null)).toBe("-");
    expect(formatDate(undefined)).toBe("-");
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });
});
