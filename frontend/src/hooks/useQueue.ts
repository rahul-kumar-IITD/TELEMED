import { useState } from "react";
import { changeStatus, queuePath } from "../api/doctorQueue";
import { MESSAGES } from "../config/routes";
import type { QueueResponse, StatusTarget } from "../types/contracts";
import { useResource } from "./useResource";
import { useRowActions } from "./useRowActions";

const conflictMessage = (): string => MESSAGES.appointmentChanged;

/** Daily queue for a date ("" = server default today) with status actions. */
export function useQueue() {
  const [date, setDate] = useState("");
  const { state, reload } = useResource<QueueResponse>(queuePath(date), (d) => d.items.length === 0);
  const { notices, busyId, run } = useRowActions(reload, conflictMessage);
  const act = (appointmentId: number, status: StatusTarget) => run(appointmentId, () => changeStatus(appointmentId, status));
  return { state, reload, date, setDate, notices, busyId, act };
}
