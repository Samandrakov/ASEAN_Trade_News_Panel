import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import BaseScraper, RawArticle


class BernamaScraper(BaseScraper):
    SOURCE = "bernama"
    SOURCE_DISPLAY = "Bernama"
    COUNTRY = "MY"
    BASE_URL = "https://www.bernama.com/en"
    SECTIONS = [
        "/general/",
        "/business/",
        "/world/",
        "/politics/",
        "/sports/",
    ]

    SECTION_CATEGORIES = {
        "/general/": "General",
        "/business/": "Business",
        "/world/": "World",
        "/politics/": "Politics",
        "/sports/": "Sports",
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
                if "news.php" in href and "id=" in href:
                    urls.add(urljoin(self.BASE_URL + "/", href))
        return list(urls)

    def parse_article(self, url: str, html: str) -> RawArticle | None:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one("h1.title") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        body_el = soup.select_one("div.news-content") or soup.select_one(
            "div.row p"
        )
        if not body_el:
            main = soup.select_one("div.col-sm-8") or soup.select_one("main")
            if main:
                paragraphs = main.find_all("p")
                body = "\n".join(p.get_text(strip=True) for p in paragraphs)
            else:
                body = ""
        else:
            body = body_el.get_text(separator="\n", strip=True)

        pub_date = None
        date_el = soup.select_one("div.date") or soup.select_one("span.date")
        if date_el:
            date_text = date_el.get_text(strip=True)
            for fmt in ("%d/%m/%Y", "%B %d, %Y", "%d %B %Y"):
                try:
                    pub_date = datetime.strptime(date_text.strip(), fmt)
                    break
                except ValueError:
                    continue

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
            category="General",
        )
