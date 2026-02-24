"""
Universal scraper tests.

Run offline tests (no network):
    pytest backend/tests/test_scrapers.py -v

Run live integration tests (hits real sites):
    pytest backend/tests/test_scrapers.py -v --live
"""

import asyncio
from datetime import datetime

import pytest

from app.scrapers.base import BaseScraper, RawArticle, ScrapeStats
from app.scrapers.registry import SCRAPER_REGISTRY

ALL_SCRAPER_NAMES = list(SCRAPER_REGISTRY.keys())


# ─── Offline unit tests (no network) ────────────────────────────────────────


class TestScraperRegistry:
    """Verify that the registry is sane and all scrapers are properly configured."""

    def test_registry_not_empty(self):
        assert len(SCRAPER_REGISTRY) >= 9

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    def test_scraper_is_subclass(self, name):
        cls = SCRAPER_REGISTRY[name]
        assert issubclass(cls, BaseScraper)

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    def test_scraper_has_required_attrs(self, name):
        cls = SCRAPER_REGISTRY[name]
        assert cls.SOURCE, f"{name}: SOURCE is empty"
        assert cls.SOURCE_DISPLAY, f"{name}: SOURCE_DISPLAY is empty"
        assert cls.COUNTRY in ("ID", "VN", "MY"), f"{name}: COUNTRY={cls.COUNTRY} not in ID/VN/MY"
        assert cls.BASE_URL.startswith("http"), f"{name}: invalid BASE_URL"
        assert len(cls.SECTIONS) >= 1, f"{name}: no SECTIONS defined"

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    def test_scraper_source_matches_key(self, name):
        cls = SCRAPER_REGISTRY[name]
        assert cls.SOURCE == name, f"Registry key '{name}' != cls.SOURCE '{cls.SOURCE}'"

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    def test_scraper_instantiates(self, name):
        cls = SCRAPER_REGISTRY[name]
        scraper = cls(delay=0)
        assert isinstance(scraper.stats, ScrapeStats)
        assert scraper.stats.source == name
        asyncio.get_event_loop().run_until_complete(scraper.close())


class TestRawArticle:
    def test_create_minimal(self):
        art = RawArticle(
            url="https://example.com/1",
            title="Test",
            body="Body text here",
            published_date=None,
            source="test",
            source_display="Test",
            country="ID",
        )
        assert art.category is None
        assert art.author is None

    def test_create_full(self):
        art = RawArticle(
            url="https://example.com/2",
            title="Full Article",
            body="Long body text",
            published_date=datetime(2024, 1, 15),
            source="test",
            source_display="Test Source",
            country="VN",
            category="Economy",
            author="John Doe",
        )
        assert art.author == "John Doe"
        assert art.category == "Economy"


class TestScrapeStats:
    def test_default_values(self):
        stats = ScrapeStats(source="test")
        assert stats.sections_attempted == 0
        assert stats.urls_found == 0
        assert stats.articles_parsed == 0

    def test_summary_format(self):
        stats = ScrapeStats(source="test_source")
        stats.sections_attempted = 3
        stats.sections_successful = 2
        stats.urls_found = 10
        stats.urls_fetched = 8
        stats.articles_parsed = 6
        stats.articles_skipped_short = 1
        stats.articles_skipped_empty = 1
        report = stats.summary()
        assert "test_source" in report
        assert "Sections: 2/3 OK" in report
        assert "URLs found: 10" in report
        assert "Articles parsed: 6" in report


