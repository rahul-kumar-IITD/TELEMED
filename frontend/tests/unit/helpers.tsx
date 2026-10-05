import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AppRoutes } from "../../src/app/routes";
import { saveSession } from "../../src/api/session";
import type { Role } from "../../src/types/contracts";

export const FUTURE = new Date(Date.now() + 3_600_000).toISOString();
export const TOKEN = "aaa.bbb.ccc";

export function loginAs(role: Role): void {
  saveSession({ access_token: TOKEN, token_type: "bearer", expires_in: 3600, expires_at: FUTURE, user_id: 7, role });
}

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function mockFetch(handler: (path: string, init: RequestInit) => Response | Promise<Response>) {
  const fn = vi.fn((path: string, init: RequestInit = {}) => Promise.resolve(handler(path, init)));
  vi.stubGlobal("fetch", fn);
  return fn;
}

export function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}
