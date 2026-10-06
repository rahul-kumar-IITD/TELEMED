import { useCallback, useState } from "react";
import { deactivateUser, reactivateUser, usersPath, type UserList } from "../api/admin";
import { ApiError } from "../api/client";
import { MESSAGES } from "../config/routes";
import type { RoleFilter, User } from "../types/contracts";
import { useResource } from "./useResource";

export type Notice = { kind: "ok" | "error"; text: string } | null;

/** Admin user list with role filter and deactivate/reactivate; failures never change row status. */
export function useUsers() {
  const [role, setRole] = useState<RoleFilter>("");
  const [notice, setNotice] = useState<Notice>(null);
  const [pending, setPending] = useState<number | null>(null);
  const { state, reload } = useResource<UserList>(usersPath(role), (d) => d.items.length === 0);

  const toggle = useCallback(
    async (user: User) => {
      setPending(user.user_id);
      setNotice(null);
      try {
        if (user.active) await deactivateUser(user.user_id);
        else await reactivateUser(user.user_id);
        setNotice({ kind: "ok", text: `${user.email} is now ${user.active ? "deactivated" : "active"}.` });
        reload();
      } catch (e) {
        if (e instanceof ApiError && e.status === 409 && e.code === "ACTIVE_APPOINTMENTS_EXIST") {
          setNotice({ kind: "error", text: `Cannot deactivate ${user.email}: ${MESSAGES.activeAppointments}` });
        } else {
          setNotice({ kind: "error", text: e instanceof ApiError ? e.userMessage : MESSAGES.generic });
        }
      } finally {
        setPending(null);
      }
    },
    [reload],
  );

  return { state, reload, role, setRole, notice, pending, toggle };
}
