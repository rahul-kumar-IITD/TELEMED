import type { Appointment } from "../../src/types/contracts";

const HOUR = 3_600_000;
export const inMinutes = (m: number): string => new Date(Date.now() + m * 60_000).toISOString();

export function appt(over: Partial<Appointment> = {}): Appointment {
  const start = over.start_time ?? inMinutes(24 * 60);
  return {
    appointment_id: 5,
    status: "BOOKED",
    slot_id: 11,
    start_time: start,
    end_time: new Date(Date.parse(start) + HOUR / 2).toISOString(),
    doctor: { doctor_id: 1, full_name: "Dr. Asha Rao", specialty: "Cardiology" },
    patient: { patient_id: 7, full_name: "Pat Synthetic" },
    fee: "500.00",
    allowed_actions: ["CANCEL", "RESCHEDULE"],
    join_url: "https://video.example.test/room/5",
    change_deadline: new Date(Date.parse(start) - HOUR).toISOString(),
    created_at: start,
    updated_at: start,
    ...over,
  };
}
