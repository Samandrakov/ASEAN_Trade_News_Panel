from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..api.deps import get_db
from ..models.article import Article
from ..models.tag import ArticleTag
from ..schemas.article import ArticleDetail, ArticleListItem, ArticleListResponse

router = APIRouter(tags=["news"])


@router.get("/news", response_model=ArticleListResponse)
async def list_news(
    country: str | None = Query(None, max_length=8),
    tag_type: str | None = Query(None, max_length=50),
    tag_value: str | None = Query(None, max_length=100),
    date_from: str | None = Query(None, max_length=10),
    date_to: str | None = Query(None, max_length=10),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Article).options(selectinload(Article.tags))

    if country:
        query = query.where(Article.country == country)
    if search:
        term = f"%{search}%"
        query = query.where(Article.title.ilike(term) | Article.body.ilike(term))
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

    # Paginate
    query = (
        query.order_by(Article.published_date.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
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
