from app.llm.service import llm_service
from typing import Tuple, List


async def compute_ai_score(
    uid: str,
    keyword: str,
    article: str,
    competitor_context: str,
) -> Tuple[int, List[str]]:
    """
    AI-based SEO evaluation. Calls LLMService.evaluate_content().
    Returns (ai_score 0–100, feedback_points list).
    """
    score, feedback, _ = await llm_service.evaluate_content(
        uid=uid,
        keyword=keyword,
        article=article,
        competitor_context=competitor_context,
    )
    return score, feedback
