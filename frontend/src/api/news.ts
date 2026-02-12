import type {
  Article,
  ArticleListResponse,
  CountryInfo,
  NewsFilters,
  SummarizeResponse,
  TagInfo,
} from "../types";
import { api } from "./client";

export async function fetchNews(
  filters: NewsFilters
): Promise<ArticleListResponse> {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: filters.page_size,
  };
  if (filters.country) params.country = filters.country;
  if (filters.tag_type) params.tag_type = filters.tag_type;
  if (filters.tag_value) params.tag_value = filters.tag_value;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  if (filters.search) params.search = filters.search;

  const { data } = await api.get<ArticleListResponse>("/news", { params });
  return data;
}

export async function fetchArticle(id: number): Promise<Article> {
  const { data } = await api.get<Article>(`/news/${id}`);
  return data;
}

export async function fetchTags(): Promise<TagInfo[]> {
  const { data } = await api.get<TagInfo[]>("/tags");
  return data;
}

export async function fetchCountries(): Promise<CountryInfo[]> {
  const { data } = await api.get<CountryInfo[]>("/countries");
  return data;
}

export async function summarizeArticles(params: {
  article_ids?: number[];
  country?: string;
  date_from?: string;
  date_to?: string;
  max_articles?: number;
}): Promise<SummarizeResponse> {
  const { data } = await api.post<SummarizeResponse>("/summarize", params);
  return data;
}
