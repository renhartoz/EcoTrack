import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RowCard } from "../components/RowCard";
import { UI_STRINGS } from "@/lib/strings.id";
import type { ExtractedRow } from "@/types/uploads";

function createMockRow(overrides: Partial<ExtractedRow> = {}): ExtractedRow {
  return {
    id: 101,
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

describe("RowCard component", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    container.remove();
  });

  it("disables confirm button when row has hard flags", async () => {
    const row = createMockRow({
      flags: [{ code: "NASABAH_UNKNOWN", severity: "hard" }],
    });
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <RowCard
          row={row}
          uploadId={1}
          sourceType="image"
          nasabahList={[]}
          wasteTypes={[]}
          onConfirm={vi.fn()}
          onReject={vi.fn()}
          onUpdate={vi.fn()}
          onCreateNasabah={vi.fn()}
        />,
      );
    });

    const buttons = Array.from(container.querySelectorAll("button"));
    const confirmButton = buttons.find((btn) =>
      btn.textContent?.includes(UI_STRINGS.confirmRowButton),
    );

    expect(confirmButton).toBeDefined();
    expect(confirmButton?.hasAttribute("disabled")).toBe(true);

    await act(async () => {
      root.unmount();
    });
  });

  it("enables confirm button when row has only soft flags", async () => {
    const row = createMockRow({
      flags: [{ code: "AMBIGUOUS_TYPE", severity: "soft" }],
    });
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <RowCard
          row={row}
          uploadId={1}
          sourceType="image"
          nasabahList={[]}
          wasteTypes={[]}
          onConfirm={vi.fn()}
          onReject={vi.fn()}
          onUpdate={vi.fn()}
          onCreateNasabah={vi.fn()}
        />,
      );
    });

    const buttons = Array.from(container.querySelectorAll("button"));
    const confirmButton = buttons.find((btn) =>
      btn.textContent?.includes(UI_STRINGS.confirmRowButton),
    );

    expect(confirmButton).toBeDefined();
    expect(confirmButton?.hasAttribute("disabled")).toBe(false);

    await act(async () => {
      root.unmount();
    });
  });

  it("calls onConfirm when confirm button is clicked", async () => {
    const row = createMockRow({ flags: [] });
    const handleConfirm = vi.fn().mockResolvedValue(undefined);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <RowCard
          row={row}
          uploadId={1}
          sourceType="image"
          nasabahList={[]}
          wasteTypes={[]}
          onConfirm={handleConfirm}
          onReject={vi.fn()}
          onUpdate={vi.fn()}
          onCreateNasabah={vi.fn()}
        />,
      );
    });

    const buttons = Array.from(container.querySelectorAll("button"));
    const confirmButton = buttons.find((btn) =>
      btn.textContent?.includes(UI_STRINGS.confirmRowButton),
    );

    await act(async () => {
      confirmButton?.dispatchEvent(
        new MouseEvent("click", { bubbles: true, cancelable: true }),
      );
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(handleConfirm).toHaveBeenCalledWith(row.id);

    await act(async () => {
      root.unmount();
    });
  });

  it("calls onReject when reject button is clicked", async () => {
    const row = createMockRow();
    const handleReject = vi.fn().mockResolvedValue(undefined);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <RowCard
          row={row}
          uploadId={1}
          sourceType="image"
          nasabahList={[]}
          wasteTypes={[]}
          onConfirm={vi.fn()}
          onReject={handleReject}
          onUpdate={vi.fn()}
          onCreateNasabah={vi.fn()}
        />,
      );
    });

    const buttons = Array.from(container.querySelectorAll("button"));
    const rejectButton = buttons.find((btn) =>
      btn.textContent?.includes(UI_STRINGS.rejectRowButton),
    );

    await act(async () => {
      rejectButton?.dispatchEvent(
        new MouseEvent("click", { bubbles: true, cancelable: true }),
      );
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(handleReject).toHaveBeenCalledWith(row.id);

    await act(async () => {
      root.unmount();
    });
  });
});
