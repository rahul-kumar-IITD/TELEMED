import type { Role } from "../types/contracts";

export const PATHS = {
  login: "/login",
  register: "/register",
  doctors: "/doctors",
  queue: "/queue",
  slots: "/slots",
  appointments: "/appointments",
  profile: "/profile",
  adminUsers: "/admin/users",
  adminOnboard: "/admin/doctors/new",
} as const;

export const doctorRoute = (doctorId: number | string) => `/doctors/${doctorId}`;
export const bookRoute = (doctorId: number | string, slotId: number | string) =>
  `/doctors/${doctorId}/book/${slotId}`;

export const notesRoute = (appointmentId: number | string) => `/appointments/${appointmentId}/notes`;
export const detailRoute = (appointmentId: number | string) => `/queue/${appointmentId}`;

export function homeForRole(role: Role): string {
  switch (role) {
    case "PATIENT":
      return PATHS.doctors;
    case "DOCTOR":
      return PATHS.queue;
    case "ADMIN":
      return PATHS.adminUsers;
  }
}

export const MESSAGES = {
  busy: "The service is busy, please try again.",
  generic: "Something went wrong. Please try again.",
  invalidCredentials: "Invalid email or password.",
  duplicateEmail: "An account with this email already exists.",
  slotTaken: "That slot is no longer available. The slot list has been refreshed.",
  activeAppointments: "This doctor has active appointments and cannot be deactivated. The status is unchanged.",
  windowClosed: "This appointment can no longer be changed because it starts in under 60 minutes. Nothing was changed.",
  changeSlotTaken: "That slot is no longer available. Please pick another slot.",
  appointmentChanged: "This appointment changed and the action was not applied. The list has been refreshed.",
  slotChanged: "That slot changed and the action was not applied. The calendar has been refreshed.",
  sessionExpired: "Your session expired. Please log in again.",
} as const;
