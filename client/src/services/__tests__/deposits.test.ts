import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createDeposit,
  deleteDeposit,
  exportDepositsCsv,
  getDeposits,
  updateDeposit,
} from "../deposits";
import { http } from "../http";

describe("deposits service", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("constructs correct query url with filters in getDeposits", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } as never);

    await getDeposits({
      from: "2026-09-01",
      to: "2026-09-30",
      nasabah: 7,
      waste_type: 2,
      source: "confirmed",
      page: 1,
      page_size: 20,
    });

    expect(getSpy).toHaveBeenCalledWith(
      "/api/deposits/?from=2026-09-01&to=2026-09-30&nasabah=7&waste_type=2&source=confirmed&page=1&page_size=20",
    );
  });

  it("uses base url without query params when filters are empty in getDeposits", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } as never);

    await getDeposits();

    expect(getSpy).toHaveBeenCalledWith("/api/deposits/");
  });

  it("calls post with payload in createDeposit", async () => {
    const postSpy = vi
      .spyOn(http, "post")
      .mockResolvedValue({ id: 501 } as never);

    const payload = {
      nasabah_id: 7,
      waste_type_id: 2,
      weight_kg: "2.500",
      deposit_date: "2026-09-12",
    };

    await createDeposit(payload);

    expect(postSpy).toHaveBeenCalledWith("/api/deposits/", payload);
  });

  it("calls patch with payload in updateDeposit", async () => {
    const patchSpy = vi
      .spyOn(http, "patch")
      .mockResolvedValue({ id: 501 } as never);

    const payload = {
      weight_kg: "3.000",
      deposit_date: "2026-09-13",
    };

    await updateDeposit(501, payload);

    expect(patchSpy).toHaveBeenCalledWith("/api/deposits/501/", payload);
  });

  it("calls delete endpoint in deleteDeposit", async () => {
    const deleteSpy = vi.spyOn(http, "delete").mockResolvedValue({
      status: "ok",
      deleted_at: "2026-10-06T15:40:00Z",
    } as never);

    await deleteDeposit(501);

    expect(deleteSpy).toHaveBeenCalledWith("/api/deposits/501/");
  });

  it("requests CSV blob with Accept header in exportDepositsCsv", async () => {
    const mockBlob = new Blob(["id,nasabah\n1,Siti\n"], { type: "text/csv" });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => mockBlob,
    });
    globalThis.fetch = fetchMock;

    const result = await exportDepositsCsv({ source: "manual" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/deposits/export/?source=manual",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
        headers: { Accept: "text/csv" },
      }),
    );
    expect(result).toBe(mockBlob);
  });

  it("throws error when exportDepositsCsv response is not ok", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });
    globalThis.fetch = fetchMock;

    await expect(exportDepositsCsv()).rejects.toThrow(
      "Failed to export deposits CSV",
    );
  });
});
