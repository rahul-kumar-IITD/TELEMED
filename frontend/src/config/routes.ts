import type { Role } from "../types/contracts";

export const PATHS = {
  login: "/login",
  register: "/register",
  doctors: "/doctors",
  queue: "/queue",
  adminUsers: "/admin/users",
} as const;

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
  sessionExpired: "Your session expired. Please log in again.",
} as const;
