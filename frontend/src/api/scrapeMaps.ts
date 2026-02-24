import type { ScrapeMapSummary, ScrapeMapFull } from "../types";
import { api } from "./client";

export async function fetchScrapeMaps(
  activeOnly = false
): Promise<ScrapeMapSummary[]> {
  const { data } = await api.get<ScrapeMapSummary[]>("/scrape-maps", {
    params: { active_only: activeOnly },
  });
  return data;
}

export async function fetchScrapeMap(
  mapId: string
): Promise<ScrapeMapFull> {
  const { data } = await api.get<ScrapeMapFull>(`/scrape-maps/${mapId}`);
  return data;
}

export async function createScrapeMap(
  sitemapJson: string
): Promise<ScrapeMapFull> {
  const { data } = await api.post<ScrapeMapFull>("/scrape-maps", {
    sitemap_json: sitemapJson,
  });
  return data;
}

export async function updateScrapeMap(
  mapId: string,
  update: { sitemap_json?: string; active?: boolean; cron_expression?: string | null }
): Promise<ScrapeMapFull> {
  const { data } = await api.put<ScrapeMapFull>(
    `/scrape-maps/${mapId}`,
    update
  );
  return data;
}

export async function deleteScrapeMap(mapId: string): Promise<void> {
  await api.delete(`/scrape-maps/${mapId}`);
}

export async function toggleScrapeMap(
  mapId: string
): Promise<{ map_id: string; active: boolean }> {
  const { data } = await api.post<{ map_id: string; active: boolean }>(
    `/scrape-maps/${mapId}/toggle`
  );
  return data;
}

export async function importChromeMap(
  sitemapJson: string
): Promise<ScrapeMapFull> {
  const { data } = await api.post<ScrapeMapFull>("/scrape-maps/import", {
    sitemap_json: sitemapJson,
  });
  return data;
}
