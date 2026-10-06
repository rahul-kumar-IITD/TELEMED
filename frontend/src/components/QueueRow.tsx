import { Link } from "react-router-dom";
import { formatZoneTime } from "../config/format";
import { detailRoute } from "../config/routes";
import type { Appointment, StatusTarget } from "../types/contracts";
import { AriaLiveRegion } from "./AriaLiveRegion";

const ACTIONS: Record<string, { label: string; status: StatusTarget }> = {
  CHECKED_IN: { label: "Check in", status: "CHECKED_IN" },
  IN_PROGRESS: { label: "Start consultation", status: "IN_PROGRESS" },
  COMPLETED: { label: "Mark completed", status: "COMPLETED" },
  NO_SHOW: { label: "Mark NO_SHOW", status: "NO_SHOW" },
  CANCEL: { label: "Cancel appointment", status: "CANCELLED" },
};

interface Props {
  appointment: Appointment;
  timezone: string;
  notice?: string;
  busy?: boolean;
  onAction: (status: StatusTarget) => void;
}

/** One queue row: only the buttons the server lists in allowed_actions (plus a disabled early NO_SHOW). */
export function QueueRow({ appointment: a, timezone, notice, busy = false, onAction }: Props) {
  const buttons = a.allowed_actions.flatMap((key) => {
    const action = ACTIONS[key];
    return action ? [{ key, ...action }] : [];
  });
  const earlyNoShow = (a.status === "BOOKED" || a.status === "CHECKED_IN") && !a.allowed_actions.includes("NO_SHOW");

  return (
    <li className="card" data-testid="queue-row">
      <p className="m-0 font-semibold break-words">
        <span data-testid="queue-time">{formatZoneTime(a.start_time, timezone)}</span> · {a.patient.full_name}
      </p>
      <p className="m-0">
        Status: <strong data-testid="queue-status">{a.status}</strong>
      </p>
      <div className="flex flex-wrap gap-2 mt-2">
        {buttons.map((b) => (
          <button key={b.key} type="button" className="btn btn-sec" disabled={busy} onClick={() => onAction(b.status)}>
            {b.label}
          </button>
        ))}
        {earlyNoShow && (
          <button type="button" className="btn btn-sec" disabled aria-describedby={`noshow-${a.appointment_id}`}>
            Mark NO_SHOW
          </button>
        )}
        <Link className="btn btn-sec" to={detailRoute(a.appointment_id)}>
          Details
        </Link>
      </div>
      {earlyNoShow && (
        <p id={`noshow-${a.appointment_id}`} className="text-sm text-ink2">
          Mark NO_SHOW is available once the start time has passed.
        </p>
      )}
      <AriaLiveRegion assertive>
        {notice ? (
          <div data-testid="queue-notice" className="msg msg-err">
            {notice}
          </div>
        ) : null}
      </AriaLiveRegion>
    </li>
  );
}
