import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { ErrorState } from "../../../components/ErrorState";
import { LoadingState } from "../../../components/LoadingState";
import { formatLocalDateTime } from "../../../config/format";
import { doctorRoute, MESSAGES, PATHS } from "../../../config/routes";
import { useBooking } from "../../../hooks/useBooking";
import { useDoctor } from "../../../hooks/useDoctors";
import { useSlots } from "../../../hooks/useSlots";
import type { Appointment } from "../../../types/contracts";
import { NotFoundPage } from "../system/NotFoundPage";

export function BookingConfirmationPage() {
  const { doctor_id = "", slot_id = "" } = useParams();
  const doctor = useDoctor(doctor_id);
  const slots = useSlots(doctor_id);
  const { book, busy } = useBooking();
  const [booked, setBooked] = useState<Appointment | null>(null);
  const [message, setMessage] = useState("");

  if (doctor.state.status === "error" && doctor.state.error.status === 404) return <NotFoundPage />;

  const onConfirm = async () => {
    setMessage("");
    const res = await book(Number(slot_id));
    if (res.kind === "booked") setBooked(res.appointment);
    else if (res.kind === "conflict") {
      slots.reload();
      setMessage(MESSAGES.slotTaken);
    } else setMessage(res.message);
  };

  if (booked) {
    return (
      <section aria-labelledby="h-confirm">
        <h1 id="h-confirm">Booking confirmed</h1>
        <div className="card" data-testid="confirmation">
          <p className="m-0 break-words">Doctor: {booked.doctor.full_name}</p>
          <p className="m-0">Time: {formatLocalDateTime(booked.start_time)}</p>
          <p className="m-0">
            Fee: <strong data-testid="confirm-fee">{booked.fee}</strong>
          </p>
        </div>
        <Link to={PATHS.doctors} className="btn btn-sec min-h-11 min-w-11">
          Back to search
        </Link>
      </section>
    );
  }

  const slot =
    slots.state.status === "success" ? slots.state.data.items.find((s) => String(s.slot_id) === slot_id) : undefined;
  const loading = doctor.state.status === "loading" || slots.state.status === "loading";

  return (
    <section aria-labelledby="h-confirm">
      <h1 id="h-confirm">Confirm booking</h1>
      <AriaLiveRegion assertive className={message ? "msg msg-err" : undefined}>
        {message}
      </AriaLiveRegion>
      {loading && <LoadingState />}
      {doctor.state.status === "error" && <ErrorState message={doctor.state.error.userMessage} onRetry={doctor.reload} />}
      {slots.state.status === "error" && <ErrorState message={slots.state.error.userMessage} onRetry={slots.reload} />}
      {doctor.state.status === "success" && slot && (
        <div className="card" data-testid="booking-summary">
          <p className="m-0 break-words">Doctor: {doctor.state.data.full_name}</p>
          <p className="m-0">Time: {formatLocalDateTime(slot.start_time)}</p>
          <p className="m-0">
            Fee: <strong data-testid="summary-fee">{doctor.state.data.fee}</strong>
          </p>
          <button type="button" className="btn min-h-11 min-w-11 mt-3" disabled={busy} onClick={onConfirm}>
            Confirm booking
          </button>
        </div>
      )}
      {!loading && !slot && slots.state.status !== "error" && <p>This slot is not available.</p>}
      {!loading && !slot && (
        <Link to={doctorRoute(doctor_id)} className="btn btn-sec min-h-11 min-w-11">
          Choose another slot
        </Link>
      )}
    </section>
  );
}
