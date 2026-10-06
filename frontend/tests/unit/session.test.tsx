import { describe, expect, it, vi } from "vitest";
import { clearSession, getSession, getToken, saveSession, subscribeSession } from "../../src/api/session";
import { FUTURE, TOKEN } from "./helpers";

const login = {
  access_token: TOKEN,
  token_type: "bearer",
  expires_in: 3600,
  expires_at: FUTURE,
  user_id: 3,
  role: "PATIENT" as const,
};

describe("session storage", () => {
  it("stores the token in sessionStorage and never in localStorage", () => {
    saveSession(login);
    expect(getToken()).toBe(TOKEN);
    expect(sessionStorage.length).toBe(1);
    expect(localStorage.length).toBe(0);
    expect(getSession()).toMatchObject({ user_id: 3, role: "PATIENT" });
  });

  it("clears the session and notifies subscribers", () => {
    const listener = vi.fn();
    const off = subscribeSession(listener);
    saveSession(login);
    clearSession();
    off();
    clearSession();
    expect(listener).toHaveBeenCalledTimes(2);
    expect(getSession()).toBeNull();
    expect(getToken()).toBeNull();
  });

  it("ignores malformed or expired stored sessions", () => {
    sessionStorage.setItem("telemed.session", "not json");
    expect(getSession()).toBeNull();
    sessionStorage.setItem("telemed.session", JSON.stringify({ access_token: 1 }));
    expect(getSession()).toBeNull();
    sessionStorage.setItem("telemed.session", JSON.stringify({ ...login, role: "ROOT" }));
    expect(getSession()).toBeNull();
    saveSession({ ...login, expires_at: new Date(Date.now() - 1000).toISOString() });
    expect(getSession()).toBeNull();
    sessionStorage.removeItem("telemed.session");
    expect(getSession()).toBeNull();
  });
});
