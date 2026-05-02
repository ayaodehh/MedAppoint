import type { ApiErrorResponse, PaginatedResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
const REQUEST_TIMEOUT_MS = 8_000;

export class ApiError extends Error {
  status: number;
  data: ApiErrorResponse | null;

  constructor(message: string, status: number, data: ApiErrorResponse | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

type RequestOptions = Omit<RequestInit, "body" | "credentials"> & {
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
      body: hasBody ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
      signal: controller.signal,
    });

    const text = await response.text();
    const data = text ? (JSON.parse(text) as ApiErrorResponse) : null;

    if (!response.ok) {
      throw new ApiError(extractErrorMessage(data, response.status), response.status, data);
    }

    return data as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The server took too long to respond.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

function extractErrorMessage(data: ApiErrorResponse | null, status: number): string {
  if (data && typeof data === "object") {
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    const nonField = data["non_field_errors"];
    if (Array.isArray(nonField) && typeof nonField[0] === "string") {
      return nonField[0];
    }
    for (const [key, value] of Object.entries(data)) {
      if (key === "detail" || key === "non_field_errors") continue;
      if (Array.isArray(value) && typeof value[0] === "string") {
        return `${key}: ${value[0]}`;
      }
      if (typeof value === "string" && value.trim()) {
        return `${key}: ${value}`;
      }
    }
  }
  if (status === 401) return "You need to sign in again.";
  if (status === 403) return "You don't have permission to do that.";
  if (status === 429) return "Too many attempts. Please wait and try again.";
  return "Request failed.";
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "DELETE" }),
};

export function unwrapListResponse<T>(data: T[] | PaginatedResponse<T>): T[] {
  return Array.isArray(data) ? data : data.results;
}
