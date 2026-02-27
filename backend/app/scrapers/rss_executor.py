import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import httpx
from bs4 import BeautifulSoup

from .base import RawArticle

logger = logging.getLogger(__name__)


@dataclass
class RssStats:
    urls_found: int = 0
    articles_parsed: int = 0


class RssExecutor:
    """Fetch and parse an RSS/Atom feed into RawArticle objects."""

    def __init__(
        self,
        map_config: dict,
        delay_seconds: float = 2.0,
        log_callback=None,
    ):
        self.feed_url: str = map_config.get("feed_url", "")
        self.source: str = map_config.get("source", "")
        self.source_display: str = map_config.get("source_display", self.source)
        self.country: str = map_config.get("country", "")
        self.category: str | None = map_config.get("category")
        self.delay = delay_seconds
        self.log_callback = log_callback

    async def _log(self, msg: str, level: str = "INFO"):
        if self.log_callback:
            await self.log_callback(msg, level)

    async def execute(self) -> tuple[list[RawArticle], RssStats]:
        stats = RssStats()
        articles: list[RawArticle] = []

        await self._log(f"Fetching RSS feed: {self.feed_url}")

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(self.feed_url)
                resp.raise_for_status()
        except Exception as e:
            await self._log(f"Failed to fetch feed: {e}", "ERROR")
            return articles, stats

        feed = feedparser.parse(resp.text)
        entries = feed.entries
        stats.urls_found = len(entries)

        await self._log(f"Found {len(entries)} entries in feed")

        for entry in entries:
            url = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not url or not title:
                continue

            # Extract body from content or summary
            body = ""
            if "content" in entry and entry.content:
                body = entry.content[0].get("value", "")
            elif "summary" in entry:
                body = entry.get("summary", "")

            # Strip HTML tags
            if body:
                soup = BeautifulSoup(body, "lxml")
                body = soup.get_text(separator=" ", strip=True)

            if not body:
                continue

            # Parse published date
            pub_date = None
            for date_field in ("published_parsed", "updated_parsed"):
                parsed = entry.get(date_field)
                if parsed:
                    try:
                        pub_date = datetime(*parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                    break

            author = entry.get("author")

            articles.append(
                RawArticle(
                    url=url,
                    title=title,
                    body=body,
                    published_date=pub_date,
                    source=self.source,
                    source_display=self.source_display,
                    country=self.country,
                    category=self.category,
                    author=author,
                )
            )
            stats.articles_parsed += 1

            await asyncio.sleep(0)  # yield control

        await self._log(
            f"Parsed {stats.articles_parsed} articles from {stats.urls_found} entries"
        )
        return articles, stats
