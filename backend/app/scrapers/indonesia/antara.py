import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import BaseScraper, RawArticle


class AntaraScraper(BaseScraper):
    SOURCE = "antara"
    SOURCE_DISPLAY = "Antara News"
    COUNTRY = "ID"
    BASE_URL = "https://en.antaranews.com"
    SECTIONS = [
        "/news",
        "/economy",
        "/politics",
        "/national",
        "/world",
    ]

    SECTION_CATEGORIES = {
        "/news": "General",
        "/economy": "Economy",
        "/politics": "Politics",
        "/national": "National",
        "/world": "World",
    }

    async def fetch_article_urls(self) -> list[str]:
        urls: set[str] = set()
        for section in self.SECTIONS:
            self.stats.sections_attempted += 1
            html = await self.fetch_page(f"{self.BASE_URL}{section}")
            if not html:
                self.stats.sections_failed.append(section)
                continue
            self.stats.sections_successful += 1
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if re.search(r"/news/\d+/", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url.startswith(self.BASE_URL):
                        urls.add(full_url)
        return list(urls)

    def parse_article(self, url: str, html: str) -> RawArticle | None:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one("h1.post-title") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        body_el = soup.select_one("div.post-content") or soup.select_one("article")
        body = body_el.get_text(separator="\n", strip=True) if body_el else ""

        pub_date = None
        date_el = soup.select_one("span.post-date") or soup.select_one("time")
        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y"):
                try:
                    pub_date = datetime.strptime(date_text[:19], fmt)
                    break
                except ValueError:
                    continue

        if not title or not body:
            return None

        # Detect category from URL path
        category = None
        for path, cat in self.SECTION_CATEGORIES.items():
            if path in url:
                category = cat
                break

        return RawArticle(
            url=url,
            title=title,
            body=body,
            published_date=pub_date,
            source=self.SOURCE,
            source_display=self.SOURCE_DISPLAY,
            country=self.COUNTRY,
            category=category,
        )
