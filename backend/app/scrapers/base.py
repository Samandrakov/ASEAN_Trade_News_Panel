import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

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


class BaseScraper(ABC):
    SOURCE: str = ""
    SOURCE_DISPLAY: str = ""
    COUNTRY: str = ""
    BASE_URL: str = ""
    SECTIONS: list[str] = []

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": random.choice(USER_AGENTS)},
        )
        self.stats = ScrapeStats(source=self.SOURCE)

    async def close(self):
        await self.client.aclose()

    async def fetch_page(self, url: str) -> str | None:
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            logger.debug(f"[{self.SOURCE}] Fetched {url} ({resp.status_code}, {len(resp.text)} bytes)")
            return resp.text
        except httpx.HTTPError as e:
            logger.warning(f"[{self.SOURCE}] HTTP error fetching {url}: {e}")
            return None

    @abstractmethod
    async def fetch_article_urls(self) -> list[str]:
        """Return list of article URLs from index/feed pages."""

    @abstractmethod
    def parse_article(self, url: str, html: str) -> RawArticle | None:
        """Parse a single article page into RawArticle."""

    async def scrape(self) -> list[RawArticle]:
        """Template method: fetch URLs, then parse each."""
        self.stats = ScrapeStats(source=self.SOURCE)

        logger.info(f"[{self.SOURCE}] Starting scraper for {self.SOURCE_DISPLAY} ({self.COUNTRY})")
        logger.info(f"[{self.SOURCE}] Sections to crawl: {self.SECTIONS}")

        urls = await self.fetch_article_urls()
        self.stats.urls_found = len(urls)
        logger.info(f"[{self.SOURCE}] Found {len(urls)} article URLs across {self.stats.sections_successful}/{self.stats.sections_attempted} sections")

        articles = []
        for i, url in enumerate(urls, 1):
            logger.debug(f"[{self.SOURCE}] [{i}/{len(urls)}] Fetching {url}")
            html = await self.fetch_page(url)
            if not html:
                self.stats.urls_failed.append(url)
                continue

            self.stats.urls_fetched += 1
            try:
                article = self.parse_article(url, html)
                if article is None:
                    self.stats.articles_skipped_empty += 1
                    logger.debug(f"[{self.SOURCE}] Skipped (no title/body): {url}")
                elif len(article.body) < 200:
                    self.stats.articles_skipped_short += 1
                    logger.debug(f"[{self.SOURCE}] Skipped (too short: {len(article.body)} chars): {url}")
                else:
                    article.author = article.author or self._extract_author(html)
                    articles.append(article)
                    self.stats.articles_parsed += 1
                    logger.debug(f"[{self.SOURCE}] Parsed: \"{article.title[:60]}\" ({len(article.body)} chars)")
            except Exception as e:
                self.stats.articles_parse_errors += 1
                logger.warning(f"[{self.SOURCE}] Parse error for {url}: {e}")
            await asyncio.sleep(self.delay)

        logger.info(f"\n{self.stats.summary()}")
        return articles

    def _extract_author(self, html: str) -> str | None:
        """Try to extract author from common meta tags."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        # Try meta author tag
        meta = soup.find("meta", attrs={"name": "author"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        # Try common class names
        for selector in ["span.author", "div.author", "a.author-name", "span.byline"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) < 200:
                    return text
        return None
