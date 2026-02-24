import type { SavedFeed } from "../types";
import { api } from "./client";

export async function fetchFeeds(): Promise<SavedFeed[]> {
  const { data } = await api.get<SavedFeed[]>("/feeds");
  return data;
}

export async function createFeed(params: {
  name: string;
  description?: string;
  filters_json: string;
  color?: string;
}): Promise<SavedFeed> {
  const { data } = await api.post<SavedFeed>("/feeds", params);
  return data;
}

export async function updateFeed(
  id: number,
  params: {
    name?: string;
    description?: string;
    filters_json?: string;
    color?: string;
  }
): Promise<SavedFeed> {
  const { data } = await api.put<SavedFeed>(`/feeds/${id}`, params);
  return data;
}

export async function deleteFeed(id: number): Promise<void> {
  await api.delete(`/feeds/${id}`);
}
