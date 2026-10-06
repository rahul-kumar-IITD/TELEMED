import { useCallback, useState } from "react";
import { PROFILE_PATH, updateProfile } from "../api/profile";
import { ApiError } from "../api/client";
import { MESSAGES } from "../config/routes";
import type { PatientProfile, ProfileUpdate } from "../types/contracts";
import { useResource } from "./useResource";

export type SaveResult = { ok: true } | { ok: false; fieldErrors: Record<string, string>; message: string };

/** Own profile (latest version) and a save action that maps 422 field errors. */
export function useProfile() {
  const { state, reload } = useResource<PatientProfile>(PROFILE_PATH);
  const [busy, setBusy] = useState(false);
  const save = useCallback(async (body: ProfileUpdate): Promise<SaveResult> => {
    setBusy(true);
    try {
      await updateProfile(body);
      return { ok: true };
    } catch (e) {
      const fieldErrors: Record<string, string> = {};
      if (e instanceof ApiError) for (const fe of e.fieldErrors) fieldErrors[fe.field] = fe.message;
      const message = e instanceof ApiError ? e.userMessage : MESSAGES.generic;
      return { ok: false, fieldErrors, message: Object.keys(fieldErrors).length > 0 ? "" : message };
    } finally {
      setBusy(false);
    }
  }, []);
  return { state, reload, busy, save };
}
