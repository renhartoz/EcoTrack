import { ApiError, type ApiErrorResponse } from "@/types/api";

export interface RequestOptions extends RequestInit {
  _isRetry?: boolean;
  _csrfRetried?: boolean;
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler;
}

function notifyUnauthorized(): void {
  if (unauthorizedHandler) {
    unauthorizedHandler();
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function isUnsafeMethod(method: string): boolean {
  return !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

function isAuthExcludedUrl(url: string): boolean {
  return (
    url.includes("/api/auth/login/") ||
    url.includes("/api/auth/refresh/") ||
    url.includes("/api/auth/logout/")
  );
}

let refreshPromise: Promise<boolean> | null = null;

async function requestTokenRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const csrfToken = getCsrfToken();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (csrfToken) {
          headers["X-CSRFToken"] = csrfToken;
        }
        const response = await fetch("/api/auth/refresh/", {
          method: "POST",
          headers,
          body: JSON.stringify({}),
          credentials: "include",
        });
        return response.ok;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function renewCsrfToken(): Promise<void> {
  await fetch("/api/auth/me/", {
    method: "GET",
    credentials: "include",
  });
}

async function parseApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as ApiErrorResponse;
    if (payload?.error?.code && payload?.error?.message) {
      return new ApiError(
        response.status,
        payload.error.code,
        payload.error.message,
        payload.error.details,
      );
    }
  } catch {
    return new ApiError(response.status, "UNKNOWN_ERROR", response.statusText);
  }
  return new ApiError(response.status, "UNKNOWN_ERROR", response.statusText);
}

export async function request<T>(
  url: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (isUnsafeMethod(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  const response = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (response.status === 401) {
    if (!isAuthExcludedUrl(url) && !options._isRetry) {
      const refreshed = await requestTokenRefresh();
      if (refreshed) {
        return request<T>(url, {
          ...options,
          _isRetry: true,
        });
      }
      notifyUnauthorized();
    }
    throw await parseApiError(response);
  }

  if (response.status === 403 && !options._csrfRetried) {
    const clonedResponse = response.clone();
    try {
      const payload = (await clonedResponse.json()) as ApiErrorResponse;
      if (payload?.error?.code === "CSRF_FAILED") {
        await renewCsrfToken();
        return request<T>(url, {
          ...options,
          _csrfRetried: true,
        });
      }
    } catch {
      throw await parseApiError(response);
    }
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const http = {
  get: <T>(url: string, options?: RequestOptions) =>
    request<T>(url, { ...options, method: "GET" }),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) => {
    const headers = new Headers(options?.headers);
    let requestBody: BodyInit | undefined;
    if (body instanceof FormData) {
      requestBody = body;
    } else if (body !== undefined && body !== null) {
      requestBody = typeof body === "string" ? body : JSON.stringify(body);
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
    }
    return request<T>(url, {
      ...options,
      method: "POST",
      headers,
      body: requestBody,
    });
  },
  patch: <T>(url: string, body?: unknown, options?: RequestOptions) => {
    const headers = new Headers(options?.headers);
    let requestBody: BodyInit | undefined;
    if (body instanceof FormData) {
      requestBody = body;
    } else if (body !== undefined && body !== null) {
      requestBody = typeof body === "string" ? body : JSON.stringify(body);
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
    }
    return request<T>(url, {
      ...options,
      method: "PATCH",
      headers,
      body: requestBody,
    });
  },
  delete: <T>(url: string, options?: RequestOptions) =>
    request<T>(url, { ...options, method: "DELETE" }),
};
