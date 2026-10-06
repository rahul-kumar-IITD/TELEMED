import type { DoctorFilters } from "../types/contracts";

/** Local start of the given YYYY-MM-DD day as a tz-aware ISO string. */
const startOfDay = (day: string) => new Date(`${day}T00:00:00`).toISOString();
const endOfDay = (day: string) => new Date(`${day}T23:59:59`).toISOString();

export const doctorsPath = (f: DoctorFilters): string => {
  const q = new URLSearchParams();
  if (f.specialty) q.set("specialty", f.specialty);
  if (f.language) q.set("language", f.language);
  if (f.availableFrom) q.set("available_from", startOfDay(f.availableFrom));
  if (f.availableTo) q.set("available_to", endOfDay(f.availableTo));
  q.set("sort", f.sort);
  return `/api/doctors?${q.toString()}`;
};

export const doctorPath = (doctorId: string) => `/api/doctors/${encodeURIComponent(doctorId)}`;
export const slotsPath = (doctorId: string) => `${doctorPath(doctorId)}/slots`;
