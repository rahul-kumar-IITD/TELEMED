import { blockSlot, MY_SLOTS_PATH, unblockSlot } from "../api/doctorQueue";
import { MESSAGES } from "../config/routes";
import type { ListResponse, Slot } from "../types/contracts";
import { useResource } from "./useResource";
import { useRowActions } from "./useRowActions";

const conflictMessage = (): string => MESSAGES.slotChanged;

/** The doctor's own slots (all statuses) with block/unblock. */
export function useDoctorSlots() {
  const { state, reload } = useResource<ListResponse<Slot>>(MY_SLOTS_PATH, (d) => d.items.length === 0);
  const { notices, busyId, run } = useRowActions(reload, conflictMessage);
  const block = (slotId: number) => run(slotId, () => blockSlot(slotId));
  const unblock = (slotId: number) => run(slotId, () => unblockSlot(slotId));
  return { state, reload, notices, busyId, block, unblock };
}
