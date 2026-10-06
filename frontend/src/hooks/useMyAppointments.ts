import { cancelAppointment, MINE_PATH, rescheduleAppointment } from "../api/appointments";
import type { ApiError } from "../api/client";
import { MESSAGES } from "../config/routes";
import type { Appointment, ListResponse } from "../types/contracts";
import { useResource } from "./useResource";
import { useRowActions } from "./useRowActions";

const conflictMessage = (e: ApiError): string => {
  if (e.code === "CHANGE_WINDOW_CLOSED") return MESSAGES.windowClosed;
  if (e.code === "SLOT_UNAVAILABLE") return MESSAGES.changeSlotTaken;
  return MESSAGES.appointmentChanged;
};

/** The patient's appointments with cancel/reschedule; the server stays authoritative on 409. */
export function useMyAppointments() {
  const { state, reload } = useResource<ListResponse<Appointment>>(MINE_PATH, (d) => d.items.length === 0);
  const { notices, busyId, run } = useRowActions(reload, conflictMessage);
  const cancel = (id: number) => run(id, () => cancelAppointment(id));
  const reschedule = (id: number, newSlotId: number) => run(id, () => rescheduleAppointment(id, newSlotId));
  return { state, reload, notices, busyId, cancel, reschedule };
}
