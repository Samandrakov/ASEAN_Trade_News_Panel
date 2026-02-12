import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import BaseScraper, RawArticle


class TheStarScraper(BaseScraper):
    SOURCE = "thestar"
    SOURCE_DISPLAY = "The Star"
    COUNTRY = "MY"
    BASE_URL = "https://www.thestar.com.my"
    SECTIONS = [
        "/business",
        "/news/nation",
        "/news/regional",
        "/aseanplus",
        "/tech",
    ]

    SECTION_CATEGORIES = {
        "/business": "Business",
        "/news/nation": "National",
        "/news/regional": "Regional",
        "/aseanplus": "ASEAN+",
        "/tech": "Technology",
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
                if re.search(r"/(business|news|aseanplus|tech)/.+/\d{4}/\d{2}/\d{2}/", href):
                    urls.add(urljoin(self.BASE_URL, href))
        return list(urls)

    def parse_article(self, url: str, html: str) -> RawArticle | None:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one("h1.headline") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        body_el = soup.select_one("div.story-body") or soup.select_one("article")
        body = body_el.get_text(separator="\n", strip=True) if body_el else ""

        pub_date = None
        match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if match:
            try:
                pub_date = datetime(
                    int(match.group(1)), int(match.group(2)), int(match.group(3))
                )
            except ValueError:
                pass

        if not title or not body:
            return None

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
