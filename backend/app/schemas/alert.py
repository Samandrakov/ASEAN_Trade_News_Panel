from datetime import datetime

from pydantic import BaseModel


class AlertCreate(BaseModel):
    name: str
    keywords: list[str] = []
    countries: list[str] = []


class AlertUpdate(BaseModel):
    active: bool | None = None
    name: str | None = None
    keywords: list[str] | None = None
    countries: list[str] | None = None


class AlertOut(BaseModel):
    id: int
    name: str
    keywords: list[str]
    countries: list[str]
    active: bool
    created_at: datetime


class AlertMatchOut(BaseModel):
    id: int
    alert_id: int
    alert_name: str
    article_id: int
    article_title: str
    article_url: str
    article_country: str
    matched_at: datetime
    read: bool
