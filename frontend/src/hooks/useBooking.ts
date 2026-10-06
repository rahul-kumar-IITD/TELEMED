import { useCallback, useState } from "react";
import { bookAppointment } from "../api/appointments";
import { ApiError } from "../api/client";
import type { Appointment } from "../types/contracts";

export type BookingResult =
  | { kind: "booked"; appointment: Appointment }
  | { kind: "conflict" }
  | { kind: "error"; message: string };

/** Books a slot; maps the 409 slot-taken response to a distinct outcome. */
export function useBooking() {
  const [busy, setBusy] = useState(false);
  const book = useCallback(async (slotId: number): Promise<BookingResult> => {
    setBusy(true);
    try {
      return { kind: "booked", appointment: await bookAppointment(slotId) };
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) return { kind: "conflict" };
      return { kind: "error", message: e instanceof ApiError ? e.userMessage : "Something went wrong. Please try again." };
    } finally {
      setBusy(false);
    }
  }, []);
  return { book, busy };
}
