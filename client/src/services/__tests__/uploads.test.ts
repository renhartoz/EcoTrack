import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createImageUpload,
  createTextUpload,
  getUploadDetail,
  getUploadImageUrl,
  getUploads,
  retryUpload,
} from "../uploads";

describe("uploads service", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("sends multipart form data with image and source_sha256 on createImageUpload", async () => {
    let capturedBody: FormData | undefined;
    const fetchMock = vi
      .fn()
      .mockImplementation(async (_url: string, init?: RequestInit) => {
        capturedBody = init?.body as FormData;
        return {
          ok: true,
          status: 201,
          json: async () => ({ id: 41, status: "ready", rows: [] }),
        };
      });
    globalThis.fetch = fetchMock;

    const dummyBlob = new Blob(["test-image-content"], { type: "image/jpeg" });
    const dummySha256 =
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    const result = await createImageUpload(dummyBlob, dummySha256, "page1.jpg");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/uploads/");
    expect(capturedBody).toBeInstanceOf(FormData);
    expect(capturedBody?.get("source_sha256")).toBe(dummySha256);
    const filePart = capturedBody?.get("image");
    expect(filePart).toBeInstanceOf(Blob);
    expect(result.id).toBe(41);
  });

  it("sends json payload on createTextUpload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: 42, status: "ready", rows: [] }),
    });
    globalThis.fetch = fetchMock;

    const sampleText = "12/9 Bu Siti botol 2,5 kg";
    const result = await createTextUpload(sampleText);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/uploads/text/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: sampleText }),
      }),
    );
    expect(result.id).toBe(42);
  });

  it("requests paginated list on getUploads", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ count: 1, next: null, previous: null, results: [] }),
    });
    globalThis.fetch = fetchMock;

    await getUploads(2, 10);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/uploads/?page=2&page_size=10",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("requests upload detail on getUploadDetail", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 41, status: "ready", rows: [] }),
    });
    globalThis.fetch = fetchMock;

    const result = await getUploadDetail(41);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/uploads/41/",
      expect.objectContaining({ method: "GET" }),
    );
    expect(result.id).toBe(41);
  });

  it("posts retry request on retryUpload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 41, status: "ready", rows: [] }),
    });
    globalThis.fetch = fetchMock;

    const result = await retryUpload(41);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/uploads/41/retry/",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.id).toBe(41);
  });

  it("returns correct image url from getUploadImageUrl", () => {
    expect(getUploadImageUrl(41)).toBe("/api/uploads/41/image/");
  });
});
