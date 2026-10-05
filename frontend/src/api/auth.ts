import type { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, User } from "../types/contracts";
import { api } from "./client";

export const login = (req: LoginRequest) => api.post<LoginResponse>("/api/auth/login", req, false);
export const register = (req: RegisterRequest) =>
  api.post<RegisterResponse>("/api/auth/register", req, false);
export const me = () => api.get<User>("/api/auth/me");
