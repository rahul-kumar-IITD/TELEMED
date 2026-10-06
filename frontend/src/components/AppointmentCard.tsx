import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatLocalDateTime } from "../config/format";
import { notesRoute } from "../config/routes";
import type { Appointment } from "../types/contracts";
import { AriaLiveRegion } from "./AriaLiveRegion";

export const JOINABLE = ["BOOKED", "CHECKED_IN", "IN_PROGRESS"];

interface Props {
  appointment: Appointment;
  notice?: string;
  busy?: boolean;
  onCancel: () => void;
  onReschedule: () => void;
  /** Reschedule panel rendered below the actions while open. */
  children?: ReactNode;
}

/** One patient appointment: status as text, join link, and window-aware cancel/reschedule. */
export function AppointmentCard({ appointment: a, notice, busy = false, onCancel, onReschedule, children }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [now] = useState(() => Date.now());
  const changeable =
    a.status === "BOOKED" &&
    a.allowed_actions.includes("CANCEL") &&
    a.allowed_actions.includes("RESCHEDULE") &&
    now <= Date.parse(a.change_deadline);
  const windowClosed = a.status === "BOOKED" && !changeable;

  return (
    <li className="card" data-testid="appointment-card">
      <h2 className="text-lg break-words">{a.doctor.full_name}</h2>
      <p className="m-0 text-ink2 break-words">
        {a.doctor.specialty} · {formatLocalDateTime(a.start_time)}
      </p>
      <p className="m-0">
        Status: <strong data-testid="appointment-status">{a.status}</strong> · Fee {a.fee}
      </p>
      <div className="flex flex-wrap gap-2 mt-2">
        {JOINABLE.includes(a.status) &&
          (a.join_url ? (
            <a className="btn" href={a.join_url} target="_blank" rel="noopener noreferrer">
              Join video visit
            </a>
          ) : (
            <button type="button" className="btn" disabled>
              Join video visit
            </button>
          ))}
        {a.status === "BOOKED" && !confirming && (
          <>
            <button type="button" className="btn btn-sec" disabled={!changeable || busy} onClick={() => setConfirming(true)}>
              Cancel
            </button>
            <button type="button" className="btn btn-sec" disabled={!changeable || busy} onClick={onReschedule}>
              Reschedule
            </button>
          </>
        )}
        {confirming && (
          <>
            <button
              type="button"
              className="btn"
              disabled={busy}
              onClick={() => {
                setConfirming(false);
                onCancel();
              }}
            >
              Confirm cancel
            </button>
            <button type="button" className="btn btn-sec" onClick={() => setConfirming(false)}>
              Keep appointment
            </button>
          </>
        )}
        {a.status === "COMPLETED" && (
          <Link className="btn btn-sec" to={notesRoute(a.appointment_id)}>
            View consultation notes
          </Link>
        )}
      </div>
      {windowClosed && (
        <p className="text-sm text-ink2" data-testid="window-explanation">
          Cancel and Reschedule are unavailable within 60 minutes of the start time.
        </p>
      )}
      <AriaLiveRegion assertive>
        {notice ? (
          <div data-testid="appointment-notice" className="msg msg-err">
            {notice}
          </div>
        ) : null}
      </AriaLiveRegion>
      {children}
    </li>
  );
}
