from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_auth
from ..models.article import Article
from ..schemas.analytics import SummarizeRequest, SummarizeResponse
from ..services.llm_summarizer import summarize_articles

router = APIRouter(tags=["summarize"])


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    req: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    query = select(Article)

    if req.article_ids:
        query = query.where(Article.id.in_(req.article_ids))
    else:
        if req.country:
            query = query.where(Article.country == req.country)
        if req.date_from:
            query = query.where(
                Article.published_date >= datetime.fromisoformat(req.date_from)
            )
        if req.date_to:
            query = query.where(
                Article.published_date <= datetime.fromisoformat(req.date_to)
            )

    query = query.order_by(Article.published_date.desc()).limit(req.max_articles)
    result = await db.execute(query)
    articles = result.scalars().all()

    if not articles:
        return SummarizeResponse(summary="No articles found for the given criteria.", articles_count=0)

    summary_text = await summarize_articles(articles)
    return SummarizeResponse(summary=summary_text, articles_count=len(articles))
