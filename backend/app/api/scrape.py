from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db
from ..models.scrape_log import ScrapeRun
from ..pipeline.orchestrator import run_pipeline
from ..scrapers.registry import SCRAPER_REGISTRY
from ..schemas.scrape import ScrapeRunOut, ScrapeTriggerRequest, ScrapeTriggerResponse

router = APIRouter(tags=["scrape"])


@router.post("/scrape/trigger", response_model=ScrapeTriggerResponse)
async def trigger_scrape(
    req: ScrapeTriggerRequest,
    background_tasks: BackgroundTasks,
):
    sources = req.sources or list(SCRAPER_REGISTRY.keys())
    valid_sources = [s for s in sources if s in SCRAPER_REGISTRY]
    background_tasks.add_task(run_pipeline, valid_sources)
    return ScrapeTriggerResponse(
        message="Scraping started in background",
        sources=valid_sources,
    )


@router.get("/scrape/runs", response_model=list[ScrapeRunOut])
async def list_scrape_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(limit)
    result = await db.execute(query)
    return [ScrapeRunOut.model_validate(r) for r in result.scalars().all()]
