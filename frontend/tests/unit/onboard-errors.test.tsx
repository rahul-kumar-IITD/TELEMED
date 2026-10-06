import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const CREATED = {
  doctor_id: 20,
  user_id: 20,
  email: "farah@example.test",
  full_name: "Dr. Farah",
  specialty: "Neurology",
  languages: ["en", "hi"],
  fee: "900.50",
  availability_templates: [],
  slots_created: 12,
};

async function fill() {
  await userEvent.type(screen.getByLabelText("Full name"), "Dr. Farah");
  await userEvent.type(screen.getByLabelText("Email"), "farah@example.test");
  await userEvent.type(screen.getByLabelText("Initial password"), "Welcome-2026!");
  await userEvent.type(screen.getByLabelText("Specialty"), "Neurology");
  await userEvent.type(screen.getByLabelText(/Languages/), "en, hi");
  await userEvent.type(screen.getByLabelText(/Fee/), "900.50");
}

describe("onboard doctor", () => {
  it("adds and removes template rows and posts the form, then shows the new doctor", async () => {
    loginAs("ADMIN");
    const f = mockFetch(() => json(201, CREATED));
    renderApp("/admin/doctors/new");
    expect(screen.getAllByTestId("template-row")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Remove row 1" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "+ Add template row" }));
    expect(screen.getAllByTestId("template-row")).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Remove row 2" }));
    expect(screen.getAllByTestId("template-row")).toHaveLength(1);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Onboard doctor" }));
    expect(await screen.findByTestId("onboard-success")).toBeInTheDocument();
    expect(screen.getByTestId("new-name")).toHaveTextContent("Dr. Farah");
    expect(screen.getByTestId("new-email")).toHaveTextContent("farah@example.test");
    expect(screen.getByTestId("new-specialty")).toHaveTextContent("Neurology");
    expect(screen.getByTestId("new-fee")).toHaveTextContent("900.50");
    const call = f.mock.calls[0];
    expect(String(call?.[0])).toBe("/api/admin/doctors");
    const body = JSON.parse(String((call?.[1] as RequestInit).body)) as Record<string, unknown>;
    expect(body.fee).toBe("900.50");
    expect(body.languages).toEqual(["en", "hi"]);
    expect(body.availability_templates).toEqual([
      { weekday: 0, start_time: "09:00", end_time: "12:00", slot_length_minutes: 30 },
    ]);
  });

  it("shows 422 template errors next to the matching row field and keeps all values", async () => {
    loginAs("ADMIN");
    const alertSpy = vi.fn();
    vi.stubGlobal("alert", alertSpy);
    mockFetch(() =>
      json(422, {
        code: "VALIDATION_ERROR",
        message: "x",
        errors: [
          { field: "availability_templates[1].slot_length_minutes", message: "Slot length must be 5 to 120." },
          { field: "fee", message: "Fee is invalid." },
        ],
      }),
    );
    renderApp("/admin/doctors/new");
    await userEvent.click(screen.getByRole("button", { name: "+ Add template row" }));
    await fill();
    const len2 = screen.getByLabelText("Slot length, minutes (row 2)");
    await userEvent.clear(len2);
    await userEvent.type(len2, "7");
    await userEvent.click(screen.getByRole("button", { name: "Onboard doctor" }));
    const rows = await screen.findAllByTestId("template-row");
    expect(within(rows[1] as HTMLElement).getByText("Slot length must be 5 to 120.")).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).queryByText("Slot length must be 5 to 120.")).toBeNull();
    expect(screen.getByText("Fee is invalid.")).toBeInTheDocument();
    expect(screen.getByLabelText("Slot length, minutes (row 2)")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Slot length, minutes (row 2)")).toHaveValue(7);
    expect(screen.getByLabelText("Specialty")).toHaveValue("Neurology");
    expect(screen.getByLabelText("Email")).toHaveValue("farah@example.test");
    expect(screen.getByLabelText(/Fee/)).toHaveValue("900.50");
    expect(screen.getAllByTestId("template-row")).toHaveLength(2);
    expect(screen.queryByTestId("onboard-success")).toBeNull();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it("shows a duplicate email error on 409", async () => {
    loginAs("ADMIN");
    mockFetch(() => json(409, { code: "EMAIL_ALREADY_EXISTS", message: "dup" }));
    renderApp("/admin/doctors/new");
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Onboard doctor" }));
    expect(await screen.findByText(/already exists/)).toBeInTheDocument();
    expect(screen.getByLabelText("Specialty")).toHaveValue("Neurology");
  });
});
