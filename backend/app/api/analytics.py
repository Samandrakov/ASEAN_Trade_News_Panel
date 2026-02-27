from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db
from ..models.article import Article
from ..models.tag import ArticleTag
from ..schemas.analytics import TagDistributionItem, TimelinePoint, WordFrequencyItem
from ..services.word_frequency import compute_word_frequency

router = APIRouter(prefix="/analytics", tags=["analytics"])


class SentimentTrendPoint(BaseModel):
    period: str
    positive: int = 0
    negative: int = 0
    neutral: int = 0


@router.get("/word-frequency", response_model=list[WordFrequencyItem])
async def word_frequency(
    country: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    top_n: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(Article.body)
    if country:
        query = query.where(Article.country == country)
    if date_from:
        query = query.where(Article.published_date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(Article.published_date <= datetime.fromisoformat(date_to))

    result = await db.execute(query)
    texts = [row[0] for row in result.all()]

    freq = compute_word_frequency(texts, top_n)
    return [WordFrequencyItem(word=w, count=c) for w, c in freq]


@router.get("/timeline", response_model=list[TimelinePoint])
async def timeline(
    country: str | None = None,
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
):
    fmt_map = {"day": "%Y-%m-%d", "week": "%Y-W%W", "month": "%Y-%m"}
    fmt = fmt_map[granularity]

    date_label = func.strftime(fmt, Article.published_date).label("date")
    query = (
        select(date_label, func.count().label("count"))
        .where(Article.published_date.isnot(None))
        .group_by("date")
        .order_by("date")
    )
    if country:
        query = query.where(Article.country == country)

    result = await db.execute(query)
    return [TimelinePoint(date=row.date, count=row.count) for row in result.all()]


@router.get("/tag-distribution", response_model=list[TagDistributionItem])
async def tag_distribution(
    tag_type: str = Query("topic"),
    country: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(
        ArticleTag.tag_value.label("tag"), func.count().label("count")
    ).where(ArticleTag.tag_type == tag_type)

    if country:
        query = query.join(Article).where(Article.country == country)

    query = query.group_by(ArticleTag.tag_value).order_by(func.count().desc())

    result = await db.execute(query)
    return [TagDistributionItem(tag=row.tag, count=row.count) for row in result.all()]


@router.get("/sentiment-trend", response_model=list[SentimentTrendPoint])
async def sentiment_trend(
    country: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    granularity: str = Query("week", pattern="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
):
    fmt_map = {"day": "%Y-%m-%d", "week": "%Y-W%W", "month": "%Y-%m"}
    fmt = fmt_map[granularity]

    period_label = func.strftime(fmt, Article.published_date).label("period")
    query = (
        select(period_label, ArticleTag.tag_value.label("sentiment"), func.count().label("count"))
        .join(Article, ArticleTag.article_id == Article.id)
        .where(
            ArticleTag.tag_type == "sentiment",
            Article.published_date.isnot(None),
        )
        .group_by("period", ArticleTag.tag_value)
        .order_by("period")
    )
    if country:
        query = query.where(Article.country == country)
    if date_from:
        query = query.where(Article.published_date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(Article.published_date <= datetime.fromisoformat(date_to))

    result = await db.execute(query)
    rows = result.all()

    # Aggregate by period
    periods: dict[str, SentimentTrendPoint] = {}
    for row in rows:
        p = row.period
        if p not in periods:
            periods[p] = SentimentTrendPoint(period=p)
        if row.sentiment == "positive":
            periods[p].positive += row.count
        elif row.sentiment == "negative":
            periods[p].negative += row.count
        else:
            periods[p].neutral += row.count

    return list(periods.values())
