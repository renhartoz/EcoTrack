import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { confirmAllRows, confirmRow, rejectRow, updateRow } from "../rows";
import { ERROR_MESSAGES, type ErrorCode } from "@/lib/strings.id";
import { ApiError } from "@/types/api";
import { http } from "../http";

describe("rows service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls patch with payload in updateRow", async () => {
    const patchSpy = vi
      .spyOn(http, "patch")
      .mockResolvedValue({ id: 101 } as never);

    const payload = {
      tanggal: "2026-09-12",
      nasabah_id: 5,
      waste_type_id: 3,
      weight_kg: "2.500",
    };

    await updateRow(101, payload);

    expect(patchSpy).toHaveBeenCalledWith("/api/rows/101/", payload);
  });

  it("calls post with empty body in confirmRow", async () => {
    const postSpy = vi
      .spyOn(http, "post")
      .mockResolvedValue({ id: 101, status: "saved" } as never);

    await confirmRow(101);

    expect(postSpy).toHaveBeenCalledWith("/api/rows/101/confirm/", {});
  });

  it("calls post with empty body in rejectRow", async () => {
    const postSpy = vi
      .spyOn(http, "post")
      .mockResolvedValue({ id: 101, status: "rejected" } as never);

    await rejectRow(101);

    expect(postSpy).toHaveBeenCalledWith("/api/rows/101/reject/", {});
  });

  it("calls post with empty body in confirmAllRows", async () => {
    const postSpy = vi
      .spyOn(http, "post")
      .mockResolvedValue({ confirmed: 4, skipped: 1 } as never);

    await confirmAllRows(42);

    expect(postSpy).toHaveBeenCalledWith("/api/uploads/42/confirm-all/", {});
  });

  it("propagates 409 ApiError with ROW_NOT_PENDING code", async () => {
    const error = new ApiError(409, "ROW_NOT_PENDING", "Row is not pending");
    vi.spyOn(http, "post").mockRejectedValue(error);

    await expect(confirmRow(101)).rejects.toThrow(error);
    expect(ERROR_MESSAGES[error.code as ErrorCode]).toBe(
      "Baris sudah diproses sebelumnya",
    );
  });

  it("propagates 422 ApiError with ROW_HAS_HARD_FLAGS code", async () => {
    const error = new ApiError(422, "ROW_HAS_HARD_FLAGS", "Row has hard flags");
    vi.spyOn(http, "post").mockRejectedValue(error);

    await expect(confirmRow(101)).rejects.toThrow(error);
    expect(ERROR_MESSAGES[error.code as ErrorCode]).toBe(
      "Baris memiliki kesalahan yang harus diperbaiki",
    );
  });
});
