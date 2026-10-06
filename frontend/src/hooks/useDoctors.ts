import { doctorPath, doctorsPath } from "../api/doctors";
import type { DoctorFilters, DoctorSummary, ListResponse } from "../types/contracts";
import { useResource } from "./useResource";

export const DEFAULT_FILTERS: DoctorFilters = {
  specialty: "",
  language: "",
  availableFrom: "",
  availableTo: "",
  sort: "earliest_slot",
};

const noItems = (d: ListResponse<DoctorSummary>) => d.items.length === 0;

/** Doctor search results for the given filters. */
export const useDoctors = (filters: DoctorFilters) =>
  useResource<ListResponse<DoctorSummary>>(doctorsPath(filters), noItems);

/** One doctor; a 404 surfaces as an error state with status 404. */
export const useDoctor = (doctorId: string) => useResource<DoctorSummary>(doctorPath(doctorId));
