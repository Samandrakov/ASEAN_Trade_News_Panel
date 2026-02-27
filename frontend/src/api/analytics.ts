import type { SentimentTrendPoint, TagDistribution, TimelinePoint, WordFrequency } from "../types";
import { api } from "./client";

export async function fetchWordFrequency(params?: {
  country?: string;
  date_from?: string;
  date_to?: string;
  top_n?: number;
}): Promise<WordFrequency[]> {
  const { data } = await api.get<WordFrequency[]>("/analytics/word-frequency", {
    params,
  });
  return data;
}

export async function fetchTimeline(params?: {
  country?: string;
  granularity?: string;
}): Promise<TimelinePoint[]> {
  const { data } = await api.get<TimelinePoint[]>("/analytics/timeline", {
    params,
  });
  return data;
}

export async function fetchTagDistribution(params?: {
  tag_type?: string;
  country?: string;
}): Promise<TagDistribution[]> {
  const { data } = await api.get<TagDistribution[]>(
    "/analytics/tag-distribution",
    { params }
  );
  return data;
}

export async function fetchSentimentTrend(params?: {
  country?: string;
  date_from?: string;
  date_to?: string;
  granularity?: "day" | "week" | "month";
}): Promise<SentimentTrendPoint[]> {
  const { data } = await api.get<SentimentTrendPoint[]>(
    "/analytics/sentiment-trend",
    { params }
  );
  return data;
}
