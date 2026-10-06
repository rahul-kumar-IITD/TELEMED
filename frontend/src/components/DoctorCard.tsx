import { Link } from "react-router-dom";
import { doctorRoute } from "../config/routes";
import { formatLocalDateTime } from "../config/format";
import type { DoctorSummary } from "../types/contracts";

export function DoctorCard({ doctor }: { doctor: DoctorSummary }) {
  return (
    <li className="card list-none" data-testid="doctor-card">
      <h2 className="m-0 text-lg break-words">{doctor.full_name}</h2>
      <p className="m-0 text-ink2 break-words">
        {doctor.specialty} · {doctor.languages.join(", ")}
      </p>
      <p className="m-0 mt-1">
        Fee: <strong data-testid="doctor-fee">{doctor.fee}</strong>
      </p>
      <p className="m-0 text-sm text-ink2">
        {doctor.earliest_slot ? `Next slot: ${formatLocalDateTime(doctor.earliest_slot)}` : "No open slots"}
      </p>
      <Link
        to={doctorRoute(doctor.doctor_id)}
        className="btn btn-sec min-h-11 min-w-11 mt-2"
        aria-label={`View ${doctor.full_name}`}
      >
        View slots
      </Link>
    </li>
  );
}
