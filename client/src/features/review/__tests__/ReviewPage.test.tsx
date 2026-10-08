import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewPage } from "../pages/ReviewPage";
import * as uploadsService from "@/services/uploads";
import type { UploadDetail } from "@/types/uploads";

describe("ReviewPage", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders raw fields in rows table when upload is ready", async () => {
    const mockDetail: UploadDetail = {
      id: 41,
      source_type: "image",
      status: "ready",
      source_sha256: null,
      created_at: "2026-10-06T15:30:00Z",
      processing_started_at: "2026-10-06T15:30:00Z",
      error_code: null,
      error_message: null,
      page: null,
      counts: { auto: 0, confirm: 0, manual: 0, saved: 0, pending: 1 },
      rows: [
        {
          id: 301,
          row_index: 0,
          status: "pending",
          route: null,
          score: null,
          flags: [],
          raw: {
            tanggal: "12/9",
            nama: "Bu Siti",
            jenis: "botol",
            berat: "2,5",
            satuan: "kg",
            evidence_text: "12/9 Bu Siti botol 2,5 kg",
          },
          normalized: {
            tanggal: null,
            nasabah_id: null,
            waste_type_id: null,
            weight_kg: null,
          },
          evidence: { y_min: 0.31, y_max: 0.36 },
          human_edited: false,
          deposit_id: null,
        },
      ],
    };

    vi.spyOn(uploadsService, "getUploadDetail").mockResolvedValue(mockDetail);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/uploads/41"]}>
            <Routes>
              <Route path="/uploads/:id" element={<ReviewPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.textContent).toContain("12/9");
    expect(container.textContent).toContain("Bu Siti");
    expect(container.textContent).toContain("botol");
    expect(container.textContent).toContain("2,5");
    expect(container.textContent).toContain("kg");
    expect(container.textContent).toContain("12/9 Bu Siti botol 2,5 kg");
  });

  it("renders failed state with error message and retry button", async () => {
    const mockFailedDetail: UploadDetail = {
      id: 42,
      source_type: "image",
      status: "failed",
      source_sha256: null,
      created_at: "2026-10-06T15:35:00Z",
      processing_started_at: "2026-10-06T15:35:00Z",
      error_code: "LLM_RATE_LIMITED",
      error_message: "Rate limit hit",
      page: null,
      counts: { auto: 0, confirm: 0, manual: 0, saved: 0, pending: 0 },
      rows: [],
    };

    vi.spyOn(uploadsService, "getUploadDetail").mockResolvedValue(
      mockFailedDetail,
    );
    const retrySpy = vi.spyOn(uploadsService, "retryUpload").mockResolvedValue({
      ...mockFailedDetail,
      status: "ready",
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/uploads/42"]}>
            <Routes>
              <Route path="/uploads/:id" element={<ReviewPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.textContent).toContain(
      "Layanan sedang sibuk. Coba lagi dalam 1 menit.",
    );

    const retryButton = container.querySelector("button");
    expect(retryButton).not.toBeNull();
    expect(retryButton?.textContent).toContain("Coba lagi");

    await act(async () => {
      retryButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(retrySpy).toHaveBeenCalledWith("42");
  });
});
