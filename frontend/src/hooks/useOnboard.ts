import { useCallback, useState } from "react";
import { onboardDoctor } from "../api/admin";
import { ApiError } from "../api/client";
import { MESSAGES } from "../config/routes";
import type { FieldError, OnboardDoctorRequest, OnboardedDoctor } from "../types/contracts";

export type OnboardResult =
  | { kind: "created"; doctor: OnboardedDoctor }
  | { kind: "invalid"; fieldErrors: FieldError[] }
  | { kind: "duplicate" }
  | { kind: "error"; message: string };

export function useOnboard() {
  const [busy, setBusy] = useState(false);
  const submit = useCallback(async (req: OnboardDoctorRequest): Promise<OnboardResult> => {
    setBusy(true);
    try {
      return { kind: "created", doctor: await onboardDoctor(req) };
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) return { kind: "invalid", fieldErrors: e.fieldErrors };
      if (e instanceof ApiError && e.status === 409) return { kind: "duplicate" };
      return { kind: "error", message: e instanceof ApiError ? e.userMessage : MESSAGES.generic };
    } finally {
      setBusy(false);
    }
  }, []);
  return { submit, busy };
}
