import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..api.deps import get_db, require_auth
from ..models.article import Article
from ..models.scrape_log import ScrapeLogEntry, ScrapeRun
from ..pipeline.orchestrator import (
    cancel_all,
    cancel_run,
    get_running_run_ids,
    is_pipeline_running,
    is_source_running,
    start_pipeline,
    start_source,
)
from ..scrapers.registry import get_active_map_ids
from ..schemas.scrape import (
    ScrapeLogEntryOut,
    ScrapeRunDetailOut,
    ScrapeRunOut,
    ScrapeTriggerRequest,
    ScrapeTriggerResponse,
)

router = APIRouter(tags=["scrape"])


@router.post("/scrape/trigger", response_model=ScrapeTriggerResponse)
async def trigger_scrape(
    req: ScrapeTriggerRequest,
    background_tasks: BackgroundTasks,
    _user: str = Depends(require_auth),
):
    active_ids = await get_active_map_ids()
    sources = req.sources or active_ids
    valid_sources = [s for s in sources if s in active_ids]
    if not valid_sources:
        raise HTTPException(
            status_code=400, detail="No valid sources specified"
        )

    # Skip sources that are already running
    to_start = [s for s in valid_sources if is_source_running(s) is None]
    already_running = [s for s in valid_sources if is_source_running(s) is not None]

    if not to_start:
        raise HTTPException(
            status_code=409,
            detail=f"All requested sources are already running: {already_running}",
        )

    background_tasks.add_task(start_pipeline, to_start)
    return ScrapeTriggerResponse(
        message="Scraping started in background",
        sources=to_start,
    )


@router.post("/scrape/cancel")
async def cancel_scrape(_user: str = Depends(require_auth)):
    count = await cancel_all()
    if count > 0:
        return {"message": f"Cancellation requested for {count} run(s)"}
    raise HTTPException(
        status_code=409, detail="No pipeline is currently running"
    )


@router.post("/scrape/runs/{run_id}/cancel")
async def cancel_scrape_run(run_id: int, _user: str = Depends(require_auth)):
    """Cancel a specific scrape run by its ID."""
    cancelled = await cancel_run(run_id)
    if cancelled:
        return {"message": f"Cancellation requested for run {run_id}"}
    raise HTTPException(
        status_code=409, detail="Run is not currently active"
    )


@router.get("/scrape/status")
async def pipeline_status():
    running_ids = get_running_run_ids()
    return {
        "running": len(running_ids) > 0,
        "running_run_ids": running_ids,
    }


@router.get("/scrape/runs", response_model=list[ScrapeRunOut])
async def list_scrape_runs(
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ScrapeRun)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [
        ScrapeRunOut.model_validate(r)
        for r in result.scalars().all()
    ]


