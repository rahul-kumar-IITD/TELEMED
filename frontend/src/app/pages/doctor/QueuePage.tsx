import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { QueueRow } from "../../../components/QueueRow";
import { useQueue } from "../../../hooks/useQueue";

export function QueuePage() {
  const { state, reload, date, setDate, notices, busyId, act } = useQueue();
  const shownDate = date || (state.status === "success" ? state.data.date : "");

  return (
    <section aria-labelledby="h-queue">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 id="h-queue">Daily queue</h1>
        <div>
          <label htmlFor="queue-date" className="block font-semibold text-[.9rem] mb-1">
            Date
          </label>
          <input
            id="queue-date"
            type="date"
            className="field"
            value={shownDate}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
      </div>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message="No appointments on this date." />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && (
        <>
          <p className="text-ink2" data-testid="queue-zone">
            Times shown in {state.data.timezone} · {state.data.date}
          </p>
          <ul className="list-none p-0 m-0">
            {state.data.items.map((a) => (
              <QueueRow
                key={a.appointment_id}
                appointment={a}
                timezone={state.data.timezone}
                notice={notices[a.appointment_id]}
                busy={busyId === a.appointment_id}
                onAction={(status) => void act(a.appointment_id, status)}
              />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
