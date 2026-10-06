// The single module that touches the access token. sessionStorage only, never localStorage.
import type { LoginResponse, Role, Session } from "../types/contracts";

const KEY = "telemed.session";
const listeners = new Set<() => void>();
let cached: { raw: string | null; value: Session | null } = { raw: null, value: null };

function parse(raw: string | null): Session | null {
  if (!raw) return null;
  try {
    const v = JSON.parse(raw) as Partial<Session>;
    if (
      typeof v.access_token !== "string" ||
      typeof v.user_id !== "number" ||
      typeof v.expires_at !== "string" ||
      (v.role !== "PATIENT" && v.role !== "DOCTOR" && v.role !== "ADMIN")
    ) {
      return null;
    }
    const role: Role = v.role;
    if (Date.parse(v.expires_at) <= Date.now()) return null;
    return { access_token: v.access_token, user_id: v.user_id, role, expires_at: v.expires_at };
  } catch {
    return null;
  }
}

export function getSession(): Session | null {
  const raw = sessionStorage.getItem(KEY);
  if (raw !== cached.raw) cached = { raw, value: parse(raw) };
  return cached.value;
}

export function getToken(): string | null {
  return getSession()?.access_token ?? null;
}

export function saveSession(login: LoginResponse): void {
  const s: Session = {
    access_token: login.access_token,
    user_id: login.user_id,
    role: login.role,
    expires_at: login.expires_at,
  };
  sessionStorage.setItem(KEY, JSON.stringify(s));
  listeners.forEach((l) => l());
}

export function clearSession(): void {
  sessionStorage.removeItem(KEY);
  listeners.forEach((l) => l());
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
