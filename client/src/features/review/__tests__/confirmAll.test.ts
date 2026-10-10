import { describe, expect, it } from "vitest";
import {
  filterEligibleForConfirmAll,
  isRowEligibleForConfirmAll,
} from "../lib/confirmAll";
import type { ExtractedRow } from "@/types/uploads";

function createMockRow(overrides: Partial<ExtractedRow> = {}): ExtractedRow {
  return {
    id: 1,
    row_index: 0,
    status: "pending",
    route: "confirm",
    score: 0.85,
    flags: [],
    raw: {
      tanggal: "12/9",
      nama: "Bu Siti",
      jenis: "botol",
      berat: "2.5",
      satuan: "kg",
      evidence_text: "12/9 Bu Siti botol 2.5 kg",
    },
    normalized: {
      tanggal: "2026-09-12",
      nasabah_id: 1,
      waste_type_id: 2,
      weight_kg: "2.500",
    },
    evidence: {
      y_min: 0.3,
      y_max: 0.4,
    },
    human_edited: false,
    deposit_id: null,
    ...overrides,
  };
}

describe("confirmAll eligibility", () => {
  it("marks pending confirm rows with no flags as eligible", () => {
    const row = createMockRow();
    expect(isRowEligibleForConfirmAll(row)).toBe(true);
  });

  it("marks rows with soft flags (non-duplicate) as eligible", () => {
    const row = createMockRow({
      flags: [
        { code: "AMBIGUOUS_TYPE", severity: "soft" },
        { code: "UNIT_ASSUMED_KG", severity: "soft" },
      ],
    });
    expect(isRowEligibleForConfirmAll(row)).toBe(true);
  });

  it("marks rows with hard flags as ineligible", () => {
    const row = createMockRow({
      flags: [{ code: "NASABAH_UNKNOWN", severity: "hard" }],
    });
    expect(isRowEligibleForConfirmAll(row)).toBe(false);
  });

  it("marks rows with DUPLICATE_IN_PAGE soft flag as ineligible", () => {
    const row = createMockRow({
      flags: [{ code: "DUPLICATE_IN_PAGE", severity: "soft" }],
    });
    expect(isRowEligibleForConfirmAll(row)).toBe(false);
  });

  it("marks rows with DUPLICATE_IN_DB soft flag as ineligible", () => {
    const row = createMockRow({
      flags: [{ code: "DUPLICATE_IN_DB", severity: "soft" }],
    });
    expect(isRowEligibleForConfirmAll(row)).toBe(false);
  });

  it("marks rows with non-pending status as ineligible", () => {
    expect(isRowEligibleForConfirmAll(createMockRow({ status: "saved" }))).toBe(
      false,
    );
    expect(
      isRowEligibleForConfirmAll(createMockRow({ status: "rejected" })),
    ).toBe(false);
    expect(
      isRowEligibleForConfirmAll(createMockRow({ status: "reverted" })),
    ).toBe(false);
  });

  it("marks rows with non-confirm route as ineligible", () => {
    expect(isRowEligibleForConfirmAll(createMockRow({ route: "manual" }))).toBe(
      false,
    );
    expect(isRowEligibleForConfirmAll(createMockRow({ route: "auto" }))).toBe(
      false,
    );
    expect(isRowEligibleForConfirmAll(createMockRow({ route: null }))).toBe(
      false,
    );
  });

  it("filters multiple rows and calculates correct eligible count", () => {
    const rows: ExtractedRow[] = [
      createMockRow({ id: 1 }),
      createMockRow({
        id: 2,
        flags: [{ code: "AMBIGUOUS_TYPE", severity: "soft" }],
      }),
      createMockRow({
        id: 3,
        flags: [{ code: "NASABAH_UNKNOWN", severity: "hard" }],
      }),
      createMockRow({
        id: 4,
        flags: [{ code: "DUPLICATE_IN_PAGE", severity: "soft" }],
      }),
      createMockRow({ id: 5, route: "manual" }),
      createMockRow({ id: 6, status: "saved" }),
    ];

    const eligible = filterEligibleForConfirmAll(rows);
    expect(eligible).toHaveLength(2);
    expect(eligible.map((r) => r.id)).toEqual([1, 2]);
  });
});
