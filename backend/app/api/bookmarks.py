from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_user_id
from ..models.article import Article
from ..models.bookmark import ArticleBookmark
from ..schemas.bookmark import BookmarkCreate, BookmarkOut

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=list[BookmarkOut])
async def list_bookmarks(
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            ArticleBookmark,
            Article.title.label("article_title"),
            Article.url.label("article_url"),
            Article.source_display.label("article_source_display"),
            Article.country.label("article_country"),
        )
        .outerjoin(Article, ArticleBookmark.article_id == Article.id)
        .where(ArticleBookmark.user_id == user_id)
        .order_by(ArticleBookmark.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        BookmarkOut(
            id=row[0].id,
            article_id=row[0].article_id,
            note=row[0].note,
            created_at=row[0].created_at,
            article_title=row.article_title,
            article_url=row.article_url,
            article_source_display=row.article_source_display,
            article_country=row.article_country,
        )
        for row in rows
    ]


@router.post("", response_model=BookmarkOut, status_code=201)
async def create_bookmark(
    req: BookmarkCreate,
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Check article exists
    article_result = await db.execute(
        select(Article).where(Article.id == req.article_id)
    )
    article = article_result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Статья не найдена")

    # Check not already bookmarked
    exists = await db.execute(
        select(ArticleBookmark.id).where(
            ArticleBookmark.user_id == user_id,
            ArticleBookmark.article_id == req.article_id,
        )
    )
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Статья уже в закладках")

    bookmark = ArticleBookmark(user_id=user_id, article_id=req.article_id)
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)

    return BookmarkOut(
        id=bookmark.id,
        article_id=bookmark.article_id,
        note=bookmark.note,
        created_at=bookmark.created_at,
        article_title=article.title,
        article_url=article.url,
        article_source_display=article.source_display,
        article_country=article.country,
    )


@router.delete("/{article_id}")
async def delete_bookmark_by_article(
    article_id: int,
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArticleBookmark).where(
            ArticleBookmark.user_id == user_id,
            ArticleBookmark.article_id == article_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Закладка не найдена")
    await db.delete(bookmark)
    await db.commit()
    return {"message": "Закладка удалена"}
