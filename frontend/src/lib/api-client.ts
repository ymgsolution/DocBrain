import type { ApiErrorBody, ApiErrorField } from "@/types/api";

export class ApiError extends Error {
  status: number;
  code: string;
  correlationId: string;
  fields?: ApiErrorField[];

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error.code;
    this.correlationId = body.error.correlationId;
    this.fields = body.error.fields;
  }
}

const BFF_BASE = "/api/bff";

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new ApiError(response.status, data as ApiErrorBody);
  }

  return data as T;
}

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      value.forEach((v) => search.append(key, String(v)));
    } else {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const apiClient = {
  get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    return fetch(`${BFF_BASE}${path}${buildQuery(params)}`, { credentials: "include" }).then((r) =>
      handleResponse<T>(r),
    );
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return fetch(`${BFF_BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "include",
    }).then((r) => handleResponse<T>(r));
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return fetch(`${BFF_BASE}${path}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "include",
    }).then((r) => handleResponse<T>(r));
  },

  delete<T>(path: string): Promise<T> {
    return fetch(`${BFF_BASE}${path}`, { method: "DELETE", credentials: "include" }).then((r) =>
      handleResponse<T>(r),
    );
  },

  postForm<T>(path: string, formData: FormData): Promise<T> {
    return fetch(`${BFF_BASE}${path}`, { method: "POST", body: formData, credentials: "include" }).then((r) =>
      handleResponse<T>(r),
    );
  },
};
