import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getSession } from "../../src/api/session";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("route guards", () => {
  it.each(["/queue", "/doctors", "/admin/users"])("redirects %s to /login when unauthenticated", async (path) => {
    mockFetch(() => json(200, {}));
    renderApp(path);
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it.each([
    ["PATIENT", "/admin/users"],
    ["PATIENT", "/queue"],
    ["DOCTOR", "/admin/users"],
    ["ADMIN", "/queue"],
  ] as const)("shows not-allowed for %s on %s", async (role, path) => {
    loginAs(role);
    mockFetch(() => json(200, { items: [], total: 0 }));
    renderApp(path);
    expect(await screen.findByRole("heading", { name: "Not allowed" })).toBeInTheDocument();
  });

  it.each([
    ["PATIENT", "Find a doctor"],
    ["DOCTOR", "Daily queue"],
    ["ADMIN", "Users"],
  ] as const)("lands %s on its home shell from /", async (role, title) => {
    loginAs(role);
    mockFetch(() => json(200, { items: [], total: 0 }));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
  });

  it("shows the not-found page for unknown routes and 404 objects", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(404, { code: "NOT_FOUND", message: "Resource not found." }));
    const first = renderApp("/no-such-page");
    expect(await screen.findByRole("heading", { name: /not found/i })).toBeInTheDocument();
    first.unmount();
    renderApp("/doctors/999");
    expect(await screen.findByRole("heading", { name: /not found/i })).toBeInTheDocument();
  });

  it("clears the session and goes to /login on a 401 from a protected call", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(401, { code: "UNAUTHENTICATED", message: "Authentication required." }));
    renderApp("/doctors");
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(getSession()).toBeNull();
  });

  it("shows a generic try-again message on 503 and keeps the session", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(503, { code: "SERVICE_UNAVAILABLE", message: "SQL boom" }));
    renderApp("/doctors");
    const alert = await screen.findByTestId("error-state");
    expect(alert).toHaveTextContent(/try again/i);
    expect(alert).not.toHaveTextContent(/SQL|503/);
    expect(getSession()).not.toBeNull();
  });

  it("redirects logged-in users away from /login and logs out from the header", async () => {
    loginAs("ADMIN");
    mockFetch(() => json(200, { items: [], total: 0 }));
    renderApp("/login");
    expect(await screen.findByRole("heading", { name: "Users" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Log out" }));
    await waitFor(() => expect(getSession()).toBeNull());
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });
});
