import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Prefix for per-source cron jobs so we can manage them
_JOB_PREFIX = "cron_source_"
_FALLBACK_JOB_ID = "scrape_pipeline_fallback"


async def _scheduled_single_source(source_id: str):
    """Cron-triggered job: scrape a single source."""
    from .orchestrator import start_source

    logger.info(f"[scheduler] Cron trigger for source: {source_id}")
    await start_source(source_id)


async def _scheduled_pipeline_all():
    """Fallback interval job: scrape all active sources that do NOT have a cron expression."""
    from .orchestrator import start_source

    from ..database import async_session
    from ..models.scrape_map import ScrapeMap
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(
            select(ScrapeMap.map_id).where(
                ScrapeMap.active == True,  # noqa: E712
                ScrapeMap.cron_expression == None,  # noqa: E711
            )
        )
        source_ids = [r[0] for r in result.all()]

    if not source_ids:
        logger.info("[scheduler] No sources without cron to run on interval")
        return

    logger.info(f"[scheduler] Interval trigger for {len(source_ids)} sources without cron")
    for sid in source_ids:
        await start_source(sid)


async def sync_scheduler_jobs():
    """Read all scrape maps from DB and create/update cron jobs.
    Called at startup and when a cron expression is changed."""
    from ..database import async_session
    from ..models.scrape_map import ScrapeMap
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(
            select(ScrapeMap.map_id, ScrapeMap.cron_expression, ScrapeMap.active)
        )
        maps = result.all()

    # Remove old per-source cron jobs
    existing_jobs = scheduler.get_jobs()
    for job in existing_jobs:
        if job.id.startswith(_JOB_PREFIX):
            scheduler.remove_job(job.id)

    # Create new cron jobs for maps with cron_expression
    for map_id, cron_expr, active in maps:
        if active and cron_expr:
            job_id = f"{_JOB_PREFIX}{map_id}"
            try:
                trigger = CronTrigger.from_crontab(cron_expr)
                scheduler.add_job(
                    _scheduled_single_source,
                    trigger=trigger,
                    args=[map_id],
                    id=job_id,
                    replace_existing=True,
                )
                logger.info(f"[scheduler] Cron job for {map_id}: {cron_expr}")
            except Exception as e:
                logger.warning(f"[scheduler] Invalid cron for {map_id}: {cron_expr} — {e}")


def reschedule_source(map_id: str, cron_expression: str | None):
    """Update or remove the cron job for a single source (called after API update)."""
    job_id = f"{_JOB_PREFIX}{map_id}"

    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    if cron_expression:
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            scheduler.add_job(
                _scheduled_single_source,
                trigger=trigger,
                args=[map_id],
                id=job_id,
                replace_existing=True,
            )
            logger.info(f"[scheduler] Rescheduled {map_id}: {cron_expression}")
        except Exception as e:
            logger.warning(f"[scheduler] Failed to reschedule {map_id}: {e}")
    else:
        logger.info(f"[scheduler] Removed cron for {map_id}, will use fallback interval")


def start_scheduler():
    """Start the scheduler with a fallback interval job + per-source cron jobs."""
    # Fallback interval for sources without cron
    scheduler.add_job(
        _scheduled_pipeline_all,
        trigger=IntervalTrigger(hours=settings.scrape_interval_hours),
        id=_FALLBACK_JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started: fallback interval every {settings.scrape_interval_hours} hours"
    )

    # Sync per-source cron jobs from DB (schedule as task since it's async)
    loop = asyncio.get_event_loop()
    loop.create_task(sync_scheduler_jobs())


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
