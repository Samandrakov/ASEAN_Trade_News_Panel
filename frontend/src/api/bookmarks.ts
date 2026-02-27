import type { Bookmark } from "../types";
import { api } from "./client";

export async function fetchBookmarks(): Promise<Bookmark[]> {
  const { data } = await api.get<Bookmark[]>("/bookmarks");
  return data;
}

export async function createBookmark(article_id: number): Promise<Bookmark> {
  const { data } = await api.post<Bookmark>("/bookmarks", { article_id });
  return data;
}

export async function deleteBookmarkByArticle(
  article_id: number,
): Promise<void> {
  await api.delete(`/bookmarks/${article_id}`);
}
