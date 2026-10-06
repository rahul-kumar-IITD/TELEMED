import { useState, type FormEvent } from "react";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { FormField } from "../../../components/FormField";
import {
  EMPTY_ROW,
  TemplateRows,
  type RowErrors,
  type RowField,
  type TemplateRow,
} from "../../../components/TemplateRows";
import { MESSAGES } from "../../../config/routes";
import { useOnboard } from "../../../hooks/useOnboard";
import type { FieldError, OnboardedDoctor } from "../../../types/contracts";

type Values = {
  full_name: string;
  email: string;
  initial_password: string;
  specialty: string;
  languages: string;
  fee: string;
};
type Errors = Partial<Record<keyof Values, string>>;

const EMPTY: Values = { full_name: "", email: "", initial_password: "", specialty: "", languages: "", fee: "" };
const ROW_RE = /^availability_templates\[(\d+)\]\.(\w+)$/;
const ROW_FIELDS: string[] = ["weekday", "start_time", "end_time", "slot_length_minutes"];

function splitErrors(list: FieldError[]): { top: Errors; rows: RowErrors[]; other: string[] } {
  const top: Errors = {};
  const rows: RowErrors[] = [];
  const other: string[] = [];
  for (const fe of list) {
    const m = ROW_RE.exec(fe.field);
    if (m && ROW_FIELDS.includes(m[2] ?? "")) {
      const i = Number(m[1]);
      rows[i] = { ...rows[i], [m[2] as RowField]: fe.message };
      continue;
    }
    const key = fe.field.replace(/\[\d+\]$/, "");
    if (key in EMPTY) top[key as keyof Values] = fe.message;
    else other.push(fe.message);
  }
  return { top, rows, other };
}

function Success({ doctor, onAnother }: { doctor: OnboardedDoctor; onAnother: () => void }) {
  return (
    <section className="card" data-testid="onboard-success" aria-labelledby="h-onb-ok">
      <h1 id="h-onb-ok">Doctor onboarded</h1>
      <p className="msg msg-ok">
        {doctor.full_name} can now log in and has {doctor.slots_created} bookable slots.
      </p>
      <dl className="grid grid-cols-[160px_1fr] gap-y-1">
        <dt className="font-semibold">Name</dt>
        <dd data-testid="new-name">{doctor.full_name}</dd>
        <dt className="font-semibold">Email</dt>
        <dd data-testid="new-email">{doctor.email}</dd>
        <dt className="font-semibold">Specialty</dt>
        <dd data-testid="new-specialty">{doctor.specialty}</dd>
        <dt className="font-semibold">Languages</dt>
        <dd>{doctor.languages.join(", ")}</dd>
        <dt className="font-semibold">Fee</dt>
        <dd data-testid="new-fee">{doctor.fee}</dd>
      </dl>
      <p>
        <button type="button" className="btn" onClick={onAnother}>
          Onboard another doctor
        </button>
      </p>
    </section>
  );
}

export function OnboardDoctorPage() {
  const [v, setV] = useState<Values>(EMPTY);
  const [rows, setRows] = useState<TemplateRow[]>([{ ...EMPTY_ROW }]);
  const [errors, setErrors] = useState<Errors>({});
  const [rowErrors, setRowErrors] = useState<RowErrors[]>([]);
  const [banner, setBanner] = useState("");
  const [created, setCreated] = useState<OnboardedDoctor | null>(null);
  const { submit, busy } = useOnboard();

  const set = (k: keyof Values) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBanner("");
    setErrors({});
    setRowErrors([]);
    const name = v.full_name.trim();
    const result = await submit({
      email: v.email.trim(),
      initial_password: v.initial_password,
      ...(name ? { full_name: name } : {}),
      specialty: v.specialty.trim(),
      languages: v.languages
        .split(",")
        .map((l) => l.trim())
        .filter(Boolean),
      fee: v.fee.trim(),
      availability_templates: rows.map((r) => ({
        weekday: Number(r.weekday),
        start_time: r.start_time,
        end_time: r.end_time,
        slot_length_minutes: Number(r.slot_length_minutes),
      })),
    });
    if (result.kind === "created") setCreated(result.doctor);
    else if (result.kind === "duplicate") setErrors({ email: MESSAGES.duplicateEmail });
    else if (result.kind === "invalid") {
      const s = splitErrors(result.fieldErrors);
      setErrors(s.top);
      setRowErrors(s.rows);
      const placed = Object.keys(s.top).length > 0 || s.rows.length > 0;
      setBanner(s.other.length > 0 ? s.other.join(" ") : placed ? "" : MESSAGES.generic);
    } else setBanner(result.message);
  };

  if (created) {
    return (
      <Success
        doctor={created}
        onAnother={() => {
          setCreated(null);
          setV(EMPTY);
          setRows([{ ...EMPTY_ROW }]);
        }}
      />
    );
  }

  return (
    <section aria-labelledby="h-onb">
      <h1 id="h-onb">Onboard a doctor</h1>
      <AriaLiveRegion assertive>{banner ? <div className="msg msg-err">{banner}</div> : null}</AriaLiveRegion>
      <form className="card" onSubmit={onSubmit} noValidate>
        <div className="grid grid-cols-2 gap-x-4">
          <FormField id="onb-full_name" label="Full name" value={v.full_name} onChange={set("full_name")} error={errors.full_name} />
          <FormField id="onb-email" label="Email" type="email" value={v.email} onChange={set("email")} error={errors.email} />
          <FormField
            id="onb-password"
            label="Initial password"
            type="text"
            autoComplete="off"
            value={v.initial_password}
            onChange={set("initial_password")}
            error={errors.initial_password}
          />
          <FormField id="onb-specialty" label="Specialty" value={v.specialty} onChange={set("specialty")} error={errors.specialty} />
          <FormField
            id="onb-languages"
            label="Languages (codes, comma separated)"
            value={v.languages}
            onChange={set("languages")}
            error={errors.languages}
          />
          <FormField
            id="onb-fee"
            label="Fee (decimal, 2 places)"
            inputMode="decimal"
            value={v.fee}
            onChange={set("fee")}
            error={errors.fee}
          />
        </div>
        <h2 className="mt-4">Weekly availability template</h2>
        <TemplateRows rows={rows} errors={rowErrors} onChange={setRows} />
        <p className="mt-4">
          <button className="btn" type="submit" disabled={busy}>
            Onboard doctor
          </button>
        </p>
      </form>
    </section>
  );
}
