import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { QueueRow } from "../../src/components/QueueRow";
import type { Appointment } from "../../src/types/contracts";
import { appt, inMinutes } from "./fixtures";

function show(a: Appointment, onAction = vi.fn(), notice?: string) {
  render(
    <MemoryRouter>
      <ul>
        <QueueRow appointment={a} timezone="Asia/Kolkata" onAction={onAction} notice={notice} />
      </ul>
    </MemoryRouter>,
  );
  return onAction;
}

describe("queue row actions (AC-08)", () => {
  it("renders exactly the buttons listed in allowed_actions", async () => {
    const onAction = show(appt({ allowed_actions: ["CHECKED_IN"] }));
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(["Check in", "Mark NO_SHOW"]);
    await userEvent.click(screen.getByRole("button", { name: "Check in" }));
    expect(onAction).toHaveBeenCalledWith("CHECKED_IN");
  });

  it("disables Mark NO_SHOW with an explanation before the start time", () => {
    show(appt({ start_time: inMinutes(120), allowed_actions: ["CHECKED_IN", "CANCEL"] }));
    expect(screen.getByRole("button", { name: "Mark NO_SHOW" })).toBeDisabled();
    expect(screen.getByText(/available once the start time has passed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel appointment" })).toBeEnabled();
  });

  it("enables Mark NO_SHOW when the server lists it", async () => {
    const onAction = show(appt({ status: "CHECKED_IN", allowed_actions: ["IN_PROGRESS", "NO_SHOW"] }));
    expect(screen.queryByText(/available once the start time/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Mark NO_SHOW" }));
    expect(onAction).toHaveBeenCalledWith("NO_SHOW");
  });

  it("maps every status action and ignores unknown ones", () => {
    show(appt({ status: "IN_PROGRESS", allowed_actions: ["COMPLETED", "MYSTERY"] }));
    expect(screen.getByRole("button", { name: "Mark completed" })).toBeInTheDocument();
    expect(screen.queryByText("MYSTERY")).toBeNull();
    expect(screen.queryByRole("button", { name: "Mark NO_SHOW" })).toBeNull();
  });

  it("shows terminal rows without buttons and displays inline notices", () => {
    show(appt({ status: "COMPLETED", allowed_actions: [] }), vi.fn(), "Refreshed.");
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByTestId("queue-notice")).toHaveTextContent("Refreshed.");
    expect(screen.getByTestId("queue-time").textContent).toMatch(/^\d{2}:\d{2} Asia\/Kolkata$/);
  });
});
