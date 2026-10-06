import { useState, type FormEvent } from "react";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { ErrorState } from "../../../components/ErrorState";
import { FormField } from "../../../components/FormField";
import { LoadingState } from "../../../components/LoadingState";
import { useProfile } from "../../../hooks/useProfile";
import type { Gender, PatientProfile } from "../../../types/contracts";

type Values = { full_name: string; age: string; gender: string; phone: string };
type Errors = Partial<Record<keyof Values, string>>;

const GENDERS: { value: Gender; label: string }[] = [
  { value: "FEMALE", label: "Female" },
  { value: "MALE", label: "Male" },
  { value: "OTHER", label: "Other" },
  { value: "UNDISCLOSED", label: "Prefer not to say" },
];

const toValues = (p: PatientProfile): Values => ({
  full_name: p.full_name,
  age: String(p.age),
  gender: p.gender,
  phone: p.phone,
});

function ProfileForm({ initial, busy, save }: { initial: Values } & Pick<ReturnType<typeof useProfile>, "busy" | "save">) {
  const [v, setV] = useState<Values>(initial);
  const [errors, setErrors] = useState<Errors>({});
  const [banner, setBanner] = useState("");
  const [saved, setSaved] = useState(false);
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
    const result = await save({
      full_name: v.full_name.trim(),
      age: Number(age),
      gender: v.gender as Gender,
      phone: v.phone.trim(),
    });
    if (result.ok) {
      setSaved(true);
      return;
    }
    const server: Errors = {};
    for (const [field, message] of Object.entries(result.fieldErrors)) if (field in v) server[field as keyof Values] = message;
    setErrors(server);
    setBanner(Object.keys(server).length === 0 ? result.message || "Something went wrong. Please try again." : "");
  };

  return (
    <form onSubmit={(e) => void onSubmit(e)} noValidate className="max-w-[480px]">
      <AriaLiveRegion assertive>{banner ? <div className="msg msg-err">{banner}</div> : null}</AriaLiveRegion>
      <FormField id="pf-full_name" label="Full name" value={v.full_name} onChange={set("full_name")} error={errors.full_name} />
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
            {GENDERS.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
        }
      />
      <FormField id="pf-phone" label="Phone (contact)" type="tel" value={v.phone} onChange={set("phone")} error={errors.phone} />
      <AriaLiveRegion>{saved ? <div className="msg msg-ok">Profile saved.</div> : null}</AriaLiveRegion>
      <button type="submit" className="btn mt-3" disabled={busy}>
        Save profile
      </button>
    </form>
  );
}

export function ProfilePage() {
  const { state, reload, busy, save } = useProfile();
  return (
    <section aria-labelledby="h-profile">
      <h1 id="h-profile">My profile</h1>
      {(state.status === "loading" || state.status === "empty") && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && <ProfileForm initial={toValues(state.data)} busy={busy} save={save} />}
    </section>
  );
}
