// The only place that calls fetch. Handles bearer auth, 401 session expiry and 503.
import { MESSAGES } from "../config/routes";
import type { ApiErrorBody, FieldError } from "../types/contracts";
import { clearSession, getToken } from "./session";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldError[];

  constructor(status: number, code: string, message: string, fieldErrors: FieldError[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
  }

  /** Message safe to show users: never technical detail. */
  get userMessage(): string {
    return this.status === 503 ? MESSAGES.busy : MESSAGES.generic;
  }
}

interface RequestOptions {
  body?: unknown;
  /** false for public endpoints (login/register): no bearer header, 401 is not session expiry. */
  auth?: boolean;
  signal?: AbortSignal;
}

async function readBody(res: Response): Promise<Partial<ApiErrorBody> | null> {
  try {
    return (await res.json()) as Partial<ApiErrorBody>;
  } catch {
    return null;
  }
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const auth = opts.auth ?? true;
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = auth ? getToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: opts.signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "NETWORK_ERROR", MESSAGES.generic);
  }

  if (res.ok) {
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  const body = await readBody(res);
  const code = body?.code ?? "UNKNOWN";
  if (res.status === 401 && auth && code !== "INVALID_CREDENTIALS") {
    clearSession();
  }
  throw new ApiError(res.status, code, body?.message ?? MESSAGES.generic, body?.errors ?? []);
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, { signal }),
  post: <T>(path: string, body: unknown, auth = true) => request<T>("POST", path, { body, auth }),
};
