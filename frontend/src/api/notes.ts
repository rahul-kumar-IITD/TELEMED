import type { ConsultationNote } from "../types/contracts";
import { api } from "./client";
import { appointmentPath } from "./appointments";

export const notesPath = (appointmentId: number | string) => `${appointmentPath(appointmentId)}/notes`;
export const addNote = (appointmentId: number | string, text: string) =>
  api.post<ConsultationNote>(notesPath(appointmentId), { text });
