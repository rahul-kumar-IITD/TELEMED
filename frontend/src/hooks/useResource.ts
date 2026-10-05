import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

export type ResourceState<T> =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; error: ApiError }
  | { status: "success"; data: T };

type Outcome<T> = { key: string; data: T } | { key: string; error: ApiError };

/** Fetches `path` through the API client and exposes loading/empty/error/success. */
export function useResource<T>(
  path: string,
  isEmpty: (data: T) => boolean = () => false,
): { state: ResourceState<T>; reload: () => void } {
  const [nonce, setNonce] = useState(0);
  const [outcome, setOutcome] = useState<Outcome<T> | null>(null);
  const key = `${path}#${nonce}`;

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .get<T>(path, ctrl.signal)
      .then((data) => {
        if (!ctrl.signal.aborted) setOutcome({ key, data });
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setOutcome({
          key,
          error: e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", "Unexpected error"),
        });
      });
    return () => ctrl.abort();
  }, [path, key]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  let state: ResourceState<T>;
  if (outcome === null || outcome.key !== key) state = { status: "loading" };
  else if ("error" in outcome) state = { status: "error", error: outcome.error };
  else state = isEmpty(outcome.data) ? { status: "empty" } : { status: "success", data: outcome.data };
  return { state, reload };
}
