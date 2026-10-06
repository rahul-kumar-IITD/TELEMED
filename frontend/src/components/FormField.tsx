import type { InputHTMLAttributes, ReactNode } from "react";
import { AriaLiveRegion } from "./AriaLiveRegion";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  error?: string;
  /** Replace the default input (e.g. a select). */
  control?: ReactNode;
}

/** Labelled input with an always-present live region for its inline error. */
export function FormField({ id, label, error, control, ...rest }: Props) {
  const errId = `${id}-error`;
  return (
    <div>
      <label htmlFor={id} className="block font-semibold text-[.9rem] mt-2.5 mb-1">
        {label}
      </label>
      {control ?? (
        <input id={id} className="field" aria-invalid={error ? true : undefined} aria-describedby={errId} {...rest} />
      )}
      <AriaLiveRegion id={errId} assertive className="text-err text-[.85rem] mt-1">
        {error}
      </AriaLiveRegion>
    </div>
  );
}
