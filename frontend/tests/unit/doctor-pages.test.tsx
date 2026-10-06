import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { appt, inMinutes } from "./fixtures";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const queue = (items: unknown[], timezone = "Asia/Kolkata") => ({ date: "2030-01-10", timezone, items, total: items.length });
const note = (id: number, text: string) => ({ note_id: id, appointment_id: 5, author_id: 1, text, created_at: "2030-01-10T05:00:00Z" });
const SLOT = (id: number, status: string, minutes: number) => ({
  slot_id: id,
  doctor_id: 1,
  start_time: inMinutes(minutes),
  end_time: inMinutes(minutes + 30),
  status,
});
const DOC_ROW = appt({ allowed_actions: ["CHECKED_IN"], start_time: inMinutes(120) });

describe("doctor queue (AC-08)", () => {
  it("lists rows with the server timezone label and a date picker", async () => {
    loginAs("DOCTOR");
    const f = mockFetch(() => json(200, queue([DOC_ROW])));
    renderApp("/queue");
    expect(await screen.findByTestId("queue-time")).toHaveTextContent(/Asia\/Kolkata$/);
    expect(screen.getByLabelText("Date")).toHaveValue("2030-01-10");
    fireEvent.change(screen.getByLabelText("Date"), { target: { value: "2030-01-11" } });
    expect(f.mock.calls.some((c) => String(c[0]).includes("date=2030-01-11"))).toBe(true);
  });

  it("derives the label from the response timezone, not a constant", async () => {
    loginAs("DOCTOR");
    mockFetch(() => json(200, queue([DOC_ROW], "UTC")));
    renderApp("/queue");
    expect(await screen.findByTestId("queue-time")).toHaveTextContent(/ UTC$/);
  });

  it("updates the row after a status action", async () => {
    loginAs("DOCTOR");
    let done = false;
    const f = mockFetch((_p, init) => {
      if (init.method === "POST") {
        done = true;
        return json(200, appt({ status: "CHECKED_IN" }));
      }
      return json(200, queue([done ? appt({ status: "CHECKED_IN", allowed_actions: ["IN_PROGRESS"], start_time: inMinutes(120) }) : DOC_ROW]));
    });
    renderApp("/queue");
    await userEvent.click(await screen.findByRole("button", { name: "Check in" }));
    expect(await screen.findByText("CHECKED_IN")).toBeInTheDocument();
    expect(JSON.parse(String(f.mock.calls.find((c) => (c[1] as RequestInit).method === "POST")?.[1]?.body))).toEqual({ status: "CHECKED_IN" });
  });

  it("shows an inline message on 409 and refetches the queue", async () => {
    loginAs("DOCTOR");
    const f = mockFetch((_p, init) =>
      init.method === "POST" ? json(409, { code: "INVALID_APPOINTMENT_STATE", message: "no" }) : json(200, queue([DOC_ROW])),
    );
    renderApp("/queue");
    await userEvent.click(await screen.findByRole("button", { name: "Check in" }));
    expect(await screen.findByTestId("queue-notice")).toHaveTextContent(/refreshed/);
    const gets = f.mock.calls.filter((c) => (c[1] as RequestInit).method === "GET" && String(c[0]).startsWith("/api/doctors/me/queue"));
    expect(gets.length).toBeGreaterThanOrEqual(2);
  });

  it("shows a generic inline message for other failures, and empty/error states", async () => {
    loginAs("DOCTOR");
    mockFetch((_p, init) => (init.method === "POST" ? json(500, { code: "X", message: "x" }) : json(200, queue([DOC_ROW]))));
    const first = renderApp("/queue");
    await userEvent.click(await screen.findByRole("button", { name: "Check in" }));
    expect(await screen.findByTestId("queue-notice")).toHaveTextContent(/Something went wrong/);
    first.unmount();
    mockFetch(() => json(200, queue([])));
    renderApp("/queue");
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
  });
});

