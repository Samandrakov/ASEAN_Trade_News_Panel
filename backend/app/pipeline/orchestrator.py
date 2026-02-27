import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from ..config import settings
from ..database import async_session
from ..models.alert import Alert, AlertMatch
from ..models.article import Article
from ..models.scrape_log import ScrapeLogEntry, ScrapeRun
from ..models.tag import ArticleTag
from ..scrapers.base import RawArticle
from ..scrapers.registry import load_active_maps, load_map_by_id
from ..scrapers.rss_executor import RssExecutor
from ..scrapers.sitemap_executor import SitemapExecutor
from ..services.llm_tagger import classify_article

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-run tracking: concurrent tasks, per-run cancellation
# ---------------------------------------------------------------------------
_running_tasks: dict[int, asyncio.Task] = {}        # run_id -> Task
_cancel_events: dict[int, asyncio.Event] = {}        # run_id -> Event
_source_to_run: dict[str, int] = {}                  # source_id -> run_id (active)
_tagging_lock = asyncio.Lock()


async def _add_log(run_id: int, message: str, level: str = "INFO"):
    """Save a log entry for the given scrape run with retry on lock."""
    for attempt in range(3):
        try:
            async with async_session() as db:
                db.add(ScrapeLogEntry(
                    run_id=run_id,
                    timestamp=datetime.now(timezone.utc),
                    level=level,
                    message=message,
                ))
                await db.commit()
            return
        except Exception:
            if attempt < 2:
                await asyncio.sleep(0.5)
            else:
                logger.warning(f"Failed to write log after 3 attempts: {message[:80]}")


async def _store_articles(
    articles: list[RawArticle], run_id: int | None = None
) -> tuple[int, int]:
    """Store articles in DB in small batches. Returns (found, new)."""
    new_count = 0
    batch_size = 20

    for start in range(0, len(articles), batch_size):
        batch = articles[start : start + batch_size]
        async with async_session() as db:
            for raw in batch:
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
                    f"{raw.country} | {word_count} words"
                )

            await db.commit()

        if run_id:
            await _add_log(
                run_id,
                f"Stored batch {start // batch_size + 1}: "
                f"{new_count} new so far ({start + len(batch)}/{len(articles)} processed)"
            )

    return len(articles), new_count


async def _tag_untagged_articles():
    """Find untagged articles and classify them via LLM (serialised by lock)."""
    async with _tagging_lock:
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

                    for country in classification.get("country_mentions", []):
                        db.add(ArticleTag(
                            article_id=article.id, tag_type="country_mention", tag_value=country,
                        ))
                    for topic in classification.get("topics", []):
                        db.add(ArticleTag(
                            article_id=article.id, tag_type="topic", tag_value=topic,
                        ))
                    for sector in classification.get("sectors", []):
                        db.add(ArticleTag(
                            article_id=article.id, tag_type="sector", tag_value=sector,
                        ))
                    sentiment = classification.get("sentiment")
                    if sentiment:
                        db.add(ArticleTag(
                            article_id=article.id, tag_type="sentiment", tag_value=sentiment,
                        ))
                    summary = classification.get("summary")
                    if summary:
                        article.summary = summary

                    article.tagged = True
                    tag_summary = (
                        f"countries={classification.get('country_mentions', [])}, "
                        f"topics={classification.get('topics', [])}, "
                        f"sectors={classification.get('sectors', [])}, "
                        f"sentiment={sentiment}"
                    )
                    logger.info(f"[tagger] Tagged id={article.id}: {tag_summary}")

                await db.commit()


# ---------------------------------------------------------------------------
# Per-run control API
# ---------------------------------------------------------------------------

def is_source_running(source_id: str) -> int | None:
    """Return run_id if this source is currently being scraped, else None."""
    run_id = _source_to_run.get(source_id)
    if run_id is None:
        return None
    task = _running_tasks.get(run_id)
    if task is None or task.done():
        _source_to_run.pop(source_id, None)
        return None
    return run_id


def get_running_run_ids() -> list[int]:
    """Return list of currently running run_ids."""
    alive = []
    done_keys = []
    for run_id, task in _running_tasks.items():
        if task.done():
            done_keys.append(run_id)
        else:
            alive.append(run_id)
    for k in done_keys:
        _running_tasks.pop(k, None)
        _cancel_events.pop(k, None)
    return alive


