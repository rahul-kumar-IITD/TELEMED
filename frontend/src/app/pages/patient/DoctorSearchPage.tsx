import { useState } from "react";
import { DoctorCard } from "../../../components/DoctorCard";
import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { FormField } from "../../../components/FormField";
import { LoadingState } from "../../../components/LoadingState";
import { DEFAULT_FILTERS, useDoctors } from "../../../hooks/useDoctors";
import type { DoctorFilters, DoctorSort } from "../../../types/contracts";

export function DoctorSearchPage() {
  const [filters, setFilters] = useState<DoctorFilters>(DEFAULT_FILTERS);
  const { state, reload } = useDoctors(filters);
  const set = <K extends keyof DoctorFilters>(k: K, v: DoctorFilters[K]) => setFilters((f) => ({ ...f, [k]: v }));

  return (
    <section aria-labelledby="h-search" className="max-w-full">
      <h1 id="h-search">Find a doctor</h1>
      <form className="grid grid-cols-1 sm:grid-cols-2 gap-x-3" onSubmit={(e) => e.preventDefault()}>
        <FormField
          id="f-specialty"
          label="Specialty"
          value={filters.specialty}
          onChange={(e) => set("specialty", e.target.value)}
        />
        <FormField
          id="f-language"
          label="Language"
          value={filters.language}
          onChange={(e) => set("language", e.target.value)}
        />
        <FormField
          id="f-from"
          label="Available from"
          type="date"
          value={filters.availableFrom}
          onChange={(e) => set("availableFrom", e.target.value)}
        />
        <FormField
          id="f-to"
          label="Available to"
          type="date"
          value={filters.availableTo}
          onChange={(e) => set("availableTo", e.target.value)}
        />
        <FormField
          id="f-sort"
          label="Sort by"
          control={
            <select
              id="f-sort"
              className="field min-h-11"
              value={filters.sort}
              onChange={(e) => set("sort", e.target.value as DoctorSort)}
            >
              <option value="earliest_slot">Earliest slot</option>
              <option value="fee">Fee</option>
              <option value="name">Name</option>
            </select>
          }
        />
      </form>
      {state.status === "loading" && <LoadingState />}
      {state.status === "empty" && <EmptyState message="No doctors match your filters." />}
      {state.status === "error" && <ErrorState message={state.error.userMessage} onRetry={reload} />}
      {state.status === "success" && (
        <ul className="p-0 m-0" aria-label="Doctors">
          {state.data.items.map((d) => (
            <DoctorCard key={d.doctor_id} doctor={d} />
          ))}
        </ul>
      )}
    </section>
  );
}
