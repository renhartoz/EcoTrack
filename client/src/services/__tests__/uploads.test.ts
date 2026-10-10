import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createImageUpload,
  createTextUpload,
  getUploadDetail,
  getUploadImageUrl,
  getUploads,
  retryUpload,
} from "../uploads";
import { http } from "../http";

describe("uploads service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("builds correct FormData in createImageUpload", async () => {
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({
      id: 42,
      source_type: "image",
      status: "processing",
    } as never);

    const blob = new Blob(["fake-image-bytes"], { type: "image/jpeg" });
    const sha256 =
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    await createImageUpload(blob, sha256, "custom_page.jpg");

    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy.mock.calls[0][0]).toBe("/api/uploads/");

    const sentFormData = postSpy.mock.calls[0][1] as FormData;
    expect(sentFormData).toBeInstanceOf(FormData);
    expect(sentFormData.get("source_sha256")).toBe(sha256);

    const sentFile = sentFormData.get("image") as File;
    expect(sentFile).toBeDefined();
    expect(sentFile.name).toBe("custom_page.jpg");
  });

  it("sends text payload in createTextUpload", async () => {
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({
      id: 43,
      source_type: "text",
      status: "processing",
    } as never);

    await createTextUpload("12/9 Bu Siti botol 2 kg");

    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy).toHaveBeenCalledWith("/api/uploads/text/", {
      text: "12/9 Bu Siti botol 2 kg",
    });
  });

  it("formats pagination query in getUploads", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } as never);

    await getUploads(2, 25);

    expect(getSpy).toHaveBeenCalledWith("/api/uploads/?page=2&page_size=25");
  });

  it("calls upload detail endpoint in getUploadDetail", async () => {
    const getSpy = vi.spyOn(http, "get").mockResolvedValue({ id: 10 } as never);

    await getUploadDetail(10);

    expect(getSpy).toHaveBeenCalledWith("/api/uploads/10/");
  });

  it("calls retry endpoint with empty payload in retryUpload", async () => {
    const postSpy = vi
      .spyOn(http, "post")
      .mockResolvedValue({ id: 10 } as never);

    await retryUpload(10);

    expect(postSpy).toHaveBeenCalledWith("/api/uploads/10/retry/", {});
  });

  it("returns correct image stream url in getUploadImageUrl", () => {
    expect(getUploadImageUrl(55)).toBe("/api/uploads/55/image/");
  });
});
