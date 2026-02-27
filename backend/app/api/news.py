import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..api.deps import get_db
from ..models.article import Article
from ..models.tag import ArticleTag
from ..schemas.article import ArticleDetail, ArticleListItem, ArticleListResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["news"])

_SORT_COLUMNS = {
    "date": Article.published_date,
    "title": Article.title,
    "word_count": Article.word_count,
}


@router.get("/news", response_model=ArticleListResponse)
async def list_news(
    country: str | None = Query(None, max_length=8),
    tag_type: str | None = Query(None, max_length=50),
    tag_value: str | None = Query(None, max_length=100),
    date_from: str | None = Query(None, max_length=10),
    date_to: str | None = Query(None, max_length=10),
    search: str | None = Query(None, max_length=200),
    sort_by: str = Query("date", pattern="^(date|title|word_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # FTS5 search: find matching IDs first, fallback to LIKE
    fts_ids: list[int] | None = None
    if search:
        try:
            ids_result = await db.execute(
                text("SELECT rowid FROM articles_fts WHERE articles_fts MATCH :q").bindparams(q=search)
            )
            fts_ids = [row[0] for row in ids_result.fetchall()]
        except Exception as exc:
            logger.warning("FTS search failed, falling back to LIKE: %s", exc)
            fts_ids = None

    query = select(Article).options(selectinload(Article.tags))

    if fts_ids is not None:
        if not fts_ids:
            return ArticleListResponse(items=[], total=0, page=page, page_size=page_size)
        query = query.where(Article.id.in_(fts_ids))
    elif search:
        term = f"%{search}%"
        query = query.where(Article.title.ilike(term) | Article.body.ilike(term))

    if country:
        query = query.where(Article.country == country)
    if date_from:
        try:
            query = query.where(Article.published_date >= datetime.fromisoformat(date_from))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")
    if date_to:
        try:
            query = query.where(Article.published_date <= datetime.fromisoformat(date_to))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")
    if tag_type and tag_value:
        query = query.join(ArticleTag).where(
            ArticleTag.tag_type == tag_type, ArticleTag.tag_value == tag_value
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sorting
    sort_col = _SORT_COLUMNS.get(sort_by, Article.published_date)
    order_expr = sort_col.desc().nullslast() if sort_order == "desc" else sort_col.asc().nullslast()

    query = query.order_by(order_expr).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    articles = result.scalars().unique().all()

    return ArticleListResponse(
        items=[ArticleListItem.model_validate(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/news/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(Article)
        .options(selectinload(Article.tags))
        .where(Article.id == article_id)
    )
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleDetail.model_validate(article)
