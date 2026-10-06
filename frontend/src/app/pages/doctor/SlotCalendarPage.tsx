import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { formatZoneDay, formatZoneTime, zoneDayKey } from "../../../config/format";
import { useDoctorSlots } from "../../../hooks/useDoctorSlots";
import { useProviderTimezone } from "../../../hooks/useProviderTimezone";
import type { Slot } from "../../../types/contracts";

function groupByDay(slots: Slot[], zone: string): { key: string; label: string; items: Slot[] }[] {
  const groups: { key: string; label: string; items: Slot[] }[] = [];
  for (const s of slots) {
    const key = zoneDayKey(s.start_time, zone);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(s);
    else groups.push({ key, label: formatZoneDay(s.start_time, zone), items: [s] });
  }
  return groups;
}

export function SlotCalendarPage() {
  const { state, reload, notices, busyId, block, unblock } = useDoctorSlots();
  const zone = useProviderTimezone();

  return (
    <section aria-labelledby="h-slots">
      <h1 id="h-slots">Slot calendar</h1>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message="You have no slots in the next 14 days." />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && zone === null && <LoadingState />}
      {state.status === "success" && zone !== null && (
        <>
          <p className="text-ink2">Times shown in {zone}</p>
          {groupByDay(state.data.items, zone).map((g) => (
            <section key={g.key} aria-label={g.label} data-testid="slot-day">
              <h2 className="text-lg">{g.label}</h2>
              <ul className="list-none p-0 m-0">
                {g.items.map((s) => (
                  <li key={s.slot_id} className="card flex flex-wrap items-center gap-3" data-testid="slot-row">
                    <span className="font-semibold">{formatZoneTime(s.start_time, zone)}</span>
                    <span data-testid="slot-status">{s.status}</span>
                    {s.status === "BLOCKED" ? (
                      <button type="button" className="btn btn-sec" disabled={busyId === s.slot_id} onClick={() => void unblock(s.slot_id)}>
                        Unblock
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-sec"
                        disabled={s.status !== "AVAILABLE" || busyId === s.slot_id}
                        onClick={() => void block(s.slot_id)}
                      >
                        Block
                      </button>
                    )}
                    {s.status === "BOOKED" && <span className="text-sm text-ink2">Booked slots cannot be blocked.</span>}
                    <AriaLiveRegion assertive>
                      {notices[s.slot_id] ? <div className="msg msg-err">{notices[s.slot_id]}</div> : null}
                    </AriaLiveRegion>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </section>
  );
}
