import asyncio
import ipaddress
import logging
import random
import re
import socket
from collections.abc import Awaitable, Callable
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from .base import RawArticle, ScrapeStats, USER_AGENTS

logger = logging.getLogger(__name__)

# Type for the async log callback
LogCallback = Callable[[str, str], Awaitable[None]]


class SitemapExecutor:
    """Universal scraper engine that executes a Web Scraper Chrome Extension
    compatible sitemap JSON to produce RawArticle objects."""

    def __init__(
        self,
        sitemap: dict,
        delay: float = 2.0,
        log_callback: LogCallback | None = None,
    ):
        self.sitemap = sitemap
        self.delay = delay
        self.meta = sitemap.get("_meta", {})
        self.source = sitemap["_id"]
        self.source_display = self.meta.get("source_display", self.source)
        self.country = self.meta.get("country", "")
        self.start_urls = sitemap.get("startUrls", [])
        self.selectors = sitemap.get("selectors", [])
        self.url_filter = self.meta.get("url_filter_pattern")
        self.category_mapping = self.meta.get("category_mapping", {})
        self.date_source = self.meta.get("date_source", "selector")
        self.date_url_pattern = self.meta.get("date_url_pattern")
        self.date_selector_formats = self.meta.get("date_selector_formats", [])
        self.body_separator = self.meta.get("body_separator", "\n")
        self.min_body_length = self.meta.get("min_body_length", 200)
        self.author_selectors = self.meta.get("author_selectors", [])
        self._log_callback = log_callback

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": random.choice(USER_AGENTS)},
        )
        self.stats = ScrapeStats(source=self.source)

        # Build selector lookup: uuid -> selector dict
        self._selector_by_uuid: dict[str, dict] = {}
        # Build children map: parent_uuid -> list of child selectors
        self._children: dict[str, list[dict]] = {}
        for sel in self.selectors:
            self._selector_by_uuid[sel["uuid"]] = sel
            for parent_uuid in sel.get("parentSelectors", []):
                self._children.setdefault(parent_uuid, []).append(sel)

        # Identify root selector uuid
        root_sel = sitemap.get("rootSelector", {})
        self._root_uuid = root_sel.get("uuid", "0")

        # Identify root-level link selectors
        self._root_link_selectors = [
            s for s in self.selectors
            if s.get("type") == "SelectorLink"
            and self._root_uuid in s.get("parentSelectors", [])
        ]
        # Identify link selector UUIDs (for finding article-level selectors)
        self._link_uuids = {s["uuid"] for s in self._root_link_selectors}

        # Article-level selectors: those whose parent is a link selector
        self._article_selectors: dict[str, dict] = {}
        for sel in self.selectors:
            parents = set(sel.get("parentSelectors", []))
            if parents & self._link_uuids:
                self._article_selectors[sel["id"]] = sel

    async def _log(self, message: str, level: str = "INFO"):
        """Log to both Python logger and DB callback."""
        getattr(logger, level.lower(), logger.info)(
            f"[{self.source}] {message}"
        )
        if self._log_callback:
            try:
                await self._log_callback(message, level)
            except Exception:
                pass

    async def close(self):
        await self.client.aclose()

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Check that URL is not targeting internal/private networks (SSRF protection)."""
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Block obvious localhost variants
        blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
        if hostname.lower() in blocked_hosts:
            return False
        try:
            # Resolve hostname and check if IP is private/reserved
            for info in socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM):
                ip = ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
        except (socket.gaierror, ValueError):
            return False
        return True

    async def fetch_page(self, url: str) -> str | None:
        if not self._is_safe_url(url):
            logger.warning(f"[{self.source}] SSRF blocked: {url}")
            await self._log(f"Blocked unsafe URL: {url}", "WARNING")
            return None
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            logger.debug(
                f"[{self.source}] Fetched {url} "
                f"({resp.status_code}, {len(resp.text)} bytes)"
            )
            return resp.text
        except httpx.HTTPError as e:
            logger.warning(f"[{self.source}] HTTP error fetching {url}: {e}")
            return None

    def _detect_category(
        self, start_url: str, article_url: str
    ) -> str | None:
        if start_url in self.category_mapping:
            return self.category_mapping[start_url]
        for pattern, category in self.category_mapping.items():
            if pattern in article_url:
                return category
        return None

    def _parse_date_from_url(self, url: str) -> datetime | None:
        if not self.date_url_pattern:
            return None
        match = re.search(self.date_url_pattern, url)
        if match:
            groups = match.groups()
            try:
                if len(groups) >= 3:
                    return datetime(
                        int(groups[0]), int(groups[1]), int(groups[2])
                    )
            except (ValueError, IndexError):
                pass
        return None

    def _parse_date_from_text(self, text: str) -> datetime | None:
        if not text:
            return None
        text = text.strip()
        # Try ISO 8601 with timezone first (e.g. 2026-02-19T19:33:19+07:00)
        try:
            from datetime import timezone
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            pass
        for fmt in self.date_selector_formats:
            try:
                return datetime.strptime(text[:30], fmt)
            except ValueError:
                continue
        # Try common patterns as fallback
        # Pattern: "January 15, 2024"
        match = re.search(r"(\w+ \d+, \d{4})", text)
        if match:
            try:
                return datetime.strptime(match.group(1), "%B %d, %Y")
            except ValueError:
                pass
        # Pattern: "15/01/2024"
        match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if match:
            try:
                return datetime.strptime(match.group(1), "%d/%m/%Y")
            except ValueError:
                pass
        return None

    @staticmethod
    def _get_element_text(el) -> str:
        """Extract text from an element, handling meta tags specially."""
        if el.name == "meta":
            return (el.get("content") or "").strip()
        return el.get_text(strip=True)

    def _extract_text(
        self, soup: BeautifulSoup, selector_def: dict
    ) -> str:
        css = selector_def["selector"]
        multiple = selector_def.get("multiple", False)
        extract_attr = selector_def.get("extractAttribute")

        if multiple:
            elements = soup.select(css)
            if extract_attr:
                parts = [
                    el.get(extract_attr, "").strip()
                    for el in elements
                    if el.get(extract_attr)
                ]
            else:
                parts = [
                    self._get_element_text(el)
                    for el in elements
                    if self._get_element_text(el)
                ]
            return self.body_separator.join(parts)
        else:
            # For comma-separated fallback selectors like "h1.title, h1"
            for single_css in css.split(","):
                single_css = single_css.strip()
                el = soup.select_one(single_css)
                if el:
                    if extract_attr:
                        val = el.get(extract_attr, "").strip()
                        if val:
                            return val
                    else:
                        text = self._get_element_text(el)
                        if text:
                            return text
            return ""

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Strip query params and fragments to avoid UTM duplicates."""
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    def _extract_links(
        self, soup: BeautifulSoup, selector_def: dict, base_url: str
    ) -> list[str]:
        css = selector_def["selector"]
        extract_attr = selector_def.get("extractAttribute", "href")
        links: set[str] = set()
        for el in soup.select(css):
            href = el.get(extract_attr, "")
            if not href:
                continue
            full_url = urljoin(base_url, href)
            clean_url = self._normalize_url(full_url)
            if self.url_filter:
                if re.search(self.url_filter, clean_url):
                    links.add(clean_url)
            else:
                links.add(clean_url)
        return list(links)

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        for sel in self.author_selectors:
            if "meta[" in sel:
                el = soup.select_one(sel)
                if el and el.get("content"):
                    return el["content"].strip()
            else:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(strip=True)
                    if text and len(text) < 200:
                        return text
        return None

    async def scrape(self) -> list[RawArticle]:
        self.stats = ScrapeStats(source=self.source)
        await self._log(
            f"Starting sitemap executor for "
            f"{self.source_display} ({self.country})"
        )
        await self._log(f"Start URLs: {len(self.start_urls)} sections")

        # Phase 1: Collect article URLs from all startUrls
        article_urls: dict[str, str] = {}  # url -> start_url
        for idx, start_url in enumerate(self.start_urls, 1):
            self.stats.sections_attempted += 1
            await self._log(
                f"Fetching section [{idx}/{len(self.start_urls)}]: {start_url}"
            )
            html = await self.fetch_page(start_url)
            if not html:
                self.stats.sections_failed.append(start_url)
                await self._log(
                    f"Failed to fetch section: {start_url}", "WARNING"
                )
                continue
            self.stats.sections_successful += 1
            soup = BeautifulSoup(html, "html.parser")

            before = len(article_urls)
            for link_sel in self._root_link_selectors:
                found = self._extract_links(soup, link_sel, start_url)
                for url in found:
                    if url not in article_urls:
                        article_urls[url] = start_url

            new_in_section = len(article_urls) - before
            await self._log(
                f"Section {idx}: +{new_in_section} URLs "
                f"({len(article_urls)} total)"
            )
            await asyncio.sleep(self.delay * 0.5)

        self.stats.urls_found = len(article_urls)
        await self._log(
            f"Phase 1 done: {len(article_urls)} article URLs from "
            f"{self.stats.sections_successful}/"
            f"{self.stats.sections_attempted} sections"
        )

        if not article_urls:
            await self._log("No article URLs found, finishing", "WARNING")
            return []

        # Phase 2: Visit each article URL and extract data
        articles: list[RawArticle] = []
        total = len(article_urls)
        for i, (url, start_url) in enumerate(article_urls.items(), 1):
            html = await self.fetch_page(url)
            if not html:
                self.stats.urls_failed.append(url)
                if i % 10 == 0 or i == total:
                    await self._log(
                        f"Progress: {i}/{total} URLs processed, "
                        f"{len(self.stats.urls_failed)} failed"
                    )
                continue

            self.stats.urls_fetched += 1
            try:
                soup = BeautifulSoup(html, "html.parser")

                # Extract title
                title = ""
                if "title" in self._article_selectors:
                    title = self._extract_text(
                        soup, self._article_selectors["title"]
                    )

                # Extract body
                body = ""
                if "body" in self._article_selectors:
                    body = self._extract_text(
                        soup, self._article_selectors["body"]
                    )

                # Extract date
                pub_date = None
                if self.date_source == "url":
                    pub_date = self._parse_date_from_url(url)
                if (
                    pub_date is None
                    and "published_date" in self._article_selectors
                ):
                    date_sel = self._article_selectors["published_date"]
                    el = soup.select_one(date_sel["selector"])
                    if el:
                        dt_attr = el.get("datetime") or el.get("content")
                        if dt_attr:
                            pub_date = self._parse_date_from_text(dt_attr)
                        if pub_date is None:
                            pub_date = self._parse_date_from_text(
                                el.get_text(strip=True)
                            )
                if pub_date is None and self.date_source != "url":
                    pub_date = self._parse_date_from_url(url)

                # Validate
                if not title or not body:
                    self.stats.articles_skipped_empty += 1
                    continue
                if len(body) < self.min_body_length:
                    self.stats.articles_skipped_short += 1
                    continue

                author = self._extract_author(soup)
                category = self._detect_category(start_url, url)

                articles.append(
                    RawArticle(
                        url=url,
                        title=title,
                        body=body,
                        published_date=pub_date,
                        source=self.source,
                        source_display=self.source_display,
                        country=self.country,
                        category=category,
                        author=author,
                    )
                )
                self.stats.articles_parsed += 1

                # Log every parsed article
                await self._log(
                    f"[{i}/{total}] Parsed: \"{title[:60]}\" "
                    f"({len(body)} chars)"
                )

            except Exception as e:
                self.stats.articles_parse_errors += 1
                await self._log(
                    f"Parse error for {url}: {e}", "WARNING"
                )

            # Log progress every 10 articles
            if i % 10 == 0:
                await self._log(
                    f"Progress: {i}/{total} URLs, "
                    f"{self.stats.articles_parsed} parsed"
                )

            await asyncio.sleep(self.delay)

        await self._log(
            f"Phase 2 done: {self.stats.articles_parsed} articles parsed "
            f"from {self.stats.urls_fetched} fetched URLs"
        )
        return articles
