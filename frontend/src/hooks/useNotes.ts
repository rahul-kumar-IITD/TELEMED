import { useCallback } from "react";
import { addNote, notesPath } from "../api/notes";
import { ApiError } from "../api/client";
import { MESSAGES } from "../config/routes";
import type { ConsultationNote, ListResponse } from "../types/contracts";
import { useResource } from "./useResource";

/** Notes of one appointment (read-only list) plus append for the owning doctor. */
export function useNotes(appointmentId: string) {
  const { state, reload } = useResource<ListResponse<ConsultationNote>>(
    notesPath(appointmentId),
    (d) => d.items.length === 0,
  );
  /** Resolves to an error message, or null on success. */
  const add = useCallback(
    async (text: string): Promise<string | null> => {
      try {
        await addNote(appointmentId, text);
        reload();
        return null;
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          reload();
          return "Notes can only be added once the appointment is COMPLETED.";
        }
        return e instanceof ApiError ? e.userMessage : MESSAGES.generic;
      }
    },
    [appointmentId, reload],
  );
  return { state, reload, add };
}
