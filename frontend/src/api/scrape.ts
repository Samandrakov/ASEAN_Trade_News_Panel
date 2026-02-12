import type { ScrapeRun } from "../types";
import { api } from "./client";

export async function triggerScrape(sources?: string[]): Promise<{ message: string; sources: string[] }> {
  const { data } = await api.post("/scrape/trigger", { sources: sources || null });
  return data;
}

export async function fetchScrapeRuns(limit = 20): Promise<ScrapeRun[]> {
  const { data } = await api.get<ScrapeRun[]>("/scrape/runs", { params: { limit } });
  return data;
}
