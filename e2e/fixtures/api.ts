// Thin helpers over the real backend API. Specs never mock these endpoints.
import { randomUUID } from "node:crypto";
import type { APIRequestContext } from "@playwright/test";

export const API = "http://127.0.0.1:8000";
export const ADMIN = { email: "admin@example.test", password: "Demo-Passw0rd-1" };
export const PASSWORD = "E2e-Passw0rd-1";
export const DOCTOR_NAME = "E2E Fixture Doctor";
export const PATIENT_NAME = "E2E Patient";

export interface SlotRef {
  slot_id: number;
  start_time: string;
  status: string;
}
export interface DoctorData {
  email: string;
  password: string;
  name: string;
  specialty: string;
  token: string;
  /** The only AVAILABLE slots left, in time order, 13 and 14 days out. */
  slots: SlotRef[];
}
export interface PatientData {
  email: string;
  password: string;
  name: string;
  token: string;
}

export const unique = (): string => randomUUID().slice(0, 8);

async function ok<T>(res: Awaited<ReturnType<APIRequestContext["get"]>>, what: string): Promise<T> {
  if (!res.ok()) throw new Error(`${what} failed with ${res.status()}: ${await res.text()}`);
  return (await res.json()) as T;
}

const bearer = (token: string) => ({ Authorization: `Bearer ${token}` });

/**
 * The backend's current instant (HTTP Date header, whole seconds). The browser clock is fixed to
 * this value so slot times created by the server and the page agree on "now".
 */
export async function backendNow(request: APIRequestContext): Promise<Date> {
  const res = await request.get(`${API}/health`);
  const header = res.headers()["date"];
  if (!res.ok() || !header) throw new Error("backend /health did not return a Date header");
  return new Date(header);
}

export async function login(request: APIRequestContext, email: string, password: string): Promise<string> {
  const res = await request.post(`${API}/api/auth/login`, { data: { email, password } });
  return (await ok<{ access_token: string }>(res, "login")).access_token;
}

export async function registerPatient(request: APIRequestContext): Promise<PatientData> {
  const email = `e2e-patient-${unique()}@example.test`;
  const res = await request.post(`${API}/api/auth/register`, {
    data: { email, password: PASSWORD, full_name: PATIENT_NAME, age: 34, gender: "FEMALE", phone: "+910000000000" },
  });
  await ok(res, "register patient");
  return { email, password: PASSWORD, name: PATIENT_NAME, token: await login(request, email, PASSWORD) };
}

/**
 * Onboards a doctor through the admin API with a 09:00 template on every weekday (provider zone),
 * then blocks every generated slot except the last two. Only two far-future open slots remain, so
 * screens are identical on every run and never fall inside the 60-minute change window.
 */
export async function createDoctor(request: APIRequestContext): Promise<DoctorData> {
  const adminToken = await login(request, ADMIN.email, ADMIN.password);
  const email = `e2e-doctor-${unique()}@example.test`;
  const specialty = `E2E-${unique()}`;
  const templates = [0, 1, 2, 3, 4, 5, 6].map((weekday) => ({
    weekday,
    start_time: "09:00",
    end_time: "09:30",
    slot_length_minutes: 30,
  }));
  const res = await request.post(`${API}/api/admin/doctors`, {
    headers: bearer(adminToken),
    data: {
      email,
      initial_password: PASSWORD,
      full_name: DOCTOR_NAME,
      specialty,
      languages: ["en"],
      fee: "40.00",
      availability_templates: templates,
    },
  });
  await ok(res, "onboard doctor");
  const token = await login(request, email, PASSWORD);
  const mine = await ok<{ items: SlotRef[] }>(
    await request.get(`${API}/api/doctors/me/slots`, { headers: bearer(token) }),
    "list doctor slots",
  );
  const open = mine.items.filter((s) => s.status === "AVAILABLE").sort((a, b) => a.start_time.localeCompare(b.start_time));
  for (const slot of open.slice(0, -2)) {
    await ok(await request.put(`${API}/api/doctors/me/slots/${slot.slot_id}/block`, { headers: bearer(token) }), "block slot");
  }
  return { email, password: PASSWORD, name: DOCTOR_NAME, specialty, token, slots: open.slice(-2) };
}

export async function bookSlot(request: APIRequestContext, patient: PatientData, slotId: number): Promise<{ appointment_id: number }> {
  const res = await request.post(`${API}/api/appointments`, { headers: bearer(patient.token), data: { slot_id: slotId } });
  return ok(res, "book slot");
}

/** YYYY-MM-DD of an instant in a given IANA zone. */
export const zoneDate = (iso: string, timeZone: string): string =>
  new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(iso));

export async function providerTimezone(request: APIRequestContext): Promise<string> {
  const cfg = await ok<{ provider_timezone: string }>(await request.get(`${API}/api/config`), "config");
  return cfg.provider_timezone;
}

export async function changeStatus(request: APIRequestContext, token: string, appointmentId: number, status: string): Promise<void> {
  await ok(
    await request.post(`${API}/api/appointments/${appointmentId}/status`, { headers: bearer(token), data: { status } }),
    `status ${status}`,
  );
}

export async function addNote(request: APIRequestContext, token: string, appointmentId: number, text: string): Promise<void> {
  await ok(
    await request.post(`${API}/api/appointments/${appointmentId}/notes`, { headers: bearer(token), data: { text } }),
    "add note",
  );
}
