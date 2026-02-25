from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.config import settings

# Feature-level token caps per request
FEATURE_CAPS = {
    "intent": 500,
    "outline": 4_000,
    "article": 8_000,
    "score": 3_000,
    "edit": 2_000,
    "gap": 3_000,
    "authority": 4_000,
}

SOFT_WARNING_THRESHOLD = 0.80  # Warn at 80% of monthly budget


async def get_monthly_usage(uid: str) -> int:
    """
    Returns total tokens consumed by user in the current calendar month.
    Queries Firestore usage_logs collection.
    Imported here lazily to avoid circular imports.
    """
    from app.utils.token_tracker import get_monthly_token_count
    return await get_monthly_token_count(uid)


async def enforce_budget(uid: str, feature: str) -> dict:
    """
    Call BEFORE any LLM generation. Raises 429 if monthly cap exceeded.
    Returns a metadata dict that can be attached to the response if soft warning applies.
    """
    monthly = await get_monthly_usage(uid)
    cap = settings.monthly_token_cap

    if monthly >= cap:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly token limit of {cap:,} reached. Upgrade your plan or wait until next month.",
        )

    meta = {"monthly_used": monthly, "monthly_cap": cap}

    if monthly >= cap * SOFT_WARNING_THRESHOLD:
        meta["warning"] = (
            f"You have used {monthly / cap * 100:.0f}% of your monthly token budget."
        )

    return meta


def check_feature_cap(feature: str, estimated_tokens: int):
    """
    Raises 400 if a single request would exceed that feature's per-request token cap.
    """
    cap = FEATURE_CAPS.get(feature, 10_000)
    if estimated_tokens > cap:
        raise HTTPException(
            status_code=400,
            detail=f"Request exceeds per-call token limit for '{feature}' ({cap:,} tokens).",
        )
