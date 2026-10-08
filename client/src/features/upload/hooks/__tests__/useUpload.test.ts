import { describe, expect, it } from "vitest";
import { useUpload } from "../useUpload";

describe("useUpload hook logic", () => {
  it("exports useUpload function", () => {
    expect(typeof useUpload).toBe("function");
  });
});
