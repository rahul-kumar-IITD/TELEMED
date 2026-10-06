import { useState } from "react";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { useAuth } from "../../../hooks/useAuth";
import { useUsers } from "../../../hooks/useUsers";
import type { RoleFilter, User } from "../../../types/contracts";
import { EditPatientProfileDialog } from "./EditPatientProfileDialog";

const FILTERS: { value: RoleFilter; label: string }[] = [
  { value: "", label: "All" },
  { value: "DOCTOR", label: "Doctor" },
  { value: "PATIENT", label: "Patient" },
  { value: "ADMIN", label: "Admin" },
];

export function UserListPage() {
  const { session } = useAuth();
  const { state, reload, role, setRole, notice, pending, toggle } = useUsers();
  const [editing, setEditing] = useState<User | null>(null);

  return (
    <section aria-labelledby="h-users">
      <div className="flex items-end justify-between gap-4">
        <h1 id="h-users">Users</h1>
        <div>
          <label htmlFor="role-filter" className="block font-semibold text-[.9rem] mb-1">
            Role
          </label>
          <select id="role-filter" className="field" value={role} onChange={(e) => setRole(e.target.value as RoleFilter)}>
            {FILTERS.map((f) => (
              <option key={f.label} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <AriaLiveRegion assertive={notice?.kind === "error"}>
        {notice ? (
          <div data-testid="user-notice" className={`msg ${notice.kind === "ok" ? "msg-ok" : "msg-err"}`}>
            {notice.text}
          </div>
        ) : null}
      </AriaLiveRegion>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message="No users match this filter." />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && (
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left text-[.8rem] uppercase text-ink2">
              <th className="p-2">Name / email</th>
              <th className="p-2">Role</th>
              <th className="p-2">Status</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((u) => {
              const self = u.user_id === session?.user_id;
              return (
                <tr key={u.user_id} data-testid="user-row" className="border-b border-line align-top">
                  <td className="p-2">
                    {u.full_name ?? "-"}
                    {self ? " (you)" : ""}
                    <br />
                    <span className="text-sm text-ink2">{u.email}</span>
                  </td>
                  <td className="p-2">{u.role}</td>
                  <td className="p-2" data-testid="user-status">
                    {u.active ? "ACTIVE" : "INACTIVE"}
                  </td>
                  <td className="p-2">
                    <div className="flex flex-wrap gap-2">
                      {u.active ? (
                        <button
                          type="button"
                          className="btn btn-sec"
                          disabled={self || pending === u.user_id}
                          aria-label={`Deactivate ${u.email}`}
                          onClick={() => void toggle(u)}
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-sec"
                          disabled={pending === u.user_id}
                          aria-label={`Reactivate ${u.email}`}
                          onClick={() => void toggle(u)}
                        >
                          Reactivate
                        </button>
                      )}
                      {u.role === "PATIENT" && (
                        <button
                          type="button"
                          className="btn btn-sec"
                          aria-label={`Edit profile ${u.email}`}
                          onClick={() => setEditing(u)}
                        >
                          Edit profile
                        </button>
                      )}
                    </div>
                    {self && <div className="text-sm text-ink2">You cannot deactivate your own account.</div>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {editing && <EditPatientProfileDialog patient={editing} onClose={() => setEditing(null)} />}
    </section>
  );
}
