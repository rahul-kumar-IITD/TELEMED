import { useCallback, useSyncExternalStore } from "react";
import * as authApi from "../api/auth";
import { clearSession, getSession, saveSession, subscribeSession } from "../api/session";
import type { LoginRequest, Session } from "../types/contracts";

export interface AuthState {
  session: Session | null;
  login: (req: LoginRequest) => Promise<Session>;
  logout: () => void;
}

export function useAuth(): AuthState {
  const session = useSyncExternalStore(subscribeSession, getSession, getSession);
  const login = useCallback(async (req: LoginRequest) => {
    const res = await authApi.login(req);
    saveSession(res);
    const s = getSession();
    if (!s) throw new Error("Session could not be stored");
    return s;
  }, []);
  return { session, login, logout: clearSession };
}
