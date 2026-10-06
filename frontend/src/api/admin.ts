import type {
  ListResponse,
  OnboardDoctorRequest,
  OnboardedDoctor,
  PatientProfile,
  ProfileUpdate,
  RoleFilter,
  User,
} from "../types/contracts";
import { api } from "./client";

export type UserList = ListResponse<User>;

export const usersPath = (role: RoleFilter): string =>
  role ? `/api/admin/users?role=${encodeURIComponent(role)}` : "/api/admin/users";

export const patientProfilePath = (patientId: number): string => `/api/patients/${patientId}/profile`;

export const onboardDoctor = (req: OnboardDoctorRequest) => api.post<OnboardedDoctor>("/api/admin/doctors", req);
export const deactivateUser = (userId: number) => api.put<User>(`/api/admin/users/${userId}/deactivate`);
export const reactivateUser = (userId: number) => api.put<User>(`/api/admin/users/${userId}/reactivate`);
export const updatePatientProfile = (patientId: number, body: ProfileUpdate) =>
  api.put<PatientProfile>(`/api/admin/patients/${patientId}/profile`, body);
