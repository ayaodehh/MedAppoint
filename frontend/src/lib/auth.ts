import { apiClient, ApiError } from "@/lib/api-client";
import type { User } from "@/lib/types";

export type LoginPayload = {
  username: string;
  password: string;
  otp_token?: string;
};

export type RegisterPayload = {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  password: string;
  medical_record_number: string;
  date_of_birth: string;
};

export async function getCurrentUser() {
  try {
    return await apiClient.get<User>("/accounts/users/me/");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function login(payload: LoginPayload) {
  const response = await apiClient.post<{ user: User }>("/auth/login/", payload);
  return response.user;
}

export async function register(payload: RegisterPayload) {
  const response = await apiClient.post<{ user: User }>("/auth/register/", payload);
  return response.user;
}

export async function logout() {
  await apiClient.post("/auth/logout/", {});
}

export async function stepUpPassword(username: string, password: string) {
  await apiClient.post("/auth/login/", { username, password });
}