@router.get("/scrape/runs/by-source/{source_id}", response_model=list[ScrapeRunOut])
async def list_runs_by_source(
    source_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get scrape runs for a specific source."""
    query = (
        select(ScrapeRun)
        .where(ScrapeRun.source == source_id)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [ScrapeRunOut.model_validate(r) for r in result.scalars().all()]


@router.get(
    "/scrape/runs/{run_id}", response_model=ScrapeRunDetailOut
)
async def get_scrape_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ScrapeRun)
        .where(ScrapeRun.id == run_id)
        .options(selectinload(ScrapeRun.log_entries))
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=404, detail="Scrape run not found"
        )
    return ScrapeRunDetailOut.model_validate(run)


@router.get("/scrape/runs/{run_id}/logs")
async def poll_run_logs(
    run_id: int,
    after_id: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Return log entries added after a given log entry ID.
    Frontend polls this every 1-2 seconds for live updates."""
    query = (
        select(ScrapeLogEntry)
        .where(ScrapeLogEntry.run_id == run_id)
        .where(ScrapeLogEntry.id > after_id)
        .order_by(ScrapeLogEntry.id)
    )
    result = await db.execute(query)
    entries = result.scalars().all()
    return [ScrapeLogEntryOut.model_validate(e) for e in entries]


@router.get("/scrape/live")
async def live_scrape_status(
    db: AsyncSession = Depends(get_db),
):
    """Returns currently running scrape runs with their latest log entries."""
    query = (
        select(ScrapeRun)
        .where(ScrapeRun.status == "running")
        .order_by(ScrapeRun.started_at.desc())
    )
    result = await db.execute(query)
    running_runs = result.scalars().all()

    live_data = []
    for run in running_runs:
        log_query = (
            select(ScrapeLogEntry)
            .where(ScrapeLogEntry.run_id == run.id)
            .order_by(ScrapeLogEntry.id.desc())
            .limit(10)
        )
        log_result = await db.execute(log_query)
        recent_logs = list(reversed(log_result.scalars().all()))

        live_data.append(
            {
                "run_id": run.id,
                "source": run.source,
                "started_at": run.started_at.isoformat(),
                "articles_found": run.articles_found,
                "articles_new": run.articles_new,
                "recent_logs": [
                    {
                        "id": e.id,
                        "timestamp": e.timestamp.isoformat(),
                        "level": e.level,
                        "message": e.message,
                    }
                    for e in recent_logs
                ],
            }
        )

    return {
        "running": len(live_data) > 0,
        "runs": live_data,
    }


@router.get("/scrape/stats")
async def scrape_stats(db: AsyncSession = Depends(get_db)):
    """Return aggregate stats about collected articles by source."""
    result = await db.execute(
        select(
            Article.source,
            Article.source_display,
            Article.country,
            func.count(Article.id).label("total"),
            func.max(Article.scraped_at).label("last_scraped"),
        ).group_by(
            Article.source, Article.source_display, Article.country
        )
    )
    rows = result.all()
    return [
        {
            "source": r.source,
            "source_display": r.source_display,
            "country": r.country,
            "total_articles": r.total,
            "last_scraped": (
                r.last_scraped.isoformat() if r.last_scraped else None
            ),
        }
        for r in rows
    ]


@router.get("/scrape/stats/{source_id}")
async def scrape_stats_by_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Detailed stats for a specific source."""
    # Article count
    article_count = await db.execute(
        select(func.count(Article.id)).where(Article.source == source_id)
    )
    total_articles = article_count.scalar() or 0

    # Run stats
    run_stats = await db.execute(
        select(
            func.count(ScrapeRun.id).label("total_runs"),
            func.sum(case((ScrapeRun.status == "success", 1), else_=0)).label("success_runs"),
            func.sum(case((ScrapeRun.status == "failed", 1), else_=0)).label("failed_runs"),
            func.sum(case((ScrapeRun.status == "cancelled", 1), else_=0)).label("cancelled_runs"),
            func.max(ScrapeRun.started_at).label("last_run_at"),
        ).where(ScrapeRun.source == source_id)
    )
    row = run_stats.one()

    return {
        "source": source_id,
        "total_articles": total_articles,
        "total_runs": row.total_runs or 0,
        "success_runs": row.success_runs or 0,
        "failed_runs": row.failed_runs or 0,
        "cancelled_runs": row.cancelled_runs or 0,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
    }


@router.get("/scrape/articles/{source_id}")
async def articles_by_source(
    source_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get articles collected from a specific source (without body for performance)."""
    query = (
        select(
            Article.id,
            Article.url,
            Article.title,
            Article.country,
            Article.category,
            Article.published_date,
            Article.scraped_at,
            Article.word_count,
            Article.source_display,
            Article.author,
        )
        .where(Article.source == source_id)
        .order_by(Article.scraped_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    return [
        {
            "id": r.id,
            "url": r.url,
            "title": r.title,
            "country": r.country,
            "category": r.category,
            "published_date": r.published_date.isoformat() if r.published_date else None,
            "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
            "word_count": r.word_count,
            "source_display": r.source_display,
            "author": r.author,
        }
        for r in result.all()
    ]


@router.get("/scrape/articles/{source_id}/{article_id}")
async def article_detail_by_source(
    source_id: str,
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get full article with body (loaded on demand)."""
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.source == source_id,
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "country": article.country,
        "category": article.category,
        "published_date": article.published_date.isoformat() if article.published_date else None,
        "scraped_at": article.scraped_at.isoformat() if article.scraped_at else None,
        "word_count": article.word_count,
        "source_display": article.source_display,
        "author": article.author,
        "body": article.body,
    }
