import { useState, type FormEvent } from "react";
import { patientProfilePath, updatePatientProfile } from "../../../api/admin";
import { ApiError } from "../../../api/client";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { FormField } from "../../../components/FormField";
import { LoadingState } from "../../../components/LoadingState";
import { MESSAGES } from "../../../config/routes";
import { useResource } from "../../../hooks/useResource";
import type { Gender, PatientProfile, User } from "../../../types/contracts";

type Values = { full_name: string; age: string; gender: string; phone: string };
type Errors = Partial<Record<keyof Values, string>>;

const GENDERS: { value: Gender; label: string }[] = [
  { value: "FEMALE", label: "Female" },
  { value: "MALE", label: "Male" },
  { value: "OTHER", label: "Other" },
  { value: "UNDISCLOSED", label: "Prefer not to say" },
];

function ProfileForm({ patientId, initial, onClose }: { patientId: number; initial: Values; onClose: () => void }) {
  const [v, setV] = useState<Values>(initial);
  const [errors, setErrors] = useState<Errors>({});
  const [banner, setBanner] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof Values) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBanner("");
    setSaved(false);
    setErrors({});
    const age = v.age.trim();
    if (!/^\d+$/.test(age)) {
      setErrors({ age: "Age must be a whole number from 1 to 130." });
      return;
    }
    setBusy(true);
    try {
      await updatePatientProfile(patientId, {
        full_name: v.full_name.trim(),
        age: Number(age),
        gender: v.gender as Gender,
        phone: v.phone.trim(),
      });
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422 && err.fieldErrors.length > 0) {
        const server: Errors = {};
        for (const fe of err.fieldErrors) if (fe.field in v) server[fe.field as keyof Values] = fe.message;
        setErrors(server);
        if (Object.keys(server).length === 0) setBanner(MESSAGES.generic);
      } else setBanner(err instanceof ApiError ? err.userMessage : MESSAGES.generic);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate>
      <AriaLiveRegion assertive>{banner ? <div className="msg msg-err">{banner}</div> : null}</AriaLiveRegion>
      <FormField id="pf-full_name" label="Full name" value={v.full_name} onChange={set("full_name")} error={errors.full_name} />
      <div className="grid grid-cols-2 gap-3">
        <FormField id="pf-age" label="Age" type="number" inputMode="numeric" value={v.age} onChange={set("age")} error={errors.age} />
        <FormField
          id="pf-gender"
          label="Gender"
          error={errors.gender}
          control={
            <select
              id="pf-gender"
              className="field"
              value={v.gender}
              onChange={set("gender")}
              aria-invalid={errors.gender ? true : undefined}
              aria-describedby="pf-gender-error"
            >
              <option value="">Select...</option>
              {GENDERS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          }
        />
      </div>
      <FormField id="pf-phone" label="Phone (contact)" type="tel" value={v.phone} onChange={set("phone")} error={errors.phone} />
      <AriaLiveRegion>{saved ? <div className="msg msg-ok">Profile saved.</div> : null}</AriaLiveRegion>
      <div className="flex gap-2 mt-3">
        <button type="submit" className="btn" disabled={busy}>
          Save
        </button>
        <button type="button" className="btn btn-sec" onClick={onClose}>
          Close
        </button>
      </div>
    </form>
  );
}

/** Modal for editing a patient's profile; prefilled from the current profile, falling back to row data. */
export function EditPatientProfileDialog({ patient, onClose }: { patient: User; onClose: () => void }) {
  const { state } = useResource<PatientProfile>(patientProfilePath(patient.user_id));
  let initial: Values | null = null;
  if (state.status === "success") {
    const p = state.data;
    initial = { full_name: p.full_name, age: String(p.age), gender: p.gender, phone: p.phone };
  } else if (state.status === "error") {
    initial = { full_name: patient.full_name ?? "", age: "", gender: "", phone: "" };
  }
  return (
    <div className="fixed inset-0 bg-ink/50 flex items-center justify-center p-4 z-50">
      <div role="dialog" aria-modal="true" aria-labelledby="pf-title" className="bg-card rounded-[10px] p-5 w-full max-w-[440px]">
        <h2 id="pf-title">Edit patient profile</h2>
        <p className="text-sm text-ink2">{patient.email}</p>
        {initial === null ? <LoadingState /> : <ProfileForm patientId={patient.user_id} initial={initial} onClose={onClose} />}
      </div>
    </div>
  );
}
