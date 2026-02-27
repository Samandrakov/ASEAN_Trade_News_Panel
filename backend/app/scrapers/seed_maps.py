import json
import logging

from sqlalchemy import select

from ..database import async_session
from ..models.scrape_map import ScrapeMap

logger = logging.getLogger(__name__)

SEED_MAPS: list[dict] = [
    # ===== INDONESIA =====
    {
        "_id": "jakarta_post",
        "startUrls": [
            "https://www.thejakartapost.com/news",
            "https://www.thejakartapost.com/business",
            "https://www.thejakartapost.com/world",
            "https://www.thejakartapost.com/southeast-asia",
            "https://www.thejakartapost.com/academia",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.tjp-title--single, h1.tjp-title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div[class*='tjp-article'], div.detailText, div.postContent, p",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "ID",
            "source_display": "The Jakarta Post",
            "url_filter_pattern": "/.+/\\d{4}/\\d{2}/\\d{2}/.+",
            "date_source": "url",
            "date_url_pattern": "/(\\d{4})/(\\d{2})/(\\d{2})/",
            "date_selector_formats": [],
            "category_mapping": {
                "https://www.thejakartapost.com/news": "National",
                "https://www.thejakartapost.com/business": "Business",
                "https://www.thejakartapost.com/world": "World",
                "https://www.thejakartapost.com/southeast-asia": "Southeast Asia",
                "https://www.thejakartapost.com/academia": "Academia & Research",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
                "a.author-name",
                "span.byline",
            ],
        },
    },
    {
        "_id": "kompas",
        "startUrls": [
            "https://english.kompas.com/money",
            "https://english.kompas.com/national",
            "https://english.kompas.com/global",
            "https://english.kompas.com/tech",
            "https://english.kompas.com/lifestyle",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.read__title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.read__content, article",
                "parentSelectors": ["1"],
            },
            {
                "id": "published_date",
                "type": "SelectorText",
                "uuid": "4",
                "multiple": False,
                "selector": "div.read__time",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "ID",
            "source_display": "Kompas.com (English)",
            "url_filter_pattern": "/read/\\d{4}/\\d{2}/\\d{2}/\\d+/",
            "date_source": "selector",
            "date_selector_formats": ["%d/%m/%Y"],
            "category_mapping": {
                "https://english.kompas.com/money": "Economy & Business",
                "https://english.kompas.com/national": "National",
                "https://english.kompas.com/global": "World",
                "https://english.kompas.com/tech": "Technology",
                "https://english.kompas.com/lifestyle": "Lifestyle",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    {
        "_id": "antara",
        "startUrls": [
            "https://en.antaranews.com/news",
            "https://en.antaranews.com/economy",
            "https://en.antaranews.com/politics",
            "https://en.antaranews.com/national",
            "https://en.antaranews.com/world",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.post-title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.post-content, article",
                "parentSelectors": ["1"],
            },
            {
                "id": "published_date",
                "type": "SelectorText",
                "uuid": "4",
                "multiple": False,
                "selector": "meta[property='article:published_time'], span.post-date, time",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "ID",
            "source_display": "Antara News",
            "url_filter_pattern": "/news/\\d+/",
            "date_source": "selector",
            "date_selector_formats": [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
                "%d %B %Y",
            ],
            "category_mapping": {
                "https://en.antaranews.com/news": "General",
                "https://en.antaranews.com/economy": "Economy",
                "https://en.antaranews.com/politics": "Politics",
                "https://en.antaranews.com/national": "National",
                "https://en.antaranews.com/world": "World",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    # ===== VIETNAM =====
    {
        "_id": "vnexpress",
        "startUrls": [
            "https://e.vnexpress.net/news/business",
            "https://e.vnexpress.net/news/economy",
            "https://e.vnexpress.net/news/industries",
            "https://e.vnexpress.net/news/news",
            "https://e.vnexpress.net/news/perspectives",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.title_post, h1.title-detail, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "article.fck_detail, div.fck_detail, article",
                "parentSelectors": ["1"],
            },
            {
                "id": "published_date",
                "type": "SelectorText",
                "uuid": "4",
                "multiple": False,
                "selector": "span.date",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "VN",
            "source_display": "VnExpress International",
            "url_filter_pattern": "/news/.+\\d+\\.html",
            "date_source": "selector",
            "date_selector_formats": ["%B %d, %Y"],
            "category_mapping": {
                "https://e.vnexpress.net/news/business": "Business",
                "https://e.vnexpress.net/news/economy": "Economy",
                "https://e.vnexpress.net/news/industries": "Industries",
                "https://e.vnexpress.net/news/news": "General",
                "https://e.vnexpress.net/news/perspectives": "Analysis & Opinion",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    {
        "_id": "vietnam_news",
        "startUrls": [
            "https://vietnamnews.vn/economy",
            "https://vietnamnews.vn/politics-laws",
            "https://vietnamnews.vn/society",
            "https://vietnamnews.vn/environment",
            "https://vietnamnews.vn/oda-fdi",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.article-title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.article-body, article",
                "parentSelectors": ["1"],
            },
            {
                "id": "published_date",
                "type": "SelectorText",
                "uuid": "4",
                "multiple": False,
                "selector": "span.article-date, time",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "VN",
            "source_display": "Vietnam News",
            "url_filter_pattern": "/\\d+/.+\\.html",
            "date_source": "selector",
            "date_selector_formats": [
                "%Y-%m-%dT%H:%M:%S",
                "%B %d, %Y",
                "%d/%m/%Y",
            ],
            "category_mapping": {
                "https://vietnamnews.vn/economy": "Economy",
                "https://vietnamnews.vn/politics-laws": "Politics & Law",
                "https://vietnamnews.vn/society": "Society",
                "https://vietnamnews.vn/environment": "Environment",
                "https://vietnamnews.vn/oda-fdi": "ODA & FDI",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    {
        "_id": "tuoitre",
        "startUrls": [
            "https://tuoitrenews.vn/news/business",
            "https://tuoitrenews.vn/news/politics",
            "https://tuoitrenews.vn/news/society",
            "https://tuoitrenews.vn/news/education",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.article-title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.content-detail, article",
                "parentSelectors": ["1"],
            },
            {
                "id": "published_date",
                "type": "SelectorText",
                "uuid": "4",
                "multiple": False,
                "selector": "div.date-time, time",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "VN",
            "source_display": "Tuoi Tre News",
            "url_filter_pattern": "/news/.+\\d+\\.htm",
            "date_source": "selector",
            "date_selector_formats": [
                "%Y-%m-%dT%H:%M:%S",
                "%B %d, %Y",
                "%b %d, %Y",
            ],
            "category_mapping": {
                "https://tuoitrenews.vn/news/business": "Business",
                "https://tuoitrenews.vn/news/politics": "Politics",
                "https://tuoitrenews.vn/news/society": "Society",
                "https://tuoitrenews.vn/news/education": "Education",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    # ===== MALAYSIA =====
    {
        "_id": "thestar",
        "startUrls": [
            "https://www.thestar.com.my/business",
            "https://www.thestar.com.my/news/nation",
            "https://www.thestar.com.my/news/regional",
            "https://www.thestar.com.my/aseanplus",
            "https://www.thestar.com.my/tech",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.headline, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.story-body, article",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "MY",
            "source_display": "The Star",
            "url_filter_pattern": "/(business|news|aseanplus|tech)/.+/\\d{4}/\\d{2}/\\d{2}/",
            "date_source": "url",
            "date_url_pattern": "/(\\d{4})/(\\d{2})/(\\d{2})/",
            "date_selector_formats": [],
            "category_mapping": {
                "https://www.thestar.com.my/business": "Business",
                "https://www.thestar.com.my/news/nation": "National",
                "https://www.thestar.com.my/news/regional": "Regional",
                "https://www.thestar.com.my/aseanplus": "ASEAN+",
                "https://www.thestar.com.my/tech": "Technology",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    {
        "_id": "malaymail",
        "startUrls": [
            "https://www.malaymail.com/news/malaysia",
            "https://www.malaymail.com/news/money",
            "https://www.malaymail.com/news/world",
            "https://www.malaymail.com/news/tech-gadgets",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.article-title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.article-body, article",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "MY",
            "source_display": "Malay Mail",
            "url_filter_pattern": "/news/.+/\\d{4}/\\d{2}/\\d{2}/",
            "date_source": "url",
            "date_url_pattern": "/(\\d{4})/(\\d{2})/(\\d{2})/",
            "date_selector_formats": [],
            "category_mapping": {
                "https://www.malaymail.com/news/malaysia": "National",
                "https://www.malaymail.com/news/money": "Economy & Business",
                "https://www.malaymail.com/news/world": "World",
                "https://www.malaymail.com/news/tech-gadgets": "Technology",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
    {
        "_id": "bernama",
        "startUrls": [
            "https://www.bernama.com/en/general/",
            "https://www.bernama.com/en/business/",
            "https://www.bernama.com/en/world/",
            "https://www.bernama.com/en/politics/",
            "https://www.bernama.com/en/sports/",
        ],
        "sitemapSpecificationVersion": 1,
        "rootSelector": {"id": "_root", "uuid": "0"},
        "selectors": [
            {
                "id": "article_links",
                "type": "SelectorLink",
                "uuid": "1",
                "multiple": True,
                "selector": "a[href]",
                "parentSelectors": ["0"],
                "extractAttribute": "href",
            },
            {
                "id": "title",
                "type": "SelectorText",
                "uuid": "2",
                "multiple": False,
                "selector": "h1.title, h1",
                "parentSelectors": ["1"],
            },
            {
                "id": "body",
                "type": "SelectorText",
                "uuid": "3",
                "multiple": True,
                "selector": "div.news-content, div.col-sm-8 p, main p",
                "parentSelectors": ["1"],
            },
            {
                "id": "published_date",
                "type": "SelectorText",
                "uuid": "4",
                "multiple": False,
                "selector": "div.date, span.date",
                "parentSelectors": ["1"],
            },
        ],
        "_meta": {
            "country": "MY",
            "source_display": "Bernama",
            "url_filter_pattern": "news\\.php.*id=",
            "date_source": "selector",
            "date_selector_formats": ["%d/%m/%Y", "%B %d, %Y", "%d %B %Y"],
            "category_mapping": {
                "https://www.bernama.com/en/general/": "General",
                "https://www.bernama.com/en/business/": "Business",
                "https://www.bernama.com/en/world/": "World",
                "https://www.bernama.com/en/politics/": "Politics",
                "https://www.bernama.com/en/sports/": "Sports",
            },
            "min_body_length": 200,
            "author_selectors": [
                "meta[name='author']",
                "span.author",
                "div.author",
            ],
        },
    },
]

# ===== RSS SEED MAPS for additional ASEAN countries =====
RSS_SEED_MAPS: list[dict] = [
    # ===== SINGAPORE =====
    {
        "_id": "cna_sg",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511",
            "country": "SG",
            "source_display": "Channel NewsAsia",
            "category": "Business",
        },
    },
    {
        "_id": "today_sg",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.todayonline.com/feed",
            "country": "SG",
            "source_display": "Today Online",
            "category": "General",
        },
    },
    # ===== THAILAND =====
    {
        "_id": "bangkokpost",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.bangkokpost.com/rss/data/topstories.xml",
            "country": "TH",
            "source_display": "Bangkok Post",
            "category": "Business",
        },
    },
    {
        "_id": "nation_thailand",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.nationthailand.com/rss",
            "country": "TH",
            "source_display": "The Nation Thailand",
            "category": "General",
        },
    },
    # ===== PHILIPPINES =====
    {
        "_id": "bworld",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.bworldonline.com/feed/",
            "country": "PH",
            "source_display": "BusinessWorld",
            "category": "Business",
        },
    },
    {
        "_id": "inquirer_biz",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://business.inquirer.net/feed",
            "country": "PH",
            "source_display": "Philippine Daily Inquirer Business",
            "category": "Business",
        },
    },
    # ===== MYANMAR =====
    {
        "_id": "irrawaddy",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.irrawaddy.com/feed",
            "country": "MM",
            "source_display": "The Irrawaddy",
            "category": "General",
        },
    },
    # ===== CAMBODIA =====
    {
        "_id": "khmertimes",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.khmertimeskh.com/feed/",
            "country": "KH",
            "source_display": "Khmer Times",
            "category": "General",
        },
    },
    # ===== LAOS =====
    {
        "_id": "vientianetimes",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://www.vientianetimes.org.la/feed/",
            "country": "LA",
            "source_display": "Vientiane Times",
            "category": "General",
        },
    },
    # ===== BRUNEI =====
    {
        "_id": "borneobulletin",
        "_type": "rss",
        "_meta": {
            "feed_url": "https://borneobulletin.com.bn/feed/",
            "country": "BN",
            "source_display": "Borneo Bulletin",
            "category": "General",
        },
    },
]


async def seed_default_maps():
    """Insert default maps if the scrape_maps table is empty."""
    async with async_session() as db:
        result = await db.execute(select(ScrapeMap.id).limit(1))
        if result.scalar_one_or_none() is not None:
            logger.info("[seed] Scrape maps table already populated, skipping seed")
            return

        all_maps = list(SEED_MAPS) + list(RSS_SEED_MAPS)
        logger.info(f"[seed] Inserting {len(all_maps)} default scrape maps")

        for sitemap in SEED_MAPS:
            m = ScrapeMap(
                map_id=sitemap["_id"],
                name=sitemap["_meta"]["source_display"],
                country=sitemap["_meta"]["country"],
                sitemap_json=json.dumps(sitemap, ensure_ascii=False),
                feed_type="sitemap",
                active=True,
            )
            db.add(m)

        for rss_map in RSS_SEED_MAPS:
            meta = rss_map["_meta"]
            # Store RSS config as JSON (feed_url etc.) inside sitemap_json for storage consistency
            m = ScrapeMap(
                map_id=rss_map["_id"],
                name=meta["source_display"],
                country=meta["country"],
                sitemap_json=json.dumps(rss_map, ensure_ascii=False),
                feed_type="rss",
                active=True,
            )
            db.add(m)

        await db.commit()
        logger.info("[seed] Default maps inserted successfully")
