import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../../../api/auth";
import { ApiError } from "../../../api/client";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { FormField } from "../../../components/FormField";
import { LoadingState } from "../../../components/LoadingState";
import { MESSAGES, PATHS } from "../../../config/routes";
import type { Gender } from "../../../types/contracts";

type Values = { full_name: string; age: string; gender: string; phone: string; email: string; password: string };
type Errors = Partial<Record<keyof Values, string>>;

const GENDERS: { value: Gender; label: string }[] = [
  { value: "FEMALE", label: "Female" },
  { value: "MALE", label: "Male" },
  { value: "OTHER", label: "Other" },
  { value: "UNDISCLOSED", label: "Prefer not to say" },
];

function validate(v: Values): Errors {
  const e: Errors = {};
  const name = v.full_name.trim();
  if (!name || name.length > 200) e.full_name = "Full name is required (1 to 200 characters).";
  const age = Number(v.age.trim());
  if (!/^\d+$/.test(v.age.trim()) || age < 1 || age > 130) e.age = "Age must be a whole number from 1 to 130.";
  if (!GENDERS.some((g) => g.value === v.gender)) e.gender = "Select a gender.";
  const phone = v.phone.trim();
  if (!phone || phone.length > 32) e.phone = "Phone number is required (up to 32 characters).";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email.trim())) e.email = "Enter a valid email address.";
  if (v.password.length < 8 || v.password.length > 128) e.password = "Password must be 8 to 128 characters.";
  return e;
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [v, setV] = useState<Values>({ full_name: "", age: "", gender: "", phone: "", email: "", password: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [banner, setBanner] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k: keyof Values) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBanner("");
    const found = validate(v);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setBusy(true);
    try {
      await register({
        email: v.email.trim(),
        password: v.password,
        full_name: v.full_name.trim(),
        age: Number(v.age.trim()),
        gender: v.gender as Gender,
        phone: v.phone.trim(),
      });
      navigate(PATHS.login, { replace: true, state: { notice: "Account created. Please log in." } });
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.status === 409) {
        setErrors({ email: MESSAGES.duplicateEmail });
      } else if (err instanceof ApiError && err.status === 422 && err.fieldErrors.length > 0) {
        const server: Errors = {};
        for (const fe of err.fieldErrors) {
          if (fe.field in v) server[fe.field as keyof Values] = fe.message;
        }
        setErrors(server);
        if (Object.keys(server).length === 0) setBanner(MESSAGES.generic);
      } else {
        setBanner(err instanceof ApiError ? err.userMessage : MESSAGES.generic);
      }
    }
  };

  return (
    <section className="card max-w-[420px] mx-auto mt-6" aria-labelledby="h-reg">
      <h1 id="h-reg">Create account</h1>
      <p className="text-sm text-ink2">Patients only. Doctors are onboarded by an admin.</p>
      <AriaLiveRegion assertive>{banner ? <div className="msg msg-err">{banner}</div> : null}</AriaLiveRegion>
      <form onSubmit={onSubmit} noValidate>
        <FormField id="reg-full_name" label="Full name" autoComplete="name" value={v.full_name}
          onChange={set("full_name")} error={errors.full_name} />
        <div className="grid grid-cols-2 gap-3">
          <FormField id="reg-age" label="Age" type="number" inputMode="numeric" min={1} max={130} step={1}
            value={v.age} onChange={set("age")} error={errors.age} />
          <FormField
            id="reg-gender"
            label="Gender"
            error={errors.gender}
            control={
              <select id="reg-gender" className="field" value={v.gender} onChange={set("gender")}
                aria-invalid={errors.gender ? true : undefined} aria-describedby="reg-gender-error">
                <option value="">Select...</option>
                {GENDERS.map((g) => (
                  <option key={g.value} value={g.value}>{g.label}</option>
                ))}
              </select>
            }
          />
        </div>
        <FormField id="reg-phone" label="Phone (contact)" type="tel" autoComplete="tel" value={v.phone}
          onChange={set("phone")} error={errors.phone} />
        <FormField id="reg-email" label="Email (your login)" type="email" autoComplete="email" value={v.email}
          onChange={set("email")} error={errors.email} />
        <FormField id="reg-password" label="Password (8 to 128 characters)" type="password"
          autoComplete="new-password" value={v.password} onChange={set("password")} error={errors.password} />
        <p className="mt-3.5">
          <button className="btn w-full" type="submit" disabled={busy}>Register</button>
        </p>
      </form>
      {busy ? <LoadingState label="Creating account..." /> : null}
      <p className="text-sm text-ink2">
        Already registered? <Link to={PATHS.login}>Log in</Link>
      </p>
    </section>
  );
}
