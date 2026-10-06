import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppointmentCard } from "../../src/components/AppointmentCard";
import type { Appointment } from "../../src/types/contracts";
import { appt, inMinutes } from "./fixtures";

function show(a: Appointment) {
  return render(
    <MemoryRouter>
      <ul>
        <AppointmentCard appointment={a} onCancel={vi.fn()} onReschedule={vi.fn()} />
      </ul>
    </MemoryRouter>,
  );
}

describe("change window (AC-06, AC-07)", () => {
  it("disables Cancel and Reschedule with a 60 minute explanation inside the window", () => {
    show(appt({ start_time: inMinutes(59), allowed_actions: [] }));
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reschedule" })).toBeDisabled();
    expect(screen.getByTestId("window-explanation")).toHaveTextContent(/60 minutes/);
  });

  it("enables both outside the window", () => {
    show(appt({ start_time: inMinutes(90) }));
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reschedule" })).toBeEnabled();
    expect(screen.queryByTestId("window-explanation")).toBeNull();
  });

  it("disables when the change deadline has passed even if actions are still listed", () => {
    show(appt({ allowed_actions: ["CANCEL", "RESCHEDULE"], change_deadline: inMinutes(-1) }));
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });

  it("offers no change buttons for non-BOOKED appointments", () => {
    show(appt({ status: "CHECKED_IN", allowed_actions: [] }));
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
    expect(screen.queryByTestId("window-explanation")).toBeNull();
  });
});
