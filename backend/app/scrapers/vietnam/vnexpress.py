import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import BaseScraper, RawArticle


class VnExpressScraper(BaseScraper):
    SOURCE = "vnexpress"
    SOURCE_DISPLAY = "VnExpress International"
    COUNTRY = "VN"
    BASE_URL = "https://e.vnexpress.net"
    SECTIONS = [
        "/news/business",
        "/news/economy",
        "/news/industries",
        "/news/news",
        "/news/perspectives",
    ]

    SECTION_CATEGORIES = {
        "/news/business": "Business",
        "/news/economy": "Economy",
        "/news/industries": "Industries",
        "/news/news": "General",
        "/news/perspectives": "Analysis & Opinion",
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
                if re.search(r"/news/.+\d+\.html", href):
                    urls.add(urljoin(self.BASE_URL, href))
        return list(urls)

    def parse_article(self, url: str, html: str) -> RawArticle | None:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one("h1.title-detail") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        body_el = soup.select_one("article.fck_detail") or soup.select_one(
            "div.fck_detail"
        )
        if not body_el:
            body_el = soup.find("article")
        body = body_el.get_text(separator="\n", strip=True) if body_el else ""

        pub_date = None
        date_el = soup.select_one("span.date")
        if date_el:
            date_text = date_el.get_text(strip=True)
            match = re.search(r"(\w+ \d+, \d{4})", date_text)
            if match:
                try:
                    pub_date = datetime.strptime(match.group(1), "%B %d, %Y")
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
