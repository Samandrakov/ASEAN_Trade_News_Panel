import logging
from datetime import datetime

from sqlalchemy import select

from ..config import settings
from ..database import async_session
from ..models.article import Article
from ..models.scrape_log import ScrapeRun
from ..models.tag import ArticleTag
from ..scrapers.base import RawArticle
from ..scrapers.registry import SCRAPER_REGISTRY
from ..services.llm_tagger import classify_article

logger = logging.getLogger(__name__)


async def _store_articles(articles: list[RawArticle]) -> tuple[int, int]:
    """Store articles in DB, skip duplicates. Returns (found, new)."""
    new_count = 0
    async with async_session() as db:
        for raw in articles:
            exists = await db.execute(
                select(Article.id).where(Article.url == raw.url)
            )
            if exists.scalar_one_or_none() is not None:
                continue

            word_count = len(raw.body.split()) if raw.body else 0

            article = Article(
                url=raw.url,
                title=raw.title,
                body=raw.body,
                source=raw.source,
                source_display=raw.source_display,
                country=raw.country,
                category=raw.category,
                author=raw.author,
                word_count=word_count,
                published_date=raw.published_date,
                tagged=False,
            )
            db.add(article)
            new_count += 1
            logger.info(
                f"  NEW: \"{raw.title[:70]}\" | {raw.source_display} | "
                f"{raw.country} | {raw.category or 'N/A'} | "
                f"{word_count} words | {raw.published_date or 'no date'}"
            )

        await db.commit()
    return len(articles), new_count


async def _tag_untagged_articles():
    """Find untagged articles and classify them via LLM."""
    async with async_session() as db:
        batch_num = 0
        while True:
            result = await db.execute(
                select(Article).where(Article.tagged == False).limit(10)  # noqa: E712
            )
            articles = result.scalars().all()
            if not articles:
                break

            batch_num += 1
            logger.info(f"[tagger] Batch #{batch_num}: tagging {len(articles)} articles")

            for article in articles:
                logger.info(f"[tagger] Classifying: \"{article.title[:60]}\" (id={article.id})")
                classification = await classify_article(article.title, article.body)
                if classification is None:
                    logger.warning(f"[tagger] No classification returned for id={article.id}")
                    article.tagged = True
                    continue

                # Store country mentions
                countries = classification.get("country_mentions", [])
                for country in countries:
                    db.add(
                        ArticleTag(
                            article_id=article.id,
                            tag_type="country_mention",
                            tag_value=country,
                        )
                    )

                # Store topics
                topics = classification.get("topics", [])
                for topic in topics:
                    db.add(
                        ArticleTag(
                            article_id=article.id,
                            tag_type="topic",
                            tag_value=topic,
                        )
                    )

                # Store sectors
                sectors = classification.get("sectors", [])
                for sector in sectors:
                    db.add(
                        ArticleTag(
                            article_id=article.id,
                            tag_type="sector",
                            tag_value=sector,
                        )
                    )

                # Store sentiment
                sentiment = classification.get("sentiment")
                if sentiment:
                    db.add(
                        ArticleTag(
                            article_id=article.id,
                            tag_type="sentiment",
                            tag_value=sentiment,
                        )
                    )

                # Store LLM summary
                summary = classification.get("summary")
                if summary:
                    article.summary = summary

                article.tagged = True

                tag_summary = (
                    f"countries={countries}, topics={topics}, "
                    f"sectors={sectors}, sentiment={sentiment}"
                )
                logger.info(f"[tagger] Tagged id={article.id}: {tag_summary}")

            await db.commit()


async def run_pipeline(sources: list[str] | None = None):
    """Run the full ETL pipeline: scrape -> store -> tag."""
    source_list = sources or list(SCRAPER_REGISTRY.keys())
    total_found = 0
    total_new = 0

    logger.info("=" * 60)
    logger.info(f"PIPELINE START | Sources: {', '.join(source_list)}")
    logger.info("=" * 60)

    for source_name in source_list:
        scraper_cls = SCRAPER_REGISTRY.get(source_name)
        if not scraper_cls:
            logger.warning(f"Unknown scraper: {source_name}, skipping")
            continue

        scraper = scraper_cls(delay=settings.scrape_delay_seconds)
        run = ScrapeRun(
            source=source_name,
            started_at=datetime.utcnow(),
            status="running",
        )

        async with async_session() as db:
            db.add(run)
            await db.commit()
            await db.refresh(run)
            run_id = run.id

        try:
            raw_articles = await scraper.scrape()
            found, new = await _store_articles(raw_articles)
            total_found += found
            total_new += new

            async with async_session() as db:
                run = await db.get(ScrapeRun, run_id)
                if run:
                    run.finished_at = datetime.utcnow()
                    run.articles_found = found
                    run.articles_new = new
                    run.status = "success"
                    await db.commit()

            logger.info(
                f"[{source_name}] DONE: {found} found, {new} new, "
                f"{found - new} duplicates skipped"
            )

        except Exception as e:
            logger.error(f"[{source_name}] PIPELINE ERROR: {e}", exc_info=True)
            async with async_session() as db:
                run = await db.get(ScrapeRun, run_id)
                if run:
                    run.finished_at = datetime.utcnow()
                    run.status = "failed"
                    run.error_message = str(e)
                    await db.commit()
        finally:
            await scraper.close()

    logger.info("-" * 60)
    logger.info(f"SCRAPING COMPLETE | Total: {total_found} found, {total_new} new")
    logger.info("-" * 60)

    # Tag all untagged articles
    logger.info("[tagger] Starting LLM tagging of new articles...")
    await _tag_untagged_articles()

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
