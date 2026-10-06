// Display formatting. Times use the browser-local zone with a short zone name; money is never parsed.

const timeFmt = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZoneName: "short",
});
const dayFmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", month: "short" });

/** "10:30 IST" in the browser-local zone. */
export function formatLocalTime(iso: string): string {
  const parts = timeFmt.formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("hour")}:${get("minute")} ${get("timeZoneName")}`;
}

/** "Tue, 7 Oct" in the browser-local zone. */
export const formatLocalDay = (iso: string): string => dayFmt.format(new Date(iso));

/** Local calendar-day key used for grouping slots. */
export function localDayKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

export const formatLocalDateTime = (iso: string): string => `${formatLocalDay(iso)}, ${formatLocalTime(iso)}`;

// Provider-zone formatting for doctor screens: the zone comes from the server, never hard-coded.

const partsIn = (iso: string, timeZone: string, opts: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat("en-GB", { ...opts, timeZone }).format(new Date(iso));

/** "10:30 Asia/Kolkata": 24h time in the provider zone followed by its label. */
export const formatZoneTime = (iso: string, timeZone: string): string =>
  `${partsIn(iso, timeZone, { hour: "2-digit", minute: "2-digit", hour12: false })} ${timeZone}`;

/** "Tue, 7 Oct" in the provider zone. */
export const formatZoneDay = (iso: string, timeZone: string): string =>
  partsIn(iso, timeZone, { weekday: "short", day: "numeric", month: "short" });

/** Calendar-day key in the provider zone, used for grouping. */
export const zoneDayKey = (iso: string, timeZone: string): string =>
  partsIn(iso, timeZone, { year: "numeric", month: "2-digit", day: "2-digit" });
