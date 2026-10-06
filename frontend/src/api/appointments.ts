import type { Appointment } from "../types/contracts";
import { api } from "./client";

export const bookAppointment = (slotId: number) =>
  api.post<Appointment>("/api/appointments", { slot_id: slotId });

export const MINE_PATH = "/api/appointments/mine";
export const appointmentPath = (id: number | string) => `/api/appointments/${encodeURIComponent(String(id))}`;
export const cancelAppointment = (id: number) => api.post<Appointment>(`${appointmentPath(id)}/cancel`, undefined);
export const rescheduleAppointment = (id: number, newSlotId: number) =>
  api.post<Appointment>(`${appointmentPath(id)}/reschedule`, { new_slot_id: newSlotId });
