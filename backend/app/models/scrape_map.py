from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ScrapeMap(Base):
    __tablename__ = "scrape_maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    map_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    country: Mapped[str] = mapped_column(String(8), index=True)
    sitemap_json: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    cron_expression: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    feed_type: Mapped[str] = mapped_column(String(32), default="sitemap")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
