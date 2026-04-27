import { apiRequest } from "./client";
import type { User } from "../types";

export type LoginResponse = {
  token: string;
  token_type: string;
  expires_at: string;
  user: User;
};

export function register(email: string, password: string, username: string) {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, username })
  });
}

export function getMe(token: string) {
  return apiRequest<User>("/auth/me", {}, token);
}

export function updateMe(
  token: string,
  payload: { username: string; full_name?: string | null; profile_bio?: string | null }
) {
  return apiRequest<User>(
    "/auth/me",
    { method: "PATCH", body: JSON.stringify(payload) },
    token
  );
}

export function searchUsers(token: string, query: string) {
  return apiRequest<User[]>(`/auth/users/search?q=${encodeURIComponent(query)}`, {}, token);
}

export function login(email: string, password: string) {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function logout(token: string) {
  return apiRequest<void>("/auth/logout", { method: "POST" }, token);
}
