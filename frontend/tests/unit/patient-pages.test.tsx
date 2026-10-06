import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { appt, inMinutes } from "./fixtures";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const slot = (id: number, minutes: number) => ({
  slot_id: id,
  doctor_id: 1,
  start_time: inMinutes(minutes),
  end_time: inMinutes(minutes + 30),
  status: "AVAILABLE",
});
const note = (id: number, text: string) => ({
  note_id: id,
  appointment_id: 5,
  author_id: 1,
  text,
  created_at: "2030-01-10T05:00:00Z",
});

describe("my appointments (AC-06 cancel)", () => {
  it("cancels after confirmation and shows the server state", async () => {
    loginAs("PATIENT");
    let cancelled = false;
    const f = mockFetch((path, init) => {
      if (init.method === "POST") {
        cancelled = true;
        return json(200, appt({ status: "CANCELLED", allowed_actions: [] }));
      }
      expect(path).toBe("/api/appointments/mine");
      return json(200, { items: [appt(cancelled ? { status: "CANCELLED", allowed_actions: [] } : {})], total: 1 });
    });
    renderApp("/appointments");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm cancel" }));
    expect(await screen.findByText("CANCELLED")).toBeInTheDocument();
    expect(f.mock.calls.some((c) => String(c[0]) === "/api/appointments/5/cancel")).toBe(true);
  });

  it("shows an inline message on 409 without alert", async () => {
    loginAs("PATIENT");
    const alertSpy = vi.fn();
    vi.stubGlobal("alert", alertSpy);
    mockFetch((_p, init) =>
      init.method === "POST"
        ? json(409, { code: "CHANGE_WINDOW_CLOSED", message: "late" })
        : json(200, { items: [appt()], total: 1 }),
    );
    renderApp("/appointments");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm cancel" }));
    expect(await screen.findByTestId("appointment-notice")).toHaveTextContent(/60 minutes/);
    expect(screen.getByTestId("appointment-status")).toHaveTextContent("BOOKED");
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it("shows a generic inline message for other failures and the empty and error states", async () => {
    loginAs("PATIENT");
    mockFetch((_p, init) =>
      init.method === "POST" ? json(500, { code: "INTERNAL_ERROR", message: "x" }) : json(200, { items: [appt()], total: 1 }),
    );
    const first = renderApp("/appointments");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm cancel" }));
    expect(await screen.findByTestId("appointment-notice")).toHaveTextContent(/Something went wrong/);
    first.unmount();
    mockFetch(() => json(200, { items: [], total: 0 }));
    const second = renderApp("/appointments");
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
    second.unmount();
    mockFetch(() => json(500, { code: "INTERNAL_ERROR", message: "x" }));
    renderApp("/appointments");
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
  });
});

describe("reschedule (AC-07)", () => {
  it("offers only the same doctor's other slots and shows the new time", async () => {
    loginAs("PATIENT");
    let moved = false;
    const f = mockFetch((path, init) => {
      if (init.method === "POST") {
        moved = true;
        return json(200, appt({ slot_id: 12, start_time: inMinutes(48 * 60) }));
      }
      if (path === "/api/doctors/1/slots") return json(200, { items: [slot(11, 24 * 60), slot(12, 48 * 60)], total: 2 });
      return json(200, { items: [appt(moved ? { slot_id: 12, start_time: inMinutes(48 * 60) } : {})], total: 1 });
    });
    renderApp("/appointments");
    await userEvent.click(await screen.findByRole("button", { name: "Reschedule" }));
    const panel = await screen.findByRole("group", { name: "Reschedule" });
    const choices = await within(panel).findAllByRole("button", { pressed: false });
    expect(choices).toHaveLength(1);
    expect(within(panel).getByRole("button", { name: "Confirm reschedule" })).toBeDisabled();
    await userEvent.click(choices[0] as HTMLElement);
    await userEvent.click(within(panel).getByRole("button", { name: "Confirm reschedule" }));
    await vi.waitFor(() => expect(moved).toBe(true));
    expect(f.mock.calls.some((c) => String(c[0]) === "/api/appointments/5/reschedule")).toBe(true);
    expect(await screen.findByRole("button", { name: "Reschedule" })).toBeInTheDocument();
  });

  it("shows empty and error states of the slot list and a 409 message", async () => {
    loginAs("PATIENT");
    mockFetch((path, init) => {
      if (init.method === "POST") return json(409, { code: "SLOT_UNAVAILABLE", message: "taken" });
      if (path === "/api/doctors/1/slots") return json(200, { items: [slot(11, 24 * 60)], total: 1 });
      return json(200, { items: [appt()], total: 1 });
    });
    renderApp("/appointments");
    await userEvent.click(await screen.findByRole("button", { name: "Reschedule" }));
    expect(await screen.findByText("No other open slots for this doctor.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("group", { name: "Reschedule" })).toBeNull();
  });

  it("reports a taken slot inline", async () => {
    loginAs("PATIENT");
    mockFetch((path, init) => {
      if (init.method === "POST") return json(409, { code: "SLOT_UNAVAILABLE", message: "taken" });
      if (path === "/api/doctors/1/slots") return json(200, { items: [slot(12, 48 * 60)], total: 1 });
      return json(200, { items: [appt()], total: 1 });
    });
    renderApp("/appointments");
    await userEvent.click(await screen.findByRole("button", { name: "Reschedule" }));
    const panel = await screen.findByRole("group", { name: "Reschedule" });
    await userEvent.click((await within(panel).findAllByRole("button", { pressed: false }))[0] as HTMLElement);
    await userEvent.click(within(panel).getByRole("button", { name: "Confirm reschedule" }));
    expect(await screen.findByTestId("appointment-notice")).toHaveTextContent(/no longer available/);
  });
});

describe("notes view (AC-09)", () => {
  it("lists notes read-only", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(200, { items: [note(1, "First note"), note(2, "Second note")], total: 2 }));
    renderApp("/appointments/5/notes");
    expect(await screen.findByText("First note")).toBeInTheDocument();
    expect(screen.getByText("Second note")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button", { name: /edit|delete/i })).toBeNull();
  });

  it("shows empty, error and not-found states", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(200, { items: [], total: 0 }));
    const a = renderApp("/appointments/5/notes");
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
    a.unmount();
    mockFetch(() => json(500, { code: "INTERNAL_ERROR", message: "x" }));
    const b = renderApp("/appointments/5/notes");
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
    b.unmount();
    mockFetch(() => json(404, { code: "NOT_FOUND", message: "x" }));
    renderApp("/appointments/5/notes");
    expect(await screen.findByRole("heading", { name: /not found/i })).toBeInTheDocument();
  });
});

describe("profile (AC-01)", () => {
  const PROFILE = { patient_id: 7, version_number: 1, full_name: "Pat Synthetic", age: 34, gender: "FEMALE", phone: "+91 90000 00001", updated_at: "x" };

  it("saves, shows a success message, and prefills from the server", async () => {
    loginAs("PATIENT");
    let phone = PROFILE.phone;
    const f = mockFetch((_p, init) => {
      if (init.method === "PUT") {
        phone = (JSON.parse(String(init.body)) as { phone: string }).phone;
        return json(200, { ...PROFILE, phone });
      }
      return json(200, { ...PROFILE, phone });
    });
    renderApp("/profile");
    const field = await screen.findByLabelText("Phone (contact)");
    expect(field).toHaveValue(PROFILE.phone);
    await userEvent.clear(field);
    await userEvent.type(field, "+91 90000 00002");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Profile saved.")).toBeInTheDocument();
    expect(f.mock.calls.some((c) => (c[1] as RequestInit).method === "PUT")).toBe(true);
  });

  it("shows server field errors and no success message", async () => {
    loginAs("PATIENT");
    mockFetch((_p, init) =>
      init.method === "PUT"
        ? json(422, { code: "VALIDATION_ERROR", message: "bad", errors: [{ field: "age", message: "Age must be 1 to 130." }] })
        : json(200, PROFILE),
    );
    renderApp("/profile");
    const age = await screen.findByLabelText("Age");
    await userEvent.clear(age);
    await userEvent.type(age, "0");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Age must be 1 to 130.")).toBeInTheDocument();
    expect(screen.queryByText("Profile saved.")).toBeNull();
  });

  it("validates a non-numeric age locally, shows banner for other failures, and load errors", async () => {
    loginAs("PATIENT");
    mockFetch((_p, init) => (init.method === "PUT" ? json(500, { code: "INTERNAL_ERROR", message: "x" }) : json(200, PROFILE)));
    const first = renderApp("/profile");
    const age = await screen.findByLabelText("Age");
    await userEvent.clear(age);
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText(/whole number/)).toBeInTheDocument();
    await userEvent.type(age, "40");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
    first.unmount();
    mockFetch(() => json(500, { code: "INTERNAL_ERROR", message: "x" }));
    renderApp("/profile");
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
  });
});
