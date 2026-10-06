import type { Appointment, StatusTarget, Slot } from "../types/contracts";
import { api } from "./client";
import { appointmentPath } from "./appointments";

export const queuePath = (date: string) =>
  date ? `/api/doctors/me/queue?date=${encodeURIComponent(date)}` : "/api/doctors/me/queue";
export const MY_SLOTS_PATH = "/api/doctors/me/slots";
export const CONFIG_PATH = "/api/config";

export const changeStatus = (appointmentId: number, status: StatusTarget) =>
  api.post<Appointment>(`${appointmentPath(appointmentId)}/status`, { status });
export const blockSlot = (slotId: number) => api.put<Slot>(`${MY_SLOTS_PATH}/${slotId}/block`);
export const unblockSlot = (slotId: number) => api.put<Slot>(`${MY_SLOTS_PATH}/${slotId}/unblock`);
