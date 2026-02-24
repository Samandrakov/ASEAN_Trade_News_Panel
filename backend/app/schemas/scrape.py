from datetime import datetime

from pydantic import BaseModel


class ScrapeRunOut(BaseModel):
    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None
    articles_found: int
    articles_new: int
    status: str
    error_message: str | None

    model_config = {"from_attributes": True}


class ScrapeLogEntryOut(BaseModel):
    id: int
    timestamp: datetime
    level: str
    message: str

    model_config = {"from_attributes": True}


class ScrapeRunDetailOut(ScrapeRunOut):
    log_entries: list[ScrapeLogEntryOut] = []


class ScrapeTriggerRequest(BaseModel):
    sources: list[str] | None = None


class ScrapeTriggerResponse(BaseModel):
    message: str
    sources: list[str]
