import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, renewCsrfToken, setUnauthorizedHandler } from "../http";
import { ApiError } from "@/types/api";

describe("http client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
    document.cookie = "csrftoken=mock-csrf-token; path=/";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    document.cookie =
      "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  });

  it("attaches X-CSRFToken header on unsafe methods", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    });
    globalThis.fetch = fetchMock;

    await http.post("/api/test/", { data: 1 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const postHeaders = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(postHeaders.get("X-CSRFToken")).toBe("mock-csrf-token");

    await http.patch("/api/test/1/", { data: 2 });
    const patchHeaders = fetchMock.mock.calls[1][1]?.headers as Headers;
    expect(patchHeaders.get("X-CSRFToken")).toBe("mock-csrf-token");

    await http.delete("/api/test/1/");
    const deleteHeaders = fetchMock.mock.calls[2][1]?.headers as Headers;
    expect(deleteHeaders.get("X-CSRFToken")).toBe("mock-csrf-token");
  });

  it("does not attach X-CSRFToken header on safe methods", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 1 }),
    });
    globalThis.fetch = fetchMock;

    await http.get("/api/test/");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const getHeaders = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(getHeaders.get("X-CSRFToken")).toBeNull();
  });

  it("performs single-flight refresh for concurrent 401 requests", async () => {
    let refreshCalls = 0;

    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url === "/api/auth/refresh/") {
        refreshCalls += 1;
        return {
          ok: true,
          status: 200,
          json: async () => ({ success: true }),
        };
      }

      if (url.startsWith("/api/item/")) {
        const itemNumber = url.split("/").pop();
        const callCount = fetchMock.mock.calls.filter(
          (c) => c[0] === url,
        ).length;
        if (callCount === 1) {
          return {
            ok: false,
            status: 401,
            json: async () => ({
              error: { code: "UNAUTHENTICATED", message: "Token expired" },
            }),
          };
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ item: itemNumber }),
        };
      }

      return {
        ok: false,
        status: 404,
        json: async () => ({
          error: { code: "NOT_FOUND", message: "Not found" },
        }),
      };
    });

    globalThis.fetch = fetchMock;

    const results = await Promise.all([
      http.get<{ item: string }>("/api/item/1"),
      http.get<{ item: string }>("/api/item/2"),
      http.get<{ item: string }>("/api/item/3"),
    ]);

    expect(results).toEqual([{ item: "1" }, { item: "2" }, { item: "3" }]);
    expect(refreshCalls).toBe(1);
  });

  it("excludes auth endpoints from 401 refresh-and-retry logic", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({
        error: { code: "UNAUTHENTICATED", message: "Invalid credentials" },
      }),
    });
    globalThis.fetch = fetchMock;

    await expect(http.post("/api/auth/login/", {})).rejects.toBeInstanceOf(
      ApiError,
    );
    await expect(http.post("/api/auth/refresh/", {})).rejects.toBeInstanceOf(
      ApiError,
    );
    await expect(http.post("/api/auth/logout/", {})).rejects.toBeInstanceOf(
      ApiError,
    );

    const refreshCalls = fetchMock.mock.calls.filter(
      (c) => c[0] === "/api/auth/refresh/",
    );
    expect(refreshCalls).toHaveLength(1);
  });

  it("calls raw fetch on renewCsrfToken with no interceptors", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
    });
    globalThis.fetch = fetchMock;

    await renewCsrfToken();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/me/", {
      method: "GET",
      credentials: "include",
    });
  });

  it("renews CSRF token and retries on 403 CSRF_FAILED", async () => {
    let callCount = 0;
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url === "/api/auth/me/") {
        document.cookie = "csrftoken=new-csrf-token; path=/";
        return {
          ok: true,
          status: 200,
        };
      }

      if (url === "/api/deposits/") {
        callCount += 1;
        if (callCount === 1) {
          return {
            ok: false,
            status: 403,
            clone: () => ({
              json: async () => ({
                error: { code: "CSRF_FAILED", message: "Invalid CSRF" },
              }),
            }),
            json: async () => ({
              error: { code: "CSRF_FAILED", message: "Invalid CSRF" },
            }),
          };
        }
        return {
          ok: true,
          status: 201,
          json: async () => ({ id: 101 }),
        };
      }

      return { ok: false, status: 500 };
    });

    globalThis.fetch = fetchMock;

    const result = await http.post<{ id: number }>("/api/deposits/", {
      amount: 10,
    });
    expect(result).toEqual({ id: 101 });
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/me/", {
      method: "GET",
      credentials: "include",
    });
    expect(callCount).toBe(2);
  });

  it("invokes unauthorized handler when refresh fails", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);

    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url === "/api/auth/refresh/") {
        return {
          ok: false,
          status: 401,
          json: async () => ({ error: { code: "UNAUTHENTICATED" } }),
        };
      }
      return {
        ok: false,
        status: 401,
        json: async () => ({ error: { code: "UNAUTHENTICATED" } }),
      };
    });
    globalThis.fetch = fetchMock;

    await expect(http.get("/api/protected/")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});
