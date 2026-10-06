import type { Appointment } from "../types/contracts";
import { api } from "./client";

export const bookAppointment = (slotId: number) =>
  api.post<Appointment>("/api/appointments", { slot_id: slotId });
