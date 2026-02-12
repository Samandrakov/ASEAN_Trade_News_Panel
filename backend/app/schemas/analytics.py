from pydantic import BaseModel


class WordFrequencyItem(BaseModel):
    word: str
    count: int


class TimelinePoint(BaseModel):
    date: str
    count: int


class TagDistributionItem(BaseModel):
    tag: str
    count: int


class SummarizeRequest(BaseModel):
    article_ids: list[int] | None = None
    country: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    max_articles: int = 50


class SummarizeResponse(BaseModel):
    summary: str
    articles_count: int
