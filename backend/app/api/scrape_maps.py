import json

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_auth
from ..models.scrape_map import ScrapeMap
from ..pipeline.scheduler import reschedule_source
from ..schemas.scrape_map import (
    ScrapeMapCreate,
    ScrapeMapOut,
    ScrapeMapSummaryOut,
    ScrapeMapUpdate,
)

router = APIRouter(tags=["scrape-maps"])


@router.get("/scrape-maps", response_model=list[ScrapeMapSummaryOut])
async def list_maps(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(ScrapeMap).order_by(ScrapeMap.country, ScrapeMap.name)
    if active_only:
        query = query.where(ScrapeMap.active == True)  # noqa: E712
    result = await db.execute(query)
    maps = result.scalars().all()
    out = []
    for m in maps:
        try:
            data = json.loads(m.sitemap_json)
        except (json.JSONDecodeError, TypeError):
            data = {}
        out.append(
            ScrapeMapSummaryOut(
                id=m.id,
                map_id=m.map_id,
                name=m.name,
                country=m.country,
                active=m.active,
                cron_expression=m.cron_expression,
                start_urls_count=len(data.get("startUrls", [])),
                selectors_count=len(data.get("selectors", [])),
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return out


@router.get("/scrape-maps/{map_id}", response_model=ScrapeMapOut)
async def get_map(map_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScrapeMap).where(ScrapeMap.map_id == map_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Map not found")
    return ScrapeMapOut.model_validate(m)


@router.post("/scrape-maps", response_model=ScrapeMapOut, status_code=201)
async def create_map(
    req: ScrapeMapCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    data = json.loads(req.sitemap_json)
    map_id = data["_id"]
    meta = data.get("_meta", {})

    exists = await db.execute(
        select(ScrapeMap.id).where(ScrapeMap.map_id == map_id)
    )
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409, detail=f"Map '{map_id}' already exists"
        )

    m = ScrapeMap(
        map_id=map_id,
        name=meta.get("source_display", map_id),
        country=meta.get("country", ""),
        sitemap_json=req.sitemap_json,
        active=True,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return ScrapeMapOut.model_validate(m)


@router.put("/scrape-maps/{map_id}", response_model=ScrapeMapOut)
async def update_map(
    map_id: str,
    req: ScrapeMapUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(
        select(ScrapeMap).where(ScrapeMap.map_id == map_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Map not found")

    if req.sitemap_json is not None:
        data = json.loads(req.sitemap_json)
        meta = data.get("_meta", {})
        m.sitemap_json = req.sitemap_json
        m.name = meta.get("source_display", m.name)
        m.country = meta.get("country", m.country)
        if data.get("_id") and data["_id"] != m.map_id:
            m.map_id = data["_id"]
    if req.active is not None:
        m.active = req.active

    if req.cron_expression is not None:
        cron_val = req.cron_expression.strip() if req.cron_expression.strip() else None
        if cron_val and not croniter.is_valid(cron_val):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {cron_val}",
            )
        m.cron_expression = cron_val

    await db.commit()
    await db.refresh(m)

    # Reschedule after commit
    reschedule_source(m.map_id, m.cron_expression)

    return ScrapeMapOut.model_validate(m)


@router.delete("/scrape-maps/{map_id}")
async def delete_map(
    map_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(
        select(ScrapeMap).where(ScrapeMap.map_id == map_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Map not found")
    await db.delete(m)
    await db.commit()
    return {"message": f"Map '{map_id}' deleted"}


@router.post("/scrape-maps/{map_id}/toggle")
async def toggle_map(
    map_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(
        select(ScrapeMap).where(ScrapeMap.map_id == map_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Map not found")
    m.active = not m.active
    await db.commit()
    return {"map_id": map_id, "active": m.active}


@router.post(
    "/scrape-maps/import", response_model=ScrapeMapOut, status_code=201
)
async def import_chrome_extension_map(
    req: ScrapeMapCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    """Import a sitemap from Web Scraper Chrome Extension format.
    If _meta is missing, create a minimal one."""
    data = json.loads(req.sitemap_json)
    if "_meta" not in data:
        data["_meta"] = {
            "country": "",
            "source_display": data.get("_id", "Unknown"),
            "url_filter_pattern": None,
            "date_source": "selector",
            "date_selector_formats": [],
            "category_mapping": {},
            "min_body_length": 200,
            "author_selectors": [],
        }
        req = ScrapeMapCreate(
            sitemap_json=json.dumps(data, ensure_ascii=False)
        )

    return await create_map(req, db)
