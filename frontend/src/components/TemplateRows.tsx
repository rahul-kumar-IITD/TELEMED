import type { ReactElement } from "react";
import { AriaLiveRegion } from "./AriaLiveRegion";

export interface TemplateRow {
  weekday: string;
  start_time: string;
  end_time: string;
  slot_length_minutes: string;
}
export type RowField = keyof TemplateRow;
export type RowErrors = Partial<Record<RowField, string>>;

export const EMPTY_ROW: TemplateRow = { weekday: "0", start_time: "09:00", end_time: "12:00", slot_length_minutes: "30" };
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

interface Props {
  rows: TemplateRow[];
  errors: RowErrors[];
  onChange: (rows: TemplateRow[]) => void;
}

/** Editable availability template rows; per-field server errors render next to the field. */
export function TemplateRows({ rows, errors, onChange }: Props) {
  const update = (i: number, k: RowField, value: string) =>
    onChange(rows.map((r, idx) => (idx === i ? { ...r, [k]: value } : r)));
  const field = (
    i: number,
    k: RowField,
    label: string,
    input: (id: string, describedBy: string, invalid: boolean) => ReactElement,
  ) => {
    const id = `tpl-${i}-${k}`;
    const err = errors[i]?.[k];
    return (
      <div>
        <label htmlFor={id} className="block font-semibold text-[.9rem] mb-1">
          {label}
        </label>
        {input(id, `${id}-error`, Boolean(err))}
        <AriaLiveRegion id={`${id}-error`} assertive className="text-err text-[.85rem] mt-1">
          {err}
        </AriaLiveRegion>
      </div>
    );
  };
  return (
    <div>
      {rows.map((r, i) => (
        <div
          key={i}
          data-testid="template-row"
          className="grid grid-cols-[1.2fr_1fr_1fr_1fr_auto] gap-2 items-start border border-line rounded-lg p-2.5 mb-2 bg-white"
        >
          {field(i, "weekday", `Weekday (row ${i + 1})`, (id, d, bad) => (
            <select
              id={id}
              className="field"
              value={r.weekday}
              aria-describedby={d}
              aria-invalid={bad || undefined}
              onChange={(e) => update(i, "weekday", e.target.value)}
            >
              {DAYS.map((n, idx) => (
                <option key={n} value={String(idx)}>
                  {n}
                </option>
              ))}
            </select>
          ))}
          {field(i, "start_time", `Start (row ${i + 1})`, (id, d, bad) => (
            <input
              id={id}
              className="field"
              type="time"
              value={r.start_time}
              aria-describedby={d}
              aria-invalid={bad || undefined}
              onChange={(e) => update(i, "start_time", e.target.value)}
            />
          ))}
          {field(i, "end_time", `End (row ${i + 1})`, (id, d, bad) => (
            <input
              id={id}
              className="field"
              type="time"
              value={r.end_time}
              aria-describedby={d}
              aria-invalid={bad || undefined}
              onChange={(e) => update(i, "end_time", e.target.value)}
            />
          ))}
          {field(i, "slot_length_minutes", `Slot length, minutes (row ${i + 1})`, (id, d, bad) => (
            <input
              id={id}
              className="field"
              type="number"
              inputMode="numeric"
              value={r.slot_length_minutes}
              aria-describedby={d}
              aria-invalid={bad || undefined}
              onChange={(e) => update(i, "slot_length_minutes", e.target.value)}
            />
          ))}
          <button
            type="button"
            className="btn btn-sec mt-6"
            disabled={rows.length <= 1}
            aria-label={`Remove row ${i + 1}`}
            onClick={() => onChange(rows.filter((_, idx) => idx !== i))}
          >
            Remove
          </button>
        </div>
      ))}
      <button type="button" className="btn btn-sec" onClick={() => onChange([...rows, { ...EMPTY_ROW }])}>
        + Add template row
      </button>
    </div>
  );
}
