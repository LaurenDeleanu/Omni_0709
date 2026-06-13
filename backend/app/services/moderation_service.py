import logging
from typing import Tuple
from openai import AsyncOpenAI

logger = logging.getLogger("successcore.moderation")

FLAGGED_CATEGORIES = {"hate", "hate/threatening", "self-harm", "sexual", "sexual/minors", "violence", "violence/graphic"}

async def moderate_content(text: str, client: AsyncOpenAI) -> Tuple[bool, dict]:
    if not text or len(text) < 10:
        return True, {"flagged": False, "categories": {}}

    try:
        response = await client.moderations.create(input=text[:4000])
        result = response.results[0]
        flagged = result.flagged
        categories = {}

        for cat, score in result.category_scores.model_dump().items():
            if score is not None and score > 0.01:
                categories[cat] = round(score, 4)

        is_blocked = flagged and any(
            cat in FLAGGED_CATEGORIES for cat in result.categories.model_dump() if result.categories.model_dump().get(cat)
        )

        if is_blocked:
            blocked_cats = [c for c in FLAGGED_CATEGORIES if result.categories.model_dump().get(c)]
            logger.warning(f"Content blocked by moderation: {blocked_cats}")

        return not is_blocked, {"flagged": flagged, "categories": categories}

    except Exception as e:
        logger.error(f"Moderation API error: {e}")
        return True, {"flagged": False, "error": str(e)}
