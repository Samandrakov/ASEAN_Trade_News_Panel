from dataclasses import dataclass, field
from datetime import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class RawArticle:
    url: str
    title: str
    body: str
    published_date: datetime | None
    source: str
    source_display: str
    country: str
    category: str | None = None
    author: str | None = None


@dataclass
class ScrapeStats:
    """Collects detailed statistics during scraping for logging."""
    source: str = ""
    sections_attempted: int = 0
    sections_successful: int = 0
    sections_failed: list[str] = field(default_factory=list)
    urls_found: int = 0
    urls_fetched: int = 0
    urls_failed: list[str] = field(default_factory=list)
    articles_parsed: int = 0
    articles_skipped_short: int = 0
    articles_skipped_empty: int = 0
    articles_parse_errors: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        lines = [
            f"=== Scraper Report: {self.source} ===",
            f"  Duration: {elapsed:.1f}s",
            f"  Sections: {self.sections_successful}/{self.sections_attempted} OK",
            f"  URLs found: {self.urls_found}",
            f"  URLs fetched: {self.urls_fetched}, failed: {len(self.urls_failed)}",
            f"  Articles parsed: {self.articles_parsed}",
            f"  Skipped (too short): {self.articles_skipped_short}",
            f"  Skipped (no title/body): {self.articles_skipped_empty}",
            f"  Parse errors: {self.articles_parse_errors}",
        ]
        if self.sections_failed:
            lines.append(f"  Failed sections: {', '.join(self.sections_failed)}")
        if self.urls_failed:
            shown = self.urls_failed[:5]
            lines.append(f"  Failed URLs (first 5): {', '.join(shown)}")
        return "\n".join(lines)
