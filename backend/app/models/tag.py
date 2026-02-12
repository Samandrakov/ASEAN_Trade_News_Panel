import enum

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TagType(str, enum.Enum):
    COUNTRY_MENTION = "country_mention"
    TOPIC = "topic"
    SENTIMENT = "sentiment"


class ArticleTag(Base):
    __tablename__ = "article_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), index=True
    )
    tag_type: Mapped[str] = mapped_column(String(32), index=True)
    tag_value: Mapped[str] = mapped_column(String(128), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    article: Mapped["Article"] = relationship("Article", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("article_id", "tag_type", "tag_value", name="uq_article_tag"),
    )

    def __repr__(self) -> str:
        return f"<ArticleTag {self.tag_type}:{self.tag_value}>"
