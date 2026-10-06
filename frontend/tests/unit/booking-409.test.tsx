import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const DOCTOR = {
  doctor_id: 1,
  full_name: "Dr. Asha Rao",
  specialty: "Cardiology",
  languages: ["English", "Hindi"],
  fee: "500.00",
  earliest_slot: "2030-01-10T05:00:00Z",
};
const slot = (id: number, start: string) => ({
  slot_id: id,
  doctor_id: 1,
  start_time: start,
  end_time: start,
  status: "AVAILABLE",
});
const S1 = slot(11, "2030-01-10T05:00:00Z");
const S2 = slot(12, "2030-01-10T06:00:00Z");
const S3 = slot(13, "2030-01-11T06:00:00Z");
const APPT = {
  appointment_id: 5,
  status: "BOOKED",
  slot_id: 11,
  start_time: S1.start_time,
  end_time: S1.end_time,
  doctor: { doctor_id: 1, full_name: "Dr. Asha Rao", specialty: "Cardiology" },
  patient: { patient_id: 7, full_name: "P" },
  fee: "500.00",
  allowed_actions: [],
  join_url: null,
  change_deadline: S1.start_time,
  created_at: S1.start_time,
  updated_at: S1.start_time,
};

describe("patient search", () => {
  it("lists doctors with fee, filters and sorts, and shows empty state", async () => {
    loginAs("PATIENT");
    const f = mockFetch((path) =>
      path.includes("specialty=none") ? json(200, { items: [], total: 0 }) : json(200, { items: [DOCTOR], total: 1 }),
    );
    renderApp("/doctors");
    expect(await screen.findByTestId("doctor-fee")).toHaveTextContent("500.00");
    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "fee");
    await userEvent.type(screen.getByLabelText("Language"), "Hindi");
    await userEvent.type(screen.getByLabelText("Available from"), "2030-01-10");
    await userEvent.type(screen.getByLabelText("Available to"), "2030-01-12");
    const urls = f.mock.calls.map((c) => String(c[0]));
    expect(urls.some((u) => u.includes("sort=fee"))).toBe(true);
    expect(urls.some((u) => u.includes("language=Hindi"))).toBe(true);
    expect(urls.some((u) => u.includes("available_from="))).toBe(true);
    await userEvent.type(screen.getByLabelText("Specialty"), "none");
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
  });

  it("shows an error with retry", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(500, { code: "INTERNAL_ERROR", message: "x" }));
    renderApp("/doctors");
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
  });
});

describe("doctor detail and booking", () => {
  it("groups slots by day with local time + zone, then confirms a booking", async () => {
    loginAs("PATIENT");
    mockFetch((path, init) => {
      if (init.method === "POST") return json(201, APPT);
      if (path.endsWith("/slots")) return json(200, { items: [S3, S1, S2], total: 3 });
      return json(200, DOCTOR);
    });
    renderApp("/doctors/1");
    const days = await screen.findAllByTestId("slot-day");
    expect(days).toHaveLength(2);
    const first = within(days[0] as HTMLElement).getAllByRole("button");
    expect(first).toHaveLength(2);
    expect(first[0]?.textContent).toMatch(/^\d{2}:\d{2} \S+/);
    const next = screen.getByRole("button", { name: "Continue to confirm" });
    expect(next).toBeDisabled();
    await userEvent.click(first[0] as HTMLElement);
    await userEvent.click(next);
    expect(await screen.findByTestId("summary-fee")).toHaveTextContent("500.00");
    expect(screen.getByText(/Dr. Asha Rao/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Confirm booking" }));
    expect(await screen.findByTestId("confirmation")).toHaveTextContent("Dr. Asha Rao");
    expect(screen.getByTestId("confirm-fee")).toHaveTextContent("500.00");
  });

  it("shows empty slots and a not-available slot on confirm", async () => {
    loginAs("PATIENT");
    mockFetch((path) => (path.endsWith("/slots") ? json(200, { items: [], total: 0 }) : json(200, DOCTOR)));
    const first = renderApp("/doctors/1");
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
    first.unmount();
    renderApp("/doctors/1/book/99");
    expect(await screen.findByText("This slot is not available.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Choose another slot" })).toBeInTheDocument();
  });

  it("shows errors on detail and confirm pages", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(500, { code: "INTERNAL_ERROR", message: "x" }));
    const first = renderApp("/doctors/1");
    expect((await screen.findAllByTestId("error-state")).length).toBe(2);
    first.unmount();
    renderApp("/doctors/1/book/11");
    expect((await screen.findAllByTestId("error-state")).length).toBe(2);
  });

  it("shows a generic inline error when booking fails otherwise", async () => {
    loginAs("PATIENT");
    mockFetch((path, init) => {
      if (init.method === "POST") return json(500, { code: "INTERNAL_ERROR", message: "x" });
      return path.endsWith("/slots") ? json(200, { items: [S1], total: 1 }) : json(200, DOCTOR);
    });
    renderApp("/doctors/1/book/11");
    await userEvent.click(await screen.findByRole("button", { name: "Confirm booking" }));
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });

  it("on 409 refetches slots and shows an inline message without alert/console.log", async () => {
    loginAs("PATIENT");
    const alertSpy = vi.fn();
    vi.stubGlobal("alert", alertSpy);
    const logSpy = vi.spyOn(console, "log");
    let taken = false;
    const f = mockFetch((path, init) => {
      if (init.method === "POST") {
        taken = true;
        return json(409, { code: "SLOT_UNAVAILABLE", message: "taken" });
      }
      if (path.endsWith("/slots")) return json(200, { items: taken ? [S2] : [S1, S2], total: 2 });
      return json(200, DOCTOR);
    });
    renderApp("/doctors/1/book/11");
    await userEvent.click(await screen.findByRole("button", { name: "Confirm booking" }));
    expect(await screen.findByText(/no longer available/i)).toBeInTheDocument();
    expect(await screen.findByText("This slot is not available.")).toBeInTheDocument();
    const slotCalls = f.mock.calls.filter((c) => String(c[0]).endsWith("/slots"));
    expect(slotCalls.length).toBeGreaterThanOrEqual(2);
    expect(alertSpy).not.toHaveBeenCalled();
    expect(logSpy).not.toHaveBeenCalled();
  });
});
