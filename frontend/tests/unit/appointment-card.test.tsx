import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppointmentCard } from "../../src/components/AppointmentCard";
import type { Appointment } from "../../src/types/contracts";
import { appt } from "./fixtures";

function show(a: Appointment, extra: { notice?: string; onCancel?: () => void } = {}) {
  return render(
    <MemoryRouter>
      <ul>
        <AppointmentCard appointment={a} onCancel={extra.onCancel ?? vi.fn()} onReschedule={vi.fn()} notice={extra.notice} />
      </ul>
    </MemoryRouter>,
  );
}

describe("AppointmentCard (AC-04 status text and join control)", () => {
  it.each([
    ["BOOKED", true],
    ["CHECKED_IN", true],
    ["IN_PROGRESS", true],
    ["COMPLETED", false],
    ["CANCELLED", false],
    ["NO_SHOW", false],
  ])("shows the status as text and the join control only when joinable: %s", (status, joinable) => {
    show(appt({ status, allowed_actions: [] }));
    expect(screen.getByTestId("appointment-status")).toHaveTextContent(status);
    expect(screen.queryByText("Join video visit") !== null).toBe(joinable);
  });

  it("renders the join control as a disabled button when there is no join url", () => {
    show(appt({ join_url: null }));
    expect(screen.getByRole("button", { name: "Join video visit" })).toBeDisabled();
  });

  it("links to the notes of a completed appointment", () => {
    show(appt({ status: "COMPLETED", allowed_actions: [], appointment_id: 9 }));
    expect(screen.getByRole("link", { name: "View consultation notes" })).toHaveAttribute("href", "/appointments/9/notes");
  });

  it("asks for confirmation before cancelling and can back out", async () => {
    const onCancel = vi.fn();
    show(appt(), { onCancel });
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Keep appointment" }));
    expect(onCancel).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("shows an inline notice", () => {
    show(appt(), { notice: "Nothing was changed." });
    expect(screen.getByTestId("appointment-notice")).toHaveTextContent("Nothing was changed.");
  });
});
