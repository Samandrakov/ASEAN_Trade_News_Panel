from pydantic import BaseModel


class ExportRequest(BaseModel):
    country: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    search: str | None = None
    tag_type: str | None = None
    tag_value: str | None = None
    format: str = "csv"
