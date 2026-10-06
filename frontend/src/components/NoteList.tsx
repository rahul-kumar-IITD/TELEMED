import { formatLocalDateTime } from "../config/format";
import type { ConsultationNote } from "../types/contracts";

/** Read-only notes in creation order: no edit, delete or input controls by design. */
export function NoteList({ notes }: { notes: ConsultationNote[] }) {
  return (
    <ol className="list-none p-0 m-0" aria-label="Consultation notes">
      {notes.map((n) => (
        <li key={n.note_id} className="card" data-testid="note">
          <p className="m-0 text-sm text-ink2">{formatLocalDateTime(n.created_at)}</p>
          <p className="m-0 whitespace-pre-wrap break-words">{n.text}</p>
        </li>
      ))}
    </ol>
  );
}
