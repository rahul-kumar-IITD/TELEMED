import { useState } from "react";
import { useSlots } from "../hooks/useSlots";
import type { Appointment } from "../types/contracts";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";
import { SlotPicker } from "./SlotPicker";

interface Props {
  appointment: Appointment;
  busy: boolean;
  onConfirm: (slotId: number) => void;
  onClose: () => void;
}

/** Open slots of the appointment's doctor only; the current slot is not offered. */
export function ReschedulePanel({ appointment, busy, onConfirm, onClose }: Props) {
  const slots = useSlots(String(appointment.doctor.doctor_id));
  const [selected, setSelected] = useState<number | null>(null);
  const others =
    slots.state.status === "success" ? slots.state.data.items.filter((s) => s.slot_id !== appointment.slot_id) : [];

  return (
    <div className="mt-3 border-t border-line pt-3" role="group" aria-label="Reschedule">
      <h3>Pick a new slot</h3>
      {slots.state.status === "loading" && <LoadingState />}
      {slots.state.status === "error" && <ErrorState message={slots.state.error.userMessage} onRetry={slots.reload} />}
      {(slots.state.status === "empty" || (slots.state.status === "success" && others.length === 0)) && (
        <EmptyState message="No other open slots for this doctor." />
      )}
      {others.length > 0 && <SlotPicker slots={others} selectedId={selected} onSelect={setSelected} />}
      <div className="flex gap-2 mt-3">
        <button
          type="button"
          className="btn"
          disabled={selected === null || busy}
          onClick={() => selected !== null && onConfirm(selected)}
        >
          Confirm reschedule
        </button>
        <button type="button" className="btn btn-sec" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