class TestParseArticleOffline:
    """Test parse_article with synthetic HTML for each scraper."""

    SAMPLE_HTML = {
        "jakarta_post": """
        <html><body>
            <h1>Indonesia GDP grows 5.2% in Q3</h1>
            <div class="detailText">
                <p>Indonesia's economy posted a healthy growth of 5.2 percent year-on-year
                in the third quarter of 2024, driven by strong domestic consumption and
                investment. The statistics bureau said that the manufacturing sector
                contributed the most to economic expansion. Exports also showed resilience
                despite global headwinds affecting trade partners in the region.</p>
            </div>
        </body></html>
        """,
        "kompas": """
        <html><body>
            <h1 class="read__title">Bank Indonesia holds rate steady at 6%</h1>
            <div class="read__time">12/01/2024, 14:30 WIB</div>
            <div class="read__content">
                <p>Bank Indonesia decided to keep its benchmark interest rate unchanged at
                6 percent on Thursday, as the central bank seeks to balance between
                supporting the rupiah currency and ensuring economic growth momentum.
                Governor Perry Warjiyo said inflation remains under control and within
                the target corridor for the year ahead.</p>
            </div>
        </body></html>
        """,
        "antara": """
        <html><body>
            <h1 class="post-title">Indonesia signs trade deal with Australia</h1>
            <span class="post-date">2024-03-15</span>
            <div class="post-content">
                <p>Indonesia and Australia have signed a comprehensive trade agreement aimed
                at boosting bilateral trade by 30 percent over the next five years. The deal
                covers tariff reductions on agricultural products, minerals, and
                manufactured goods. Both nations expressed optimism about strengthening
                economic ties in the Indo-Pacific region.</p>
            </div>
        </body></html>
        """,
        "vnexpress": """
        <html><body>
            <h1 class="title-detail">Vietnam FDI inflows surge 20% in 2024</h1>
            <span class="date">January 10, 2024, 09:00</span>
            <article class="fck_detail">
                <p>Vietnam attracted over $23 billion in foreign direct investment in 2024,
                marking a 20 percent increase compared to the previous year. The electronics
                and semiconductor sectors accounted for the largest share of new projects.
                South Korea, Japan, and Singapore remained the top investors, while several
                new Chinese manufacturers also expanded their operations in the country.</p>
            </article>
        </body></html>
        """,
        "vietnam_news": """
        <html><body>
            <h1 class="article-title">Vietnam-Russia trade reaches new milestone</h1>
            <span class="article-date">2024-06-20T08:00:00</span>
            <div class="article-body">
                <p>Bilateral trade between Vietnam and Russia reached a record $7.5 billion
                in the first half of 2024, according to the General Department of Customs.
                Energy products, agricultural goods and machinery dominated the trade flow.
                Officials from both countries discussed plans to increase trade volume to
                $10 billion by 2025, with a focus on digital economy cooperation.</p>
            </div>
        </body></html>
        """,
        "tuoitre": """
        <html><body>
            <h1 class="article-title">Ho Chi Minh City metro opens first line</h1>
            <div class="date-time"><time datetime="2024-08-15T07:30:00">Aug 15, 2024</time></div>
            <div class="content-detail">
                <p>Ho Chi Minh City officially opened its first metro line on Thursday,
                connecting Ben Thanh market in the city center to Suoi Tien theme park
                in the eastern suburbs. The 19.7-kilometer line has 14 stations and is
                expected to serve 150,000 passengers daily. The project was built with
                Japanese ODA funding over a period of twelve years.</p>
            </div>
        </body></html>
        """,
        "thestar": """
        <html><body>
            <h1 class="headline">Malaysia palm oil exports hit record high</h1>
            <div class="story-body">
                <p>Malaysia's palm oil exports reached a record 18.5 million tonnes in 2024,
                driven by strong demand from India and China. The Malaysian Palm Oil Board
                reported that revenue from palm oil exports rose 15 percent to RM95 billion.
                Industry experts attributed the growth to competitive pricing and improved
                sustainability practices that attracted more buyers from Europe.</p>
            </div>
        </body></html>
        """,
        "malaymail": """
        <html><body>
            <h1 class="article-title">Ringgit strengthens against US dollar</h1>
            <div class="article-body">
                <p>The ringgit opened higher against the US dollar on Monday, supported by
                strong economic data and foreign fund inflows into the Malaysian bond market.
                Bank Negara Malaysia's latest report showed that the economy grew 5.8 percent
                in the fourth quarter, beating analyst estimates. The central bank signaled
                a steady monetary policy stance for the near term.</p>
            </div>
        </body></html>
        """,
        "bernama": """
        <html><body>
            <h1 class="title">Malaysia to host ASEAN economic forum in 2025</h1>
            <div class="date">15/03/2024</div>
            <div class="news-content">
                <p>Malaysia will host the ASEAN Economic Forum in Kuala Lumpur next year,
                bringing together finance ministers and central bank governors from all
                ten member states. The forum will focus on digital trade facilitation,
                supply chain resilience, and green financing initiatives. Prime Minister
                Anwar Ibrahim said the event underscores Malaysia's commitment to ASEAN
                economic integration and regional prosperity.</p>
            </div>
        </body></html>
        """,
    }

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    def test_parse_article_returns_raw_article(self, name):
        cls = SCRAPER_REGISTRY[name]
        scraper = cls(delay=0)
        html = self.SAMPLE_HTML.get(name)
        assert html is not None, f"No sample HTML defined for {name}"

        # Build a plausible test URL for the scraper
        test_urls = {
            "jakarta_post": "https://www.thejakartapost.com/business/2024/01/15/test-article",
            "kompas": "https://english.kompas.com/money/read/2024/01/12/123456/test",
            "antara": "https://en.antaranews.com/news/12345/test-article",
            "vnexpress": "https://e.vnexpress.net/news/business/test-123456.html",
            "vietnam_news": "https://vietnamnews.vn/economy/12345/test.html",
            "tuoitre": "https://tuoitrenews.vn/news/business/test-12345.htm",
            "thestar": "https://www.thestar.com.my/business/story/2024/03/15/test",
            "malaymail": "https://www.malaymail.com/news/money/2024/03/15/test",
            "bernama": "https://www.bernama.com/en/news.php?id=12345",
        }

        url = test_urls[name]
        article = scraper.parse_article(url, html)

        assert article is not None, f"{name}: parse_article returned None"
        assert isinstance(article, RawArticle)
        assert article.title, f"{name}: empty title"
        assert len(article.body) > 100, f"{name}: body too short ({len(article.body)} chars)"
        assert article.source == name
        assert article.country in ("ID", "VN", "MY")

        asyncio.get_event_loop().run_until_complete(scraper.close())

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    def test_parse_empty_html_returns_none(self, name):
        cls = SCRAPER_REGISTRY[name]
        scraper = cls(delay=0)
        result = scraper.parse_article("https://example.com/nothing", "<html><body></body></html>")
        assert result is None, f"{name}: should return None for empty HTML"
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_jakarta_post_extracts_date_from_url(self):
        scraper = SCRAPER_REGISTRY["jakarta_post"](delay=0)
        html = self.SAMPLE_HTML["jakarta_post"]
        article = scraper.parse_article(
            "https://www.thejakartapost.com/business/2024/03/20/test",
            html,
        )
        assert article is not None
        assert article.published_date == datetime(2024, 3, 20)
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_jakarta_post_category_detection(self):
        scraper = SCRAPER_REGISTRY["jakarta_post"](delay=0)
        html = self.SAMPLE_HTML["jakarta_post"]
        article = scraper.parse_article(
            "https://www.thejakartapost.com/business/2024/01/15/test",
            html,
        )
        assert article is not None
        assert article.category == "Business"
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_kompas_extracts_date(self):
        scraper = SCRAPER_REGISTRY["kompas"](delay=0)
        html = self.SAMPLE_HTML["kompas"]
        article = scraper.parse_article(
            "https://english.kompas.com/money/read/2024/01/12/123456/test",
            html,
        )
        assert article is not None
        assert article.published_date == datetime(2024, 1, 12)
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_antara_extracts_date(self):
        scraper = SCRAPER_REGISTRY["antara"](delay=0)
        html = self.SAMPLE_HTML["antara"]
        article = scraper.parse_article(
            "https://en.antaranews.com/news/12345/test",
            html,
        )
        assert article is not None
        assert article.published_date == datetime(2024, 3, 15)
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_bernama_extracts_date(self):
        scraper = SCRAPER_REGISTRY["bernama"](delay=0)
        html = self.SAMPLE_HTML["bernama"]
        article = scraper.parse_article(
            "https://www.bernama.com/en/news.php?id=12345",
            html,
        )
        assert article is not None
        assert article.published_date == datetime(2024, 3, 15)
        asyncio.get_event_loop().run_until_complete(scraper.close())


