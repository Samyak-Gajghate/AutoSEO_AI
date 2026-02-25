from app.services.scoring.rule_engine import compute_rule_score
from app.services.scoring.ai_engine import compute_ai_score
from app.core.database import AsyncSessionLocal
from sqlalchemy import text
from typing import Tuple, List


RULE_WEIGHT = 0.45
AI_WEIGHT = 0.55


async def score_content(
    uid: str,
    project_id: str,
    keyword: str,
    article: str,
    meta_title: str,
    meta_description: str,
    competitor_context: str,
    version_num: int,
) -> dict:
    """
    Combines rule-based and AI scoring into final 0–100 score.
    Stores result in Neon article_versions and returns full score dict.
    """
    rule_score, rule_feedback = compute_rule_score(
        content=article,
        keyword=keyword,
        meta_title=meta_title,
        meta_description=meta_description,
    )
    ai_score, ai_feedback = await compute_ai_score(
        uid=uid,
        keyword=keyword,
        article=article,
        competitor_context=competitor_context,
    )

    combined = int(rule_score * RULE_WEIGHT + ai_score * AI_WEIGHT)
    all_feedback = rule_feedback + ai_feedback

    # Update SEO score on the article version in Neon
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE article_versions
                SET seo_score = :score
                WHERE project_id = :pid AND version_num = :v
            """),
            {"score": combined, "pid": project_id, "v": version_num},
        )
        await session.commit()

    return {
        "rule_score": rule_score,
        "ai_score": ai_score,
        "combined_score": combined,
        "feedback_points": all_feedback[:10],
    }
