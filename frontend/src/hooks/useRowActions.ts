import { useCallback, useState } from "react";
import { ApiError } from "../api/client";
import { MESSAGES } from "../config/routes";

/**
 * Runs per-row actions. A 409 becomes an inline message for that row and triggers `reload`
 * so the row shows the server state; other failures show a generic message.
 */
export function useRowActions(reload: () => void, conflictMessage: (e: ApiError) => string) {
  const [notices, setNotices] = useState<Record<number, string>>({});
  const [busyId, setBusyId] = useState<number | null>(null);

  const run = useCallback(
    async (id: number, action: () => Promise<unknown>): Promise<boolean> => {
      setBusyId(id);
      setNotices((n) => Object.fromEntries(Object.entries(n).filter(([k]) => Number(k) !== id)));
      try {
        await action();
        reload();
        return true;
      } catch (e) {
        const message = e instanceof ApiError ? (e.status === 409 ? conflictMessage(e) : e.userMessage) : MESSAGES.generic;
        setNotices((n) => ({ ...n, [id]: message }));
        if (e instanceof ApiError && e.status === 409) reload();
        return false;
      } finally {
        setBusyId(null);
      }
    },
    [reload, conflictMessage],
  );
  return { notices, busyId, run };
}
