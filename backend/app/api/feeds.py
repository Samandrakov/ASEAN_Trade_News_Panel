from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_auth
from ..models.saved_feed import SavedFeed
from ..schemas.saved_feed import SavedFeedCreate, SavedFeedOut, SavedFeedUpdate

router = APIRouter(tags=["feeds"])


@router.get("/feeds", response_model=list[SavedFeedOut])
async def list_feeds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SavedFeed).order_by(SavedFeed.name))
    feeds = result.scalars().all()
    return [SavedFeedOut.model_validate(f) for f in feeds]


@router.get("/feeds/{feed_id}", response_model=SavedFeedOut)
async def get_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SavedFeed).where(SavedFeed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return SavedFeedOut.model_validate(feed)


@router.post("/feeds", response_model=SavedFeedOut, status_code=201)
async def create_feed(
    req: SavedFeedCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    feed = SavedFeed(
        name=req.name,
        description=req.description,
        filters_json=req.filters_json,
        color=req.color,
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return SavedFeedOut.model_validate(feed)


@router.put("/feeds/{feed_id}", response_model=SavedFeedOut)
async def update_feed(
    feed_id: int,
    req: SavedFeedUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(select(SavedFeed).where(SavedFeed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if req.name is not None:
        feed.name = req.name
    if req.description is not None:
        feed.description = req.description
    if req.filters_json is not None:
        feed.filters_json = req.filters_json
    if req.color is not None:
        feed.color = req.color
    await db.commit()
    await db.refresh(feed)
    return SavedFeedOut.model_validate(feed)


@router.delete("/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(select(SavedFeed).where(SavedFeed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    await db.delete(feed)
    await db.commit()
    return {"message": f"Feed '{feed.name}' deleted"}
