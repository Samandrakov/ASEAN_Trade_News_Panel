from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db
from ..models.article import Article
from ..models.tag import ArticleTag

router = APIRouter(tags=["tags"])


@router.get("/tags")
async def get_tags(db: AsyncSession = Depends(get_db)):
    query = (
        select(ArticleTag.tag_type, ArticleTag.tag_value, func.count().label("count"))
        .group_by(ArticleTag.tag_type, ArticleTag.tag_value)
        .order_by(func.count().desc())
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        {"tag_type": row.tag_type, "tag_value": row.tag_value, "count": row.count}
        for row in rows
    ]


@router.get("/countries")
async def get_countries(db: AsyncSession = Depends(get_db)):
    query = (
        select(Article.country, func.count().label("count"))
        .group_by(Article.country)
        .order_by(func.count().desc())
    )
    result = await db.execute(query)
    rows = result.all()

    country_names = {
        "ID": "Indonesia",
        "VN": "Vietnam",
        "MY": "Malaysia",
    }
    return [
        {
            "code": row.country,
            "name": country_names.get(row.country, row.country),
            "count": row.count,
        }
        for row in rows
    ]
