import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createNasabah,
  getNasabahDetail,
  getNasabahList,
  updateNasabah,
} from "../nasabah";
import { http } from "../http";

describe("nasabah service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("constructs correct query url in getNasabahList", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } as never);

    await getNasabahList({ q: "siti", page: 1, page_size: 20 });

    expect(getSpy).toHaveBeenCalledWith(
      "/api/nasabah/?q=siti&page=1&page_size=20",
    );
  });

  it("uses base url without query params when params are omitted in getNasabahList", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } as never);

    await getNasabahList();

    expect(getSpy).toHaveBeenCalledWith("/api/nasabah/");
  });

  it("calls post with payload in createNasabah", async () => {
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({
      id: 7,
      name: "Siti Aminah",
    } as never);

    await createNasabah({ name: "Siti Aminah" });

    expect(postSpy).toHaveBeenCalledWith("/api/nasabah/", {
      name: "Siti Aminah",
    });
  });

  it("calls get with id in getNasabahDetail", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({
      id: 7,
      name: "Siti",
    } as never);

    await getNasabahDetail(7);

    expect(getSpy).toHaveBeenCalledWith("/api/nasabah/7/");
  });

  it("calls patch with payload in updateNasabah", async () => {
    const patchSpy = vi.spyOn(http, "patch").mockResolvedValue({
      id: 7,
      name: "Siti Updated",
    } as never);

    await updateNasabah(7, { name: "Siti Updated", is_active: false });

    expect(patchSpy).toHaveBeenCalledWith("/api/nasabah/7/", {
      name: "Siti Updated",
      is_active: false,
    });
  });
});
