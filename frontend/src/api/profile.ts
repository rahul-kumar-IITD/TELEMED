import type { PatientProfile, ProfileUpdate } from "../types/contracts";
import { api } from "./client";

export const PROFILE_PATH = "/api/patients/me/profile";
export const updateProfile = (body: ProfileUpdate) => api.put<PatientProfile>(PROFILE_PATH, body);
