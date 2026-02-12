import json
import logging

import anthropic

from ..config import settings

logger = logging.getLogger(__name__)

TAGGING_PROMPT = """Analyze this news article and return a JSON object with the following fields:

- "country_mentions": list of countries explicitly mentioned from [Russia, China, USA, Japan, South Korea, India, EU, Indonesia, Vietnam, Malaysia, Thailand, Philippines, Singapore, Myanmar, Cambodia, Laos, Brunei, Australia, Taiwan, ASEAN]
- "topics": list from [trade, investment, sanctions, energy, agriculture, manufacturing, digital_economy, infrastructure, diplomacy, finance, tourism, labor, logistics, regulations, privatization, monetary_policy, real_estate, commodities, startups, education]
- "sectors": list of economic sectors/industries from [oil_gas, mining, automotive, electronics, textiles, food_processing, palm_oil, rubber, fisheries, construction, banking, insurance, telecommunications, aviation, shipping, retail, pharmaceuticals, chemicals, steel, renewable_energy]
- "sentiment": one of ["positive", "negative", "neutral"]
- "summary": 2-3 sentence summary focused on economic/trade implications. Mention specific countries, companies, trade volumes or policy changes if present.

Article title: {title}
Article text (excerpt): {body}

Return ONLY valid JSON, no markdown fences or extra text."""


async def classify_article(title: str, body: str) -> dict | None:
    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY set, skipping tagging")
        return None

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        message = await client.messages.create(
            model=settings.llm_model_tagging,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": TAGGING_PROMPT.format(
                        title=title, body=body[:3000]
                    ),
                }
            ],
        )
        text = message.content[0].text.strip()
        # Remove markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, anthropic.APIError) as e:
        logger.error(f"Failed to classify article '{title[:50]}': {e}")
        return None
