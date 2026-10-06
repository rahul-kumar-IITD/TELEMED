import { useState } from "react";
import { AppointmentCard } from "../../../components/AppointmentCard";
import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { ReschedulePanel } from "../../../components/ReschedulePanel";
import { useMyAppointments } from "../../../hooks/useMyAppointments";

export function MyAppointmentsPage() {
  const { state, reload, notices, busyId, cancel, reschedule } = useMyAppointments();
  const [rescheduling, setRescheduling] = useState<number | null>(null);

  return (
    <section aria-labelledby="h-mine">
      <h1 id="h-mine">My appointments</h1>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message="You have no appointments yet." />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && (
        <ul className="list-none p-0 m-0">
          {state.data.items.map((a) => (
            <AppointmentCard
              key={a.appointment_id}
              appointment={a}
              notice={notices[a.appointment_id]}
              busy={busyId === a.appointment_id}
              onCancel={() => void cancel(a.appointment_id)}
              onReschedule={() => setRescheduling(a.appointment_id)}
            >
              {rescheduling === a.appointment_id && (
                <ReschedulePanel
                  appointment={a}
                  busy={busyId === a.appointment_id}
                  onClose={() => setRescheduling(null)}
                  onConfirm={(slotId) => {
                    setRescheduling(null);
                    void reschedule(a.appointment_id, slotId);
                  }}
                />
              )}
            </AppointmentCard>
          ))}
        </ul>
      )}
    </section>
  );
}
