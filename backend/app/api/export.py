import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_auth
from ..models.article import Article
from ..schemas.export import ExportRequest

router = APIRouter(tags=["export"])

COLUMNS = ["ID", "Title", "Source", "Country", "Category", "Published Date", "Word Count", "URL"]


def _build_query(req: ExportRequest):
    query = select(Article).order_by(Article.published_date.desc())
    if req.country:
        query = query.where(Article.country == req.country)
    if req.date_from:
        query = query.where(Article.published_date >= req.date_from)
    if req.date_to:
        query = query.where(Article.published_date <= req.date_to)
    if req.search:
        pattern = f"%{req.search}%"
        query = query.where(Article.title.ilike(pattern) | Article.body.ilike(pattern))
    return query


def _article_row(a: Article) -> list:
    pub = a.published_date.strftime("%Y-%m-%d") if isinstance(a.published_date, datetime) else str(a.published_date or "")
    return [a.id, a.title, a.source_display, a.country, a.category or "", pub, a.word_count or 0, a.url]


@router.post("/export")
async def export_articles(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(_build_query(req))
    articles = result.scalars().all()

    if req.format == "xlsx":
        wb = Workbook(write_only=True)
        ws = wb.create_sheet("Articles")
        ws.append(COLUMNS)
        for a in articles:
            ws.append(_article_row(a))

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"},
        )
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(COLUMNS)
        for a in articles:
            writer.writerow(_article_row(a))

        output = buf.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(output),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )
