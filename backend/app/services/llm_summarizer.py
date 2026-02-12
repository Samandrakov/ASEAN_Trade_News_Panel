import logging
from typing import TYPE_CHECKING

import anthropic

from ..config import settings

if TYPE_CHECKING:
    from ..models.article import Article

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """You are an expert analyst focusing on trade cooperation between Russia and ASEAN countries (Indonesia, Vietnam, Malaysia).

Summarize the following {count} news articles into a structured briefing in Russian language:

1. **Ключевые события**: Основные события и новости
2. **Торговля и инвестиции**: Тенденции в торговле, инвестиционных потоках
3. **По странам**: Заметные события по каждой стране
4. **Значение для сотрудничества Россия-АСЕАН**: Как эти события влияют на перспективы
5. **Риски и возможности**: Ключевые риски и возможности

Articles:
{articles_text}

Write the summary in Russian. Be analytical, not just descriptive. Cite specific articles by their titles."""


async def summarize_articles(articles: list["Article"]) -> str:
    if not settings.anthropic_api_key:
        return "Error: ANTHROPIC_API_KEY is not configured."

    articles_text = "\n\n".join(
        f"[{i + 1}] {a.title} ({a.source_display}, {a.country})\n{a.body[:2000]}"
        for i, a in enumerate(articles)
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        message = await client.messages.create(
            model=settings.llm_model_summarize,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARIZE_PROMPT.format(
                        count=len(articles), articles_text=articles_text
                    ),
                }
            ],
        )
        return message.content[0].text
    except anthropic.APIError as e:
        logger.error(f"Failed to summarize: {e}")
        return f"Error generating summary: {e}"
