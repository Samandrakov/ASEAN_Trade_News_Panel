import json
from datetime import datetime

from pydantic import BaseModel, field_validator

_ALLOWED_FILTER_KEYS = {"country", "tag_type", "tag_value", "date_from", "date_to", "search"}


def _validate_filters_json(v: str) -> str:
    try:
        data = json.loads(v)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("filters_json must be a JSON object")
    for key in data:
        if key not in _ALLOWED_FILTER_KEYS:
            raise ValueError(f"Unknown filter key: {key}")
    return v


class SavedFeedCreate(BaseModel):
    name: str
    description: str | None = None
    filters_json: str
    color: str | None = None

    @field_validator("filters_json")
    @classmethod
    def validate_filters(cls, v: str) -> str:
        return _validate_filters_json(v)


class SavedFeedUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    filters_json: str | None = None
    color: str | None = None

    @field_validator("filters_json")
    @classmethod
    def validate_filters(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_filters_json(v)


class SavedFeedOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    filters_json: str
    color: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
