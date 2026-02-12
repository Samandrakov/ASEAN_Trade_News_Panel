import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _scheduled_pipeline():
    from .orchestrator import run_pipeline

    await run_pipeline()


def start_scheduler():
    scheduler.add_job(
        _scheduled_pipeline,
        trigger=IntervalTrigger(hours=settings.scrape_interval_hours),
        id="scrape_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started: scraping every {settings.scrape_interval_hours} hours"
    )


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