class TestExtractAuthor:
    def test_meta_author(self):
        scraper = SCRAPER_REGISTRY["jakarta_post"](delay=0)
        html = '<html><head><meta name="author" content="Jane Reporter"></head><body></body></html>'
        assert scraper._extract_author(html) == "Jane Reporter"
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_span_author(self):
        scraper = SCRAPER_REGISTRY["jakarta_post"](delay=0)
        html = '<html><body><span class="author">John Writer</span></body></html>'
        assert scraper._extract_author(html) == "John Writer"
        asyncio.get_event_loop().run_until_complete(scraper.close())

    def test_no_author(self):
        scraper = SCRAPER_REGISTRY["jakarta_post"](delay=0)
        html = "<html><body><p>No author info</p></body></html>"
        assert scraper._extract_author(html) is None
        asyncio.get_event_loop().run_until_complete(scraper.close())


# ─── Live integration tests (require --live flag) ───────────────────────────


@pytest.mark.live
class TestScrapersLive:
    """Actually hit real websites. Run with: pytest --live -v -k TestScrapersLive"""

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    @pytest.mark.asyncio
    async def test_fetch_article_urls(self, name):
        """Each scraper should find at least 1 URL from its sections."""
        cls = SCRAPER_REGISTRY[name]
        scraper = cls(delay=0.5)
        try:
            urls = await scraper.fetch_article_urls()
            print(f"\n[{name}] Found {len(urls)} URLs")
            if urls:
                print(f"  Sample: {urls[0]}")
            assert len(urls) > 0, f"{name}: no URLs found — site may have changed structure"
        finally:
            await scraper.close()

    @pytest.mark.parametrize("name", ALL_SCRAPER_NAMES)
    @pytest.mark.asyncio
    async def test_scrape_at_least_one(self, name):
        """Each scraper should successfully scrape at least 1 article end-to-end."""
        cls = SCRAPER_REGISTRY[name]
        scraper = cls(delay=0.5)
        try:
            urls = await scraper.fetch_article_urls()
            if not urls:
                pytest.skip(f"{name}: no URLs found, cannot test parsing")

            # Try first 5 URLs to find at least one parseable article
            parsed = None
            for url in urls[:5]:
                html = await scraper.fetch_page(url)
                if not html:
                    continue
                result = scraper.parse_article(url, html)
                if result and len(result.body) >= 200:
                    parsed = result
                    break

            assert parsed is not None, (
                f"{name}: could not parse any article from first 5 URLs — "
                f"site structure may have changed"
            )
            print(f"\n[{name}] Parsed: \"{parsed.title[:60]}\" ({len(parsed.body)} chars)")
            assert parsed.source == name
            assert parsed.country in ("ID", "VN", "MY")
        finally:
            await scraper.close()
