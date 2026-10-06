import { useState, type FormEvent } from "react";
import { AriaLiveRegion } from "./AriaLiveRegion";

interface Props {
  /** Resolves to an error message, or null when the note was appended. */
  onSubmit: (text: string) => Promise<string | null>;
}

/** Append-only note entry; the caller renders it only for COMPLETED appointments. */
export function NoteForm({ onSubmit }: Props) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (!text.trim()) {
      setError("Note text is required.");
      return;
    }
    setBusy(true);
    const result = await onSubmit(text);
    setBusy(false);
    setError(result ?? "");
    if (result === null) setText("");
  };

  return (
    <form onSubmit={(e) => void submit(e)} noValidate aria-label="Add consultation note">
      <label htmlFor="note-text" className="block font-semibold text-[.9rem] mt-2.5 mb-1">
        Consultation note
      </label>
      <textarea
        id="note-text"
        className="field"
        rows={4}
        maxLength={5000}
        value={text}
        aria-describedby="note-error"
        onChange={(e) => setText(e.target.value)}
      />
      <AriaLiveRegion id="note-error" assertive className="text-err text-[.85rem] mt-1">
        {error}
      </AriaLiveRegion>
      <button type="submit" className="btn mt-2" disabled={busy}>
        Add note
      </button>
    </form>
  );
}
