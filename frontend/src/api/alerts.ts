import type { Alert, AlertMatch } from "../types";
import { api } from "./client";

export async function fetchAlerts(): Promise<Alert[]> {
  const { data } = await api.get<Alert[]>("/alerts");
  return data;
}

export async function fetchAlertMatches(params: {
  limit?: number;
}): Promise<AlertMatch[]> {
  const { data } = await api.get<AlertMatch[]>("/alerts/matches", { params });
  return data;
}

export async function fetchUnreadCount(): Promise<number> {
  const { data } = await api.get<{ count: number }>("/alerts/unread-count");
  return data.count;
}

export async function createAlert(params: {
  name: string;
  keywords: string[];
  countries: string[];
}): Promise<Alert> {
  const { data } = await api.post<Alert>("/alerts", params);
  return data;
}

export async function updateAlert(
  id: number,
  params: { active?: boolean },
): Promise<Alert> {
  const { data } = await api.put<Alert>(`/alerts/${id}`, params);
  return data;
}

export async function deleteAlert(id: number): Promise<void> {
  await api.delete(`/alerts/${id}`);
}

export async function markAllRead(): Promise<void> {
  await api.post("/alerts/mark-read");
}
