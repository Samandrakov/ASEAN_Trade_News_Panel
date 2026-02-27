from datetime import datetime

from pydantic import BaseModel


class BookmarkCreate(BaseModel):
    article_id: int


class BookmarkOut(BaseModel):
    id: int
    article_id: int
    note: str | None = None
    created_at: datetime
    article_title: str | None = None
    article_url: str | None = None
    article_source_display: str | None = None
    article_country: str | None = None
