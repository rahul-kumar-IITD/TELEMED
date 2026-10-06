import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { EmptyState } from "../../../components/EmptyState";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { SlotPicker } from "../../../components/SlotPicker";
import { bookRoute, PATHS } from "../../../config/routes";
import { useDoctor } from "../../../hooks/useDoctors";
import { useSlots } from "../../../hooks/useSlots";
import { NotFoundPage } from "../system/NotFoundPage";

export function DoctorDetailPage() {
  const { doctor_id = "" } = useParams();
  const navigate = useNavigate();
  const doctor = useDoctor(doctor_id);
  const slots = useSlots(doctor_id);
  const [selected, setSelected] = useState<number | null>(null);

  if (doctor.state.status === "error" && doctor.state.error.status === 404) return <NotFoundPage />;

  return (
    <section aria-labelledby="h-doctor">
      <Link to={PATHS.doctors} className="btn btn-sec min-h-11 min-w-11">
        Back to search
      </Link>
      {doctor.state.status === "loading" && <LoadingState />}
      {doctor.state.status === "error" && <ErrorState message={doctor.state.error.userMessage} onRetry={doctor.reload} />}
      {doctor.state.status === "success" && (
        <>
          <h1 id="h-doctor" className="break-words">{doctor.state.data.full_name}</h1>
          <p className="text-ink2 break-words">
            {doctor.state.data.specialty} · {doctor.state.data.languages.join(", ")}
          </p>
          <p>
            Fee: <strong data-testid="doctor-fee">{doctor.state.data.fee}</strong>
          </p>
        </>
      )}
      <h2>Open slots (next 14 days)</h2>
      {slots.state.status === "loading" && <LoadingState />}
      {slots.state.status === "empty" && <EmptyState message="No open slots in the next 14 days." />}
      {slots.state.status === "error" && <ErrorState message={slots.state.error.userMessage} onRetry={slots.reload} />}
      {slots.state.status === "success" && (
        <>
          <SlotPicker slots={slots.state.data.items} selectedId={selected} onSelect={setSelected} />
          <button
            type="button"
            className="btn min-h-11 min-w-11 mt-3"
            disabled={selected === null}
            onClick={() => selected !== null && navigate(bookRoute(doctor_id, selected))}
          >
            Continue to confirm
          </button>
        </>
      )}
    </section>
  );
}
