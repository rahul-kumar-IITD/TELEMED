import { Link, useParams } from "react-router-dom";
import { appointmentPath } from "../../../api/appointments";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { NoteForm } from "../../../components/NoteForm";
import { NoteList } from "../../../components/NoteList";
import { formatZoneDay, formatZoneTime } from "../../../config/format";
import { PATHS } from "../../../config/routes";
import { useNotes } from "../../../hooks/useNotes";
import { useProviderTimezone } from "../../../hooks/useProviderTimezone";
import { useResource } from "../../../hooks/useResource";
import type { Appointment } from "../../../types/contracts";
import { NotFoundPage } from "../system/NotFoundPage";

/** Doctor's view of one appointment: add-note form only when COMPLETED, notes append-only. */
export function AppointmentDetailPage() {
  const { appointment_id = "" } = useParams();
  const appointment = useResource<Appointment>(appointmentPath(appointment_id));
  const notes = useNotes(appointment_id);
  const zone = useProviderTimezone();

  if (appointment.state.status === "error" && appointment.state.error.status === 404) return <NotFoundPage />;

  return (
    <section aria-labelledby="h-detail">
      <Link to={PATHS.queue} className="btn btn-sec">
        Back to queue
      </Link>
      <h1 id="h-detail">Appointment details</h1>
      {appointment.state.status === "loading" && <LoadingState />}
      {appointment.state.status === "error" && (
        <ErrorState message={appointment.state.error.userMessage} onRetry={appointment.reload} />
      )}
      {appointment.state.status === "success" && (
        <div className="card">
          <p className="m-0 font-semibold break-words">{appointment.state.data.patient.full_name}</p>
          {zone !== null && (
            <p className="m-0">
              {formatZoneDay(appointment.state.data.start_time, zone)}, {formatZoneTime(appointment.state.data.start_time, zone)}
            </p>
          )}
          <p className="m-0">
            Status: <strong data-testid="detail-status">{appointment.state.data.status}</strong>
          </p>
        </div>
      )}
      <h2>Consultation notes</h2>
      {notes.state.status === "loading" && <LoadingState />}
      {notes.state.status === "empty" && <p className="text-ink2">No notes yet.</p>}
      {notes.state.status === "error" && <ErrorState message={notes.state.error.userMessage} onRetry={notes.reload} />}
      {notes.state.status === "success" && <NoteList notes={notes.state.data.items} />}
      {appointment.state.status === "success" && appointment.state.data.status === "COMPLETED" && (
        <NoteForm onSubmit={notes.add} />
      )}
    </section>
  );
}
