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

export interface ScrapeLogEntry {
  id: number;
  timestamp: string;
  level: string;
  message: string;
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

export interface ScrapeRunDetail extends ScrapeRun {
  log_entries: ScrapeLogEntry[];
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

export interface ScrapeMapSummary {
  id: number;
  map_id: string;
  name: string;
  country: string;
  active: boolean;
  cron_expression: string | null;
  start_urls_count: number;
  selectors_count: number;
  created_at: string;
  updated_at: string;
}

export interface ScrapeMapFull {
  id: number;
  map_id: string;
  name: string;
  country: string;
  active: boolean;
  cron_expression: string | null;
  created_at: string;
  updated_at: string;
  sitemap_json: string;
}

export interface LiveScrapeRun {
  run_id: number;
  source: string;
  started_at: string;
  articles_found: number;
  articles_new: number;
  recent_logs: ScrapeLogEntry[];
}

export interface LiveScrapeStatus {
  running: boolean;
  runs: LiveScrapeRun[];
}

export interface SourceStats {
  source: string;
  source_display: string;
  country: string;
  total_articles: number;
  last_scraped: string | null;
}

export interface SourceDetailStats {
  source: string;
  total_articles: number;
  total_runs: number;
  success_runs: number;
  failed_runs: number;
  cancelled_runs: number;
  last_run_at: string | null;
}

export interface SourceArticle {
  id: number;
  url: string;
  title: string;
  country: string;
  category: string | null;
  published_date: string | null;
  scraped_at: string | null;
  word_count: number;
  source_display: string;
  author: string | null;
}

export interface SourceArticleDetail extends SourceArticle {
  body: string;
}

export interface PipelineStatus {
  running: boolean;
  running_run_ids: number[];
}

export interface SavedFeed {
  id: number;
  name: string;
  description: string | null;
  filters_json: string;
  color: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedFilters {
  country?: string;
  tag_type?: string;
  tag_value?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AuthUser {
  username: string;
}
