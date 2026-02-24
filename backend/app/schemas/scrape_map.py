import json
from datetime import datetime

from pydantic import BaseModel, field_validator


class ScrapeMapCreate(BaseModel):
    sitemap_json: str

    @field_validator("sitemap_json")
    @classmethod
    def validate_json(cls, v: str) -> str:
        try:
            data = json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e
        if "_id" not in data:
            raise ValueError("Missing _id field")
        if "startUrls" not in data:
            raise ValueError("Missing startUrls field")
        if "selectors" not in data:
            raise ValueError("Missing selectors field")
        if "_meta" not in data:
            raise ValueError("Missing _meta field")
        meta = data["_meta"]
        if "country" not in meta:
            raise ValueError("Missing _meta.country field")
        if "source_display" not in meta:
            raise ValueError("Missing _meta.source_display field")
        return v


class ScrapeMapUpdate(BaseModel):
    sitemap_json: str | None = None
    active: bool | None = None
    cron_expression: str | None = None

    @field_validator("sitemap_json")
    @classmethod
    def validate_json(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            data = json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e
        if "_id" not in data:
            raise ValueError("Missing _id field")
        return v


class ScrapeMapOut(BaseModel):
    id: int
    map_id: str
    name: str
    country: str
    active: bool
    cron_expression: str | None = None
    created_at: datetime
    updated_at: datetime
    sitemap_json: str

    model_config = {"from_attributes": True}


class ScrapeMapSummaryOut(BaseModel):
    id: int
    map_id: str
    name: str
    country: str
    active: bool
    cron_expression: str | None = None
    start_urls_count: int
    selectors_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
