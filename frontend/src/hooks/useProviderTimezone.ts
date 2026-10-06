import { CONFIG_PATH } from "../api/doctorQueue";
import type { AppConfig } from "../types/contracts";
import { useResource } from "./useResource";

/** Provider timezone from GET /api/config (never hard-coded); null until loaded. */
export function useProviderTimezone(): string | null {
  const { state } = useResource<AppConfig>(CONFIG_PATH);
  return state.status === "success" ? state.data.provider_timezone : null;
}
