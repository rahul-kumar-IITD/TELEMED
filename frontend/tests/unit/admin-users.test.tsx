import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const u = (id: number, role: string, active: boolean, name: string) => ({
  user_id: id,
  email: `${name.toLowerCase()}@example.test`,
  role,
  active,
  full_name: name,
  created_at: "2030-01-01T00:00:00Z",
});
const ME = u(7, "ADMIN", true, "Boss");
const DOC = u(11, "DOCTOR", true, "Doc");
const PAT = u(2, "PATIENT", true, "Pat");
const OFF = u(3, "PATIENT", false, "Off");
const PROFILE = { patient_id: 2, version_number: 1, full_name: "Pat Full", age: 34, gender: "FEMALE", phone: "+91 1", updated_at: "x" };

function row(email: string) {
  return screen.getAllByTestId("user-row").find((r) => r.textContent?.includes(email)) as HTMLElement;
}

describe("user list", () => {
  it("filters by role and disables Deactivate on own row", async () => {
    loginAs("ADMIN");
    const f = mockFetch((path) =>
      path.includes("role=DOCTOR") ? json(200, { items: [DOC], total: 1 }) : json(200, { items: [ME, DOC, OFF], total: 3 }),
    );
    renderApp("/admin/users");
    await screen.findAllByTestId("user-row");
    expect(within(row("boss@")).getByRole("button", { name: /Deactivate/ })).toBeDisabled();
    expect(within(row("doc@")).getByRole("button", { name: /Deactivate/ })).toBeEnabled();
    expect(within(row("off@")).getByRole("button", { name: /Reactivate/ })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Role"), "DOCTOR");
    await screen.findByText("doc@example.test");
    expect(f.mock.calls.some((c) => String(c[0]).includes("role=DOCTOR"))).toBe(true);
    expect(screen.getAllByTestId("user-row")).toHaveLength(1);
  });

  it("reactivates a user", async () => {
    loginAs("ADMIN");
    const f = mockFetch((_path, init) =>
      init.method === "PUT" ? json(200, { ...OFF, active: true }) : json(200, { items: [OFF], total: 1 }),
    );
    renderApp("/admin/users");
    await userEvent.click(await screen.findByRole("button", { name: /Reactivate/ }));
    expect(await screen.findByTestId("user-notice")).toHaveTextContent(/active/);
    expect(f.mock.calls.some((c) => String(c[0]) === "/api/admin/users/3/reactivate")).toBe(true);
  });

  it("shows active-appointments message on 409 and keeps the status", async () => {
    loginAs("ADMIN");
    const alertSpy = vi.fn();
    vi.stubGlobal("alert", alertSpy);
    mockFetch((_p, init) =>
      init.method === "PUT"
        ? json(409, { code: "ACTIVE_APPOINTMENTS_EXIST", message: "busy" })
        : json(200, { items: [DOC], total: 1 }),
    );
    renderApp("/admin/users");
    await userEvent.click(await screen.findByRole("button", { name: /Deactivate/ }));
    expect(await screen.findByTestId("user-notice")).toHaveTextContent(/active appointments/i);
    expect(screen.getByTestId("user-status")).toHaveTextContent("ACTIVE");
    expect(screen.getByRole("button", { name: /Deactivate/ })).toBeInTheDocument();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it("admin reaches both screens through navigation links", async () => {
    loginAs("ADMIN");
    mockFetch(() => json(200, { items: [], total: 0 }));
    renderApp("/admin/users");
    await userEvent.click(await screen.findByRole("link", { name: "Onboard doctor" }));
    expect(await screen.findByRole("heading", { name: "Onboard a doctor" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Users" }));
    expect(await screen.findByRole("heading", { name: "Users" })).toBeInTheDocument();
  });
});

describe("edit patient profile", () => {
  it("only patient rows have Edit profile; dialog is prefilled and saves", async () => {
    loginAs("ADMIN");
    const f = mockFetch((path, init) => {
      if (init.method === "PUT") return json(200, PROFILE);
      if (path === "/api/patients/2/profile") return json(200, PROFILE);
      return json(200, { items: [DOC, PAT], total: 2 });
    });
    renderApp("/admin/users");
    await screen.findAllByTestId("user-row");
    expect(within(row("doc@")).queryByRole("button", { name: /Edit profile/ })).toBeNull();
    await userEvent.click(within(row("pat@")).getByRole("button", { name: /Edit profile/ }));
    const dlg = await screen.findByRole("dialog");
    expect(await within(dlg).findByLabelText("Full name")).toHaveValue("Pat Full");
    expect(within(dlg).getByLabelText("Age")).toHaveValue(34);
    expect(within(dlg).getByLabelText("Gender")).toHaveValue("FEMALE");
    expect(within(dlg).getByLabelText(/Phone/)).toHaveValue("+91 1");
    await userEvent.click(within(dlg).getByRole("button", { name: "Save" }));
    expect(await within(dlg).findByText("Profile saved.")).toBeInTheDocument();
    const put = f.mock.calls.find((c) => (c[1] as RequestInit).method === "PUT");
    expect(String(put?.[0])).toBe("/api/admin/patients/2/profile");
    expect(JSON.parse(String((put?.[1] as RequestInit).body))).toEqual({
      full_name: "Pat Full",
      age: 34,
      gender: "FEMALE",
      phone: "+91 1",
    });
  });

  it("shows server 422 age error and no success message", async () => {
    loginAs("ADMIN");
    mockFetch((path, init) => {
      if (init.method === "PUT")
        return json(422, { code: "VALIDATION_ERROR", message: "x", errors: [{ field: "age", message: "Age must be 1 to 130." }] });
      if (path === "/api/patients/2/profile") return json(200, PROFILE);
      return json(200, { items: [PAT], total: 1 });
    });
    renderApp("/admin/users");
    await userEvent.click(await screen.findByRole("button", { name: /Edit profile/ }));
    const dlg = await screen.findByRole("dialog");
    const age = await within(dlg).findByLabelText("Age");
    await userEvent.clear(age);
    await userEvent.type(age, "200");
    await userEvent.click(within(dlg).getByRole("button", { name: "Save" }));
    expect(await within(dlg).findByText("Age must be 1 to 130.")).toBeInTheDocument();
    expect(within(dlg).queryByText("Profile saved.")).toBeNull();
    expect(age).toHaveValue(200);
  });
});
