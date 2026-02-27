import type { AuthUser, LoginResponse } from "../types";
import { api } from "./client";

const TOKEN_KEY = "asean_token";
const REFRESH_KEY = "asean_refresh_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/login", {
    username,
    password,
  });
  setToken(data.access_token);
  if (data.refresh_token) {
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
  }
  return data;
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/auth/me");
  return data;
}

export function logout(): void {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (refreshToken) {
    api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => {});
  }
  clearToken();
  window.location.href = "/login";
}