def is_pipeline_running() -> bool:
    return len(get_running_run_ids()) > 0


async def cancel_run(run_id: int) -> bool:
    """Cancel a specific run. Returns True if cancellation was requested."""
    ev = _cancel_events.get(run_id)
    task = _running_tasks.get(run_id)
    if ev is None or task is None or task.done():
        return False
    ev.set()
    task.cancel()
    logger.info(f"Cancellation requested for run_id={run_id}")
    return True


async def cancel_all() -> int:
    """Cancel all running scrape tasks. Returns count of cancelled."""
    count = 0
    for run_id in list(_running_tasks.keys()):
        if await cancel_run(run_id):
            count += 1
    return count


async def start_source(source_id: str) -> int | None:
    """Create a ScrapeRun and start scraping a single source as an asyncio.Task.
    Returns run_id, or None if source is already running / not found."""
    # Check if already running
    existing = is_source_running(source_id)
    if existing is not None:
        logger.info(f"Source {source_id} is already running (run_id={existing}), skipping")
        return None

    # Load map
    sitemap_data = await load_map_by_id(source_id)
    if sitemap_data is None:
        logger.warning(f"Unknown source map: {source_id}")
        return None

    # Create ScrapeRun record
    run = ScrapeRun(
        source=source_id,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    async with async_session() as db:
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    # Set up cancel event and launch task
    cancel_event = asyncio.Event()
    _cancel_events[run_id] = cancel_event
    _source_to_run[source_id] = run_id

    task = asyncio.create_task(
        _run_single_source(run_id, source_id, sitemap_data, cancel_event)
    )
    _running_tasks[run_id] = task

    # Clean up tracking when done
    def _on_done(_task):
        _running_tasks.pop(run_id, None)
        _cancel_events.pop(run_id, None)
        _source_to_run.pop(source_id, None)

    task.add_done_callback(_on_done)

    logger.info(f"Started source {source_id} as run_id={run_id}")
    return run_id


async def _check_alerts(new_article_ids: list[int]) -> None:
    """Check newly stored articles against active alerts and create AlertMatch records."""
    if not settings.alert_check_enabled or not new_article_ids:
        return
    try:
        async with async_session() as db:
            alerts_result = await db.execute(
                select(Alert).where(Alert.active == True)  # noqa: E712
            )
            alerts = alerts_result.scalars().all()
            if not alerts:
                return

            articles_result = await db.execute(
                select(Article).where(Article.id.in_(new_article_ids))
            )
            articles = articles_result.scalars().all()

            for alert in alerts:
                keywords = json.loads(alert.keywords_json or "[]")
                countries = json.loads(alert.countries_json or "[]")

                for article in articles:
                    # Country filter (if specified)
                    if countries and article.country not in countries:
                        continue

                    # Keyword check (any keyword in title or body)
                    if keywords:
                        text_lower = (article.title + " " + article.body).lower()
                        if not any(kw.lower() in text_lower for kw in keywords):
                            continue

                    db.add(AlertMatch(
                        alert_id=alert.id,
                        article_id=article.id,
                        read=False,
                    ))

            await db.commit()
    except Exception as exc:
        logger.warning(f"[alerts] Error checking alerts: {exc}")


async def _run_single_source(
    run_id: int,
    source_id: str,
    sitemap_data: dict,
    cancel_event: asyncio.Event,
):
    """Execute scrape → store → tag for a single source."""
    await _add_log(run_id, f"Starting scraper for {source_id}")

    async def _log_cb(msg: str, level: str = "INFO"):
        await _add_log(run_id, msg, level)

    feed_type = sitemap_data.get("_type", "sitemap")

    if feed_type == "rss":
        meta = sitemap_data.get("_meta", {})
        map_config = {
            "feed_url": meta.get("feed_url", ""),
            "source": source_id,
            "source_display": meta.get("source_display", source_id),
            "country": meta.get("country", ""),
            "category": meta.get("category"),
        }
        executor = RssExecutor(
            map_config=map_config,
            delay_seconds=settings.scrape_delay_seconds,
            log_callback=_log_cb,
        )
    else:
        executor = SitemapExecutor(
            sitemap_data,
            delay=settings.scrape_delay_seconds,
            log_callback=_log_cb,
        )

    try:
        if feed_type == "rss":
            raw_articles, rss_stats = await executor.execute()
        else:
            raw_articles = await executor.scrape()

        # Check cancellation after scraping
        if cancel_event.is_set():
            await _add_log(run_id, "Cancelled by user", level="WARNING")
            async with async_session() as db:
                r = await db.get(ScrapeRun, run_id)
                if r:
                    r.finished_at = datetime.now(timezone.utc)
                    r.status = "cancelled"
                    await db.commit()
            logger.info(f"[{source_id}] Cancelled by user")
            return

        # Save executor stats to logs
        if feed_type == "rss":
            stats = rss_stats
            await _add_log(run_id, f"Feed entries found: {stats.urls_found}, parsed: {stats.articles_parsed}")
        else:
            stats = executor.stats
            await _add_log(
                run_id,
                f"Sections attempted: {stats.sections_attempted}, "
                f"successful: {stats.sections_successful}, "
                f"failed: {stats.sections_failed}",
            )
            await _add_log(
                run_id,
                f"URLs found: {stats.urls_found}, "
                f"fetched: {stats.urls_fetched}, "
                f"failed: {len(stats.urls_failed)}",
            )
            await _add_log(
                run_id,
                f"Articles parsed: {stats.articles_parsed}, "
                f"skipped (short): {stats.articles_skipped_short}, "
                f"skipped (empty): {stats.articles_skipped_empty}, "
                f"parse errors: {stats.articles_parse_errors}",
            )

        found, new = await _store_articles(raw_articles, run_id=run_id)

        msg = f"Done: {found} found, {new} new, {found - new} duplicates skipped"
        await _add_log(run_id, msg)

        async with async_session() as db:
            r = await db.get(ScrapeRun, run_id)
            if r:
                r.finished_at = datetime.now(timezone.utc)
                r.articles_found = found
                r.articles_new = new
                r.status = "success"
                await db.commit()

        logger.info(f"[{source_id}] {msg}")

        # Check alerts for newly scraped articles
        if new > 0:
            async with async_session() as db:
                new_ids_result = await db.execute(
                    select(Article.id)
                    .where(Article.source == source_id)
                    .order_by(Article.id.desc())
                    .limit(new)
                )
                new_ids = [row[0] for row in new_ids_result.fetchall()]
            await _check_alerts(new_ids)

        # Tag articles (serialised across all runs)
        if cancel_event.is_set():
            return
        if settings.anthropic_api_key:
            logger.info(f"[{source_id}] Starting LLM tagging...")
            await _tag_untagged_articles()
        else:
            logger.info(f"[{source_id}] ANTHROPIC_API_KEY not set, skipping tagging.")

    except asyncio.CancelledError:
        logger.info(f"[{source_id}] Task cancelled")
        await _add_log(run_id, "Cancelled by user", level="WARNING")
        async with async_session() as db:
            r = await db.get(ScrapeRun, run_id)
            if r:
                r.finished_at = datetime.now(timezone.utc)
                r.status = "cancelled"
                await db.commit()
    except Exception as e:
        error_msg = f"Pipeline error: {e}"
        logger.error(f"[{source_id}] {error_msg}", exc_info=True)
        await _add_log(run_id, error_msg, level="ERROR")
        async with async_session() as db:
            r = await db.get(ScrapeRun, run_id)
            if r:
                r.finished_at = datetime.now(timezone.utc)
                r.status = "failed"
                r.error_message = str(e)
                await db.commit()
    finally:
        if feed_type != "rss":
            await executor.close()


# ---------------------------------------------------------------------------
# High-level pipeline launcher (for scheduler / "run all")
# ---------------------------------------------------------------------------

async def start_pipeline(sources: list[str] | None = None):
    """Start scraping for multiple sources concurrently. Each gets its own Task."""
    if sources:
        source_ids = sources
    else:
        all_maps = await load_active_maps()
        source_ids = [m["_id"] for m in all_maps]

    logger.info("=" * 60)
    logger.info(f"PIPELINE START | Sources: {', '.join(source_ids)}")
    logger.info("=" * 60)

    run_ids = []
    for source_id in source_ids:
        rid = await start_source(source_id)
        if rid is not None:
            run_ids.append(rid)

    # Wait for all launched tasks to complete
    tasks = [_running_tasks[rid] for rid in run_ids if rid in _running_tasks]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
