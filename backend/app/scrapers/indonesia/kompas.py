import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import BaseScraper, RawArticle


class KompasScraper(BaseScraper):
    SOURCE = "kompas"
    SOURCE_DISPLAY = "Kompas.com (English)"
    COUNTRY = "ID"
    BASE_URL = "https://english.kompas.com"
    SECTIONS = [
        "/money",
        "/national",
        "/global",
        "/tech",
        "/lifestyle",
    ]

    # Map section path to human-readable category
    SECTION_CATEGORIES = {
        "/money": "Economy & Business",
        "/national": "National",
        "/global": "World",
        "/tech": "Technology",
        "/lifestyle": "Lifestyle",
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
                if re.search(r"/read/\d{4}/\d{2}/\d{2}/\d+/", href):
                    urls.add(urljoin(self.BASE_URL, href))
        return list(urls)

    def _detect_category(self, url: str) -> str | None:
        for path, cat in self.SECTION_CATEGORIES.items():
            if path.strip("/") in url:
                return cat
        return None

    def parse_article(self, url: str, html: str) -> RawArticle | None:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one("h1.read__title")
        if not title_el:
            title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        body_el = soup.select_one("div.read__content")
        if not body_el:
            body_el = soup.select_one("article")
        body = body_el.get_text(separator="\n", strip=True) if body_el else ""

        pub_date = None
        date_el = soup.select_one("div.read__time")
        if date_el:
            date_text = date_el.get_text(strip=True)
            match = re.search(r"(\d{2}/\d{2}/\d{4})", date_text)
            if match:
                try:
                    pub_date = datetime.strptime(match.group(1), "%d/%m/%Y")
                except ValueError:
                    pass

        if not title or not body:
            return None

        return RawArticle(
            url=url,
            title=title,
            body=body,
            published_date=pub_date,
            source=self.SOURCE,
            source_display=self.SOURCE_DISPLAY,
            country=self.COUNTRY,
            category=self._detect_category(url),
        )
