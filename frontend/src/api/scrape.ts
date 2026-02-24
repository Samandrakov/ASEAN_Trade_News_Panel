import type {
  ScrapeRun,
  ScrapeRunDetail,
  ScrapeLogEntry,
  LiveScrapeStatus,
  SourceStats,
  SourceDetailStats,
  SourceArticle,
  SourceArticleDetail,
  PipelineStatus,
} from "../types";
import { api } from "./client";

export async function triggerScrape(
  sources?: string[]
): Promise<{ message: string; sources: string[] }> {
  const { data } = await api.post("/scrape/trigger", {
    sources: sources || null,
  });
  return data;
}

export async function cancelScrape(): Promise<{ message: string }> {
  const { data } = await api.post("/scrape/cancel");
  return data;
}

export async function cancelScrapeRun(
  runId: number
): Promise<{ message: string }> {
  const { data } = await api.post(`/scrape/runs/${runId}/cancel`);
  return data;
}

export async function fetchPipelineStatus(): Promise<PipelineStatus> {
  const { data } = await api.get<PipelineStatus>("/scrape/status");
  return data;
}

export async function fetchScrapeRuns(
  limit = 20
): Promise<ScrapeRun[]> {
  const { data } = await api.get<ScrapeRun[]>("/scrape/runs", {
    params: { limit },
  });
  return data;
}

export async function fetchScrapeRunDetail(
  runId: number
): Promise<ScrapeRunDetail> {
  const { data } = await api.get<ScrapeRunDetail>(
    `/scrape/runs/${runId}`
  );
  return data;
}

export async function fetchRunsBySource(
  sourceId: string,
  limit = 50
): Promise<ScrapeRun[]> {
  const { data } = await api.get<ScrapeRun[]>(
    `/scrape/runs/by-source/${sourceId}`,
    { params: { limit } }
  );
  return data;
}

export async function fetchLiveScrapeStatus(): Promise<LiveScrapeStatus> {
  const { data } = await api.get<LiveScrapeStatus>("/scrape/live");
  return data;
}

export async function pollRunLogs(
  runId: number,
  afterId: number = 0
): Promise<ScrapeLogEntry[]> {
  const { data } = await api.get<ScrapeLogEntry[]>(
    `/scrape/runs/${runId}/logs`,
    { params: { after_id: afterId } }
  );
  return data;
}

export async function fetchScrapeStats(): Promise<SourceStats[]> {
  const { data } = await api.get<SourceStats[]>("/scrape/stats");
  return data;
}

export async function fetchSourceDetailStats(
  sourceId: string
): Promise<SourceDetailStats> {
  const { data } = await api.get<SourceDetailStats>(
    `/scrape/stats/${sourceId}`
  );
  return data;
}

export async function fetchSourceArticles(
  sourceId: string,
  limit = 50,
  offset = 0
): Promise<SourceArticle[]> {
  const { data } = await api.get<SourceArticle[]>(
    `/scrape/articles/${sourceId}`,
    { params: { limit, offset } }
  );
  return data;
}

export async function fetchSourceArticleDetail(
  sourceId: string,
  articleId: number
): Promise<SourceArticleDetail> {
  const { data } = await api.get<SourceArticleDetail>(
    `/scrape/articles/${sourceId}/${articleId}`
  );
  return data;
}
