from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    keywords_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    countries_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    matches: Mapped[list["AlertMatch"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class AlertMatch(Base):
    __tablename__ = "alert_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id"), index=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id"), index=True)
    matched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    alert: Mapped["Alert"] = relationship(back_populates="matches")
