import json
import logging

from sqlalchemy import select

from ..database import async_session
from ..models.scrape_map import ScrapeMap

logger = logging.getLogger(__name__)


async def load_active_maps() -> list[dict]:
    """Load all active sitemap definitions from the database."""
    async with async_session() as db:
        result = await db.execute(
            select(ScrapeMap).where(ScrapeMap.active == True)  # noqa: E712
        )
        maps = result.scalars().all()
        return [
            {
                "db_id": m.id,
                "map_id": m.map_id,
                **json.loads(m.sitemap_json),
            }
            for m in maps
        ]


async def load_map_by_id(map_id: str) -> dict | None:
    """Load a single sitemap by its map_id."""
    async with async_session() as db:
        result = await db.execute(
            select(ScrapeMap).where(ScrapeMap.map_id == map_id)
        )
        m = result.scalar_one_or_none()
        if m:
            return {
                "db_id": m.id,
                "map_id": m.map_id,
                **json.loads(m.sitemap_json),
            }
        return None


async def get_active_map_ids() -> list[str]:
    """Return list of active map_ids (for API source validation)."""
    async with async_session() as db:
        result = await db.execute(
            select(ScrapeMap.map_id).where(
                ScrapeMap.active == True  # noqa: E712
            )
        )
        return [row[0] for row in result.all()]
