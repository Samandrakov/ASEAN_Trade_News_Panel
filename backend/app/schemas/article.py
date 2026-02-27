from datetime import datetime

from pydantic import BaseModel


class ArticleTagOut(BaseModel):
    id: int
    tag_type: str
    tag_value: str
    confidence: float | None

    model_config = {"from_attributes": True}


class ArticleListItem(BaseModel):
    id: int
    url: str
    title: str
    summary: str | None
    source: str
    source_display: str
    country: str
    category: str | None
    author: str | None
    word_count: int | None
    published_date: datetime | None
    scraped_at: datetime
    tagged: bool
    tags: list[ArticleTagOut]

    model_config = {"from_attributes": True}


class ArticleDetail(ArticleListItem):
    body: str


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    page_size: int
