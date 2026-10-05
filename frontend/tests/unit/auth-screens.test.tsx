import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getSession } from "../../src/api/session";
import { FUTURE, json, mockFetch, renderApp, TOKEN } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

async function fillLogin(email = "a@example.test", password = "Passw0rd!") {
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: "Log in" }));
}

describe("login screen", () => {
  it("stores the token in sessionStorage only and lands the role home", async () => {
    mockFetch((path) =>
      path === "/api/auth/login"
        ? json(200, { access_token: TOKEN, token_type: "bearer", expires_in: 3600, expires_at: FUTURE, user_id: 2, role: "DOCTOR" })
        : json(200, { items: [], total: 0 }),
    );
    renderApp("/login");
    await fillLogin();
    expect(await screen.findByRole("heading", { name: "Daily queue" })).toBeInTheDocument();
    expect(sessionStorage.getItem("telemed.session")).toContain(TOKEN);
    expect(localStorage.length).toBe(0);
  });

  it("shows one generic message in a live region on 401 and does not treat it as expiry", async () => {
    mockFetch(() => json(401, { code: "INVALID_CREDENTIALS", message: "Invalid email or password." }));
    renderApp("/login");
    const region = screen.getAllByRole("alert")[0];
    await fillLogin();
    await waitFor(() => expect(region).toHaveTextContent("Invalid email or password."));
    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(getSession()).toBeNull();
  });

  it("rejects empty fields without calling the API", async () => {
    const fetchMock = mockFetch(() => json(200, {}));
    renderApp("/login");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a try-again message on a 503 and a generic one on network failure", async () => {
    mockFetch(() => json(503, { code: "SERVICE_UNAVAILABLE", message: "x" }));
    const first = renderApp("/login");
    await fillLogin();
    expect(await screen.findByText(/try again/i)).toBeInTheDocument();
    first.unmount();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("down"))));
    renderApp("/login");
    await fillLogin();
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });
});

async function fillRegister(overrides: Partial<Record<string, string>> = {}) {
  const v = { name: "Pat One", age: "34", phone: "+911234567890", email: "p@example.test", password: "Passw0rd!", ...overrides };
  await userEvent.type(screen.getByLabelText("Full name"), v.name);
  await userEvent.type(screen.getByLabelText("Age"), v.age);
  await userEvent.selectOptions(screen.getByLabelText("Gender"), "FEMALE");
  await userEvent.type(screen.getByLabelText(/Phone/), v.phone);
  await userEvent.type(screen.getByLabelText(/Email/), v.email);
  await userEvent.type(screen.getByLabelText(/^Password/), v.password);
  await userEvent.click(screen.getByRole("button", { name: "Register" }));
}

describe("register screen", () => {
  it("shows the duplicate-email message on 409 inside a live region", async () => {
    mockFetch(() => json(409, { code: "EMAIL_ALREADY_REGISTERED", message: "dup" }));
    renderApp("/register");
    await fillRegister();
    const message = await screen.findByText("An account with this email already exists.");
    expect(message.closest("[role=alert]")).not.toBeNull();
    expect(screen.getByRole("heading", { name: "Create account" })).toBeInTheDocument();
  });

  it("validates client-side and does not call the API", async () => {
    const fetchMock = mockFetch(() => json(201, {}));
    renderApp("/register");
    await fillRegister({ age: "200", email: "nope", password: "short" });
    expect(await screen.findByText(/Age must be/)).toBeInTheDocument();
    expect(screen.getByText(/valid email/)).toBeInTheDocument();
    expect(screen.getByText(/Password must be/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("goes to login with a notice after success", async () => {
    mockFetch(() => json(201, { user_id: 5, role: "PATIENT", email: "p@example.test" }));
    renderApp("/register");
    await fillRegister();
    expect(await screen.findByText("Account created. Please log in.")).toBeInTheDocument();
  });

  it("maps server 422 field errors and falls back to a banner", async () => {
    mockFetch(() => json(422, { code: "VALIDATION_ERROR", message: "x", errors: [{ field: "phone", message: "bad phone" }] }));
    const first = renderApp("/register");
    await fillRegister();
    expect(await screen.findByText("bad phone")).toBeInTheDocument();
    first.unmount();
    mockFetch(() => json(422, { code: "VALIDATION_ERROR", message: "x", errors: [{ field: "body", message: "m" }] }));
    renderApp("/register");
    await fillRegister();
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });

  it("shows a try-again message on 503", async () => {
    mockFetch(() => json(503, { code: "SERVICE_UNAVAILABLE", message: "x" }));
    renderApp("/register");
    await fillRegister();
    expect(await screen.findByText(/try again/i)).toBeInTheDocument();
  });
});
