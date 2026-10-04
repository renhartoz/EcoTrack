import { describe, expect, it } from "vitest";
import {
  ERROR_MESSAGES,
  FLAG_MESSAGES,
  ROUTE_LABELS,
  type ErrorCode,
  type FlagCode,
  type RouteType,
} from "../strings.id";

describe("strings.id mappings", () => {
  it("covers all required route labels", () => {
    const requiredRoutes: RouteType[] = ["auto", "confirm", "manual"];
    for (const route of requiredRoutes) {
      expect(ROUTE_LABELS[route]).toBeDefined();
      expect(ROUTE_LABELS[route].length).toBeGreaterThan(0);
    }
  });

  it("covers all 17 flag codes from spec Section 12.4", () => {
    const requiredFlags: FlagCode[] = [
      "WEIGHT_UNPARSEABLE",
      "WEIGHT_NONPOSITIVE",
      "WEIGHT_OUT_OF_RANGE",
      "TYPE_UNKNOWN",
      "AMBIGUOUS_TYPE",
      "NASABAH_UNKNOWN",
      "AMBIGUOUS_NASABAH",
      "DATE_UNPARSEABLE",
      "DATE_OUT_OF_RANGE",
      "DATE_INHERITED",
      "UNIT_ASSUMED_KG",
      "LOW_LLM_CONFIDENCE",
      "ILLEGIBLE_FIELD",
      "DUPLICATE_IN_PAGE",
      "DUPLICATE_IN_DB",
      "PAGE_TOTAL_MISMATCH",
      "WEIGHT_READER_MISMATCH",
    ];

    expect(requiredFlags).toHaveLength(17);
    for (const flag of requiredFlags) {
      expect(FLAG_MESSAGES[flag]).toBeDefined();
      expect(FLAG_MESSAGES[flag].length).toBeGreaterThan(0);
    }
  });

  it("covers all 15 error codes from spec Appendix B", () => {
    const requiredErrors: ErrorCode[] = [
      "UNAUTHENTICATED",
      "NOT_FOUND",
      "VALIDATION_ERROR",
      "INVALID_IMAGE",
      "FILE_TOO_LARGE",
      "THROTTLED",
      "ROW_NOT_PENDING",
      "ROW_HAS_HARD_FLAGS",
      "LLM_TIMEOUT",
      "LLM_API_ERROR",
      "LLM_SCHEMA_INVALID",
      "REPLAY_MISS",
      "LLM_RATE_LIMITED",
      "OCR_API_ERROR",
      "CSRF_FAILED",
    ];

    expect(requiredErrors).toHaveLength(15);
    for (const code of requiredErrors) {
      expect(ERROR_MESSAGES[code]).toBeDefined();
      expect(ERROR_MESSAGES[code].length).toBeGreaterThan(0);
    }
  });
});
