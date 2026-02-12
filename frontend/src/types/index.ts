export interface ArticleTag {
  id: number;
  tag_type: "country_mention" | "topic" | "sector" | "sentiment";
  tag_value: string;
  confidence: number | null;
}

export interface Article {
  id: number;
  url: string;
  title: string;
  body?: string;
  summary: string | null;
  source: string;
  source_display: string;
  country: string;
  category: string | null;
  author: string | null;
  word_count: number | null;
  published_date: string | null;
  scraped_at: string;
  tags: ArticleTag[];
}

export interface ArticleListResponse {
  items: Article[];
  total: number;
  page: number;
  page_size: number;
}

export interface WordFrequency {
  word: string;
  count: number;
}

export interface TimelinePoint {
  date: string;
  count: number;
}

export interface TagDistribution {
  tag: string;
  count: number;
}

export interface CountryInfo {
  code: string;
  name: string;
  count: number;
}

export interface TagInfo {
  tag_type: string;
  tag_value: string;
  count: number;
}

export interface ScrapeRun {
  id: number;
  source: string;
  started_at: string;
  finished_at: string | null;
  articles_found: number;
  articles_new: number;
  status: string;
  error_message: string | null;
}

export interface SummarizeResponse {
  summary: string;
  articles_count: number;
}

export interface NewsFilters {
  country?: string;
  tag_type?: string;
  tag_value?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page: number;
  page_size: number;
}
