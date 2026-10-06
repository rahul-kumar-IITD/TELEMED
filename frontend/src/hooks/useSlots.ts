import { slotsPath } from "../api/doctors";
import type { ListResponse, Slot } from "../types/contracts";
import { useResource } from "./useResource";

/** Open slots (next 14 days) of one doctor; `reload` refetches after a booking conflict. */
export const useSlots = (doctorId: string) =>
  useResource<ListResponse<Slot>>(slotsPath(doctorId), (d) => d.items.length === 0);
