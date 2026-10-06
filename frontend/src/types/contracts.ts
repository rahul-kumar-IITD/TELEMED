// Mirrors specs/design/api-contracts.md (snake_case kept as-is).
export type Role = "PATIENT" | "DOCTOR" | "ADMIN";
export type Gender = "FEMALE" | "MALE" | "OTHER" | "UNDISCLOSED";

export interface User {
  user_id: number;
  email: string;
  role: Role;
  active: boolean;
  full_name: string | null;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  expires_at: string;
  user_id: number;
  role: Role;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  age: number;
  gender: Gender;
  phone: string;
}

export interface RegisterResponse {
  user_id: number;
  role: Role;
  email: string;
}

export interface FieldError {
  field: string;
  message: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  errors?: FieldError[];
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export interface Session {
  access_token: string;
  user_id: number;
  role: Role;
  expires_at: string;
}

export type DoctorSort = "earliest_slot" | "fee" | "name";

export interface DoctorSummary {
  doctor_id: number;
  full_name: string;
  specialty: string;
  languages: string[];
  fee: string; // decimal string, rendered as-is
  earliest_slot: string | null;
}

export interface Slot {
  slot_id: number;
  doctor_id: number;
  start_time: string;
  end_time: string;
  status: string;
}

export interface Appointment {
  appointment_id: number;
  status: string;
  slot_id: number;
  start_time: string;
  end_time: string;
  doctor: { doctor_id: number; full_name: string; specialty: string };
  patient: { patient_id: number; full_name: string };
  fee: string;
  allowed_actions: string[];
  join_url: string | null;
  change_deadline: string;
  created_at: string;
  updated_at: string;
}

/** Search filters as entered; dates are local YYYY-MM-DD strings or "". */
export interface DoctorFilters {
  specialty: string;
  language: string;
  availableFrom: string;
  availableTo: string;
  sort: DoctorSort;
}

export interface AvailabilityTemplate {
  weekday: number; // 0 = Monday
  start_time: string; // HH:MM
  end_time: string;
  slot_length_minutes: number;
}

export interface OnboardDoctorRequest {
  email: string;
  initial_password: string;
  full_name?: string;
  specialty: string;
  languages: string[];
  fee: string; // decimal string, sent as typed
  availability_templates: AvailabilityTemplate[];
}

export interface OnboardedDoctor {
  doctor_id: number;
  user_id: number;
  email: string;
  full_name: string;
  specialty: string;
  languages: string[];
  fee: string;
  availability_templates: (AvailabilityTemplate & { template_id: number })[];
  slots_created: number;
}

export type RoleFilter = "" | Role;

export interface PatientProfile {
  patient_id: number;
  version_number: number;
  full_name: string;
  age: number;
  gender: Gender;
  phone: string;
  updated_at: string;
}

export interface ProfileUpdate {
  full_name: string;
  age: number;
  gender: Gender;
  phone: string;
}

export interface ConsultationNote {
  note_id: number;
  appointment_id: number;
  author_id: number;
  text: string;
  created_at: string;
}

export interface QueueResponse extends ListResponse<Appointment> {
  date: string; // YYYY-MM-DD in the provider timezone
  timezone: string; // IANA name, e.g. "Asia/Kolkata"
}

export interface AppConfig {
  provider_timezone: string;
  slot_window_days: number;
  change_window_minutes: number;
}

export type StatusTarget = "CHECKED_IN" | "IN_PROGRESS" | "COMPLETED" | "NO_SHOW" | "CANCELLED";
