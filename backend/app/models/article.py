from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    body: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(128), index=True)
    source_display: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(2), index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    author: Mapped[str | None] = mapped_column(String(512), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    tagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")

    tags: Mapped[list["ArticleTag"]] = relationship(
        "ArticleTag", back_populates="article", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Article {self.id}: {self.title[:50]}>"
