import { http } from "./http";
import type { LoginCredentials, User } from "@/types/auth";

export interface LoginResponse {
  user: User;
}

export async function loginRequest(
  credentials: LoginCredentials,
): Promise<User> {
  const response = await http.post<LoginResponse>(
    "/api/auth/login/",
    credentials,
  );
  return response.user;
}

export async function logoutRequest(): Promise<void> {
  await http.post<{ status: string }>("/api/auth/logout/", {});
}

export async function getMeRequest(): Promise<User> {
  return http.get<User>("/api/auth/me/");
}