describe("slot calendar (AC-08 supporting: block/unblock)", () => {
  it("blocks an AVAILABLE slot, unblocks a BLOCKED one, and disables BOOKED", async () => {
    loginAs("DOCTOR");
    const slots = [SLOT(1, "AVAILABLE", 600), SLOT(2, "BLOCKED", 660), SLOT(3, "BOOKED", 720)];
    const f = mockFetch((path, init) => {
      if (path === "/api/config") return json(200, { provider_timezone: "Asia/Kolkata", slot_window_days: 14, change_window_minutes: 60 });
      if (init.method === "PUT") return json(200, slots[0]);
      return json(200, { items: slots, total: 3 });
    });
    renderApp("/slots");
    const rows = await screen.findAllByTestId("slot-row");
    expect(within(rows[0] as HTMLElement).getByRole("button", { name: "Block" })).toBeEnabled();
    expect(within(rows[1] as HTMLElement).getByRole("button", { name: "Unblock" })).toBeEnabled();
    expect(within(rows[2] as HTMLElement).getByRole("button", { name: "Block" })).toBeDisabled();
    await userEvent.click(within(rows[0] as HTMLElement).getByRole("button", { name: "Block" }));
    await vi.waitFor(() => expect(f.mock.calls.some((c) => String(c[0]) === "/api/doctors/me/slots/1/block")).toBe(true));
    await userEvent.click(within((await screen.findAllByTestId("slot-row"))[1] as HTMLElement).getByRole("button", { name: "Unblock" }));
    await vi.waitFor(() => expect(f.mock.calls.some((c) => String(c[0]) === "/api/doctors/me/slots/2/unblock")).toBe(true));
  });

  it("shows an inline 409 message, and empty/error states", async () => {
    loginAs("DOCTOR");
    mockFetch((path, init) => {
      if (path === "/api/config") return json(200, { provider_timezone: "UTC", slot_window_days: 14, change_window_minutes: 60 });
      if (init.method === "PUT") return json(409, { code: "INVALID_SLOT_STATE", message: "no" });
      return json(200, { items: [SLOT(1, "AVAILABLE", 600)], total: 1 });
    });
    const a = renderApp("/slots");
    await userEvent.click(await screen.findByRole("button", { name: "Block" }));
    expect(await screen.findByText(/calendar has been refreshed/)).toBeInTheDocument();
    a.unmount();
    mockFetch((path) => (path === "/api/config" ? json(200, { provider_timezone: "UTC", slot_window_days: 14, change_window_minutes: 60 }) : json(200, { items: [], total: 0 })));
    const b = renderApp("/slots");
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
    b.unmount();
    mockFetch(() => json(500, { code: "X", message: "x" }));
    renderApp("/slots");
    expect((await screen.findAllByTestId("error-state")).length).toBeGreaterThan(0);
  });
});

describe("appointment detail (AC-09)", () => {
  const CONFIG = { provider_timezone: "Asia/Kolkata", slot_window_days: 14, change_window_minutes: 60 };

  it("shows no note form for a BOOKED appointment", async () => {
    loginAs("DOCTOR");
    mockFetch((path) => {
      if (path === "/api/config") return json(200, CONFIG);
      if (path.endsWith("/notes")) return json(200, { items: [], total: 0 });
      return json(200, appt());
    });
    renderApp("/queue/5");
    expect(await screen.findByTestId("detail-status")).toHaveTextContent("BOOKED");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(await screen.findByText("No notes yet.")).toBeInTheDocument();
  });

  it("adds a note on a COMPLETED appointment and lists it without edit or delete", async () => {
    loginAs("DOCTOR");
    const notes = [note(1, "Existing note")];
    mockFetch((path, init) => {
      if (path === "/api/config") return json(200, CONFIG);
      if (path.endsWith("/notes") && init.method === "POST") {
        notes.push(note(2, "Fresh note"));
        return json(201, notes[1]);
      }
      if (path.endsWith("/notes")) return json(200, { items: [...notes], total: notes.length });
      return json(200, appt({ status: "COMPLETED", allowed_actions: [] }));
    });
    renderApp("/queue/5");
    await userEvent.type(await screen.findByLabelText("Consultation note"), "Fresh note");
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findAllByTestId("note")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /edit|delete/i })).toBeNull();
    expect(screen.getByLabelText("Consultation note")).toHaveValue("");
  });

  it("validates empty text and surfaces 409 and generic failures inline", async () => {
    loginAs("DOCTOR");
    let status = 409;
    mockFetch((path, init) => {
      if (path === "/api/config") return json(200, CONFIG);
      if (path.endsWith("/notes") && init.method === "POST") return json(status, { code: "INVALID_APPOINTMENT_STATE", message: "x" });
      if (path.endsWith("/notes")) return json(200, { items: [], total: 0 });
      return json(200, appt({ status: "COMPLETED", allowed_actions: [] }));
    });
    renderApp("/queue/5");
    await userEvent.click(await screen.findByRole("button", { name: "Add note" }));
    expect(await screen.findByText("Note text is required.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Consultation note"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText(/only be added once/)).toBeInTheDocument();
    status = 500;
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });

  it("shows not-found and load errors", async () => {
    loginAs("DOCTOR");
    mockFetch((path) => (path === "/api/config" ? json(200, CONFIG) : json(404, { code: "NOT_FOUND", message: "x" })));
    const a = renderApp("/queue/5");
    expect(await screen.findByRole("heading", { name: /not found/i })).toBeInTheDocument();
    a.unmount();
    mockFetch(() => json(500, { code: "X", message: "x" }));
    renderApp("/queue/5");
    expect((await screen.findAllByTestId("error-state")).length).toBeGreaterThan(0);
  });
});
