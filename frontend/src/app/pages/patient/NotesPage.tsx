import { Link, useParams } from "react-router-dom";
import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { NoteList } from "../../../components/NoteList";
import { PATHS } from "../../../config/routes";
import { useNotes } from "../../../hooks/useNotes";
import { NotFoundPage } from "../system/NotFoundPage";

/** Read-only consultation notes of one of the patient's appointments. */
export function NotesPage() {
  const { appointment_id = "" } = useParams();
  const { state, reload } = useNotes(appointment_id);

  if (state.status === "error" && state.error.status === 404) return <NotFoundPage />;
  return (
    <section aria-labelledby="h-notes">
      <Link to={PATHS.appointments} className="btn btn-sec">
        Back to my appointments
      </Link>
      <h1 id="h-notes">Consultation notes</h1>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message="No notes were added for this appointment." />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && <NoteList notes={state.data.items} />}
    </section>
  );
}
