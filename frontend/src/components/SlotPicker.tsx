import { formatLocalDay, formatLocalTime, localDayKey } from "../config/format";
import type { Slot } from "../types/contracts";

interface Props {
  slots: Slot[];
  selectedId: number | null;
  onSelect: (slotId: number) => void;
}

/** Open slots grouped by local calendar day; times in the browser-local zone. */
export function SlotPicker({ slots, selectedId, onSelect }: Props) {
  const sorted = [...slots].sort((a, b) => a.start_time.localeCompare(b.start_time));
  const groups: { key: string; label: string; items: Slot[] }[] = [];
  for (const s of sorted) {
    const key = localDayKey(s.start_time);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(s);
    else groups.push({ key, label: formatLocalDay(s.start_time), items: [s] });
  }
  return (
    <div>
      {groups.map(({ key, label, items }) => (
        <section key={key} aria-label={label} data-testid="slot-day">
          <h3 className="mb-1">{label}</h3>
          <div className="flex flex-wrap gap-2">
            {items.map((s) => (
              <button
                key={s.slot_id}
                type="button"
                className={`btn min-h-11 min-w-11 ${s.slot_id === selectedId ? "" : "btn-sec"}`}
                aria-pressed={s.slot_id === selectedId}
                onClick={() => onSelect(s.slot_id)}
              >
                {formatLocalTime(s.start_time)}
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
