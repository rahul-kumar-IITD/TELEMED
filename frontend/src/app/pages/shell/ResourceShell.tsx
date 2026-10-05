import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { useResource } from "../../../hooks/useResource";
import type { ListResponse } from "../../../types/contracts";
import { NotFoundPage } from "../system/NotFoundPage";

interface ListProps {
  title: string;
  path: string;
  emptyMessage: string;
  /** Object routes map a 404 NOT_FOUND to the not-found page. */
  object?: boolean;
}

/** Placeholder page body: fetches via the API client and shows loading, empty and error states. */
export function ResourceShell({ title, path, emptyMessage, object = false }: ListProps) {
  const { state, reload } = useResource<ListResponse<unknown> | Record<string, unknown>>(path, (d) =>
    "items" in d && Array.isArray(d.items) ? d.items.length === 0 : false,
  );

  if (state.status === "error" && object && state.error.status === 404) return <NotFoundPage />;

  return (
    <section aria-labelledby="h-shell">
      <h1 id="h-shell">{title}</h1>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message={emptyMessage} />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && (
        <div className="card">This section is coming soon.</div>
      )}
    </section>
  );
}
