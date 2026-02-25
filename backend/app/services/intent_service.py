import re
from typing import Optional
from app.models.schemas import SearchIntent


# ─── Heuristic Rules (fast, free) ─────────────────────────────────────────────

COMPARISON_SIGNALS = r"\b(best|top|vs|versus|compare|comparison|alternative|alternatives|review|reviews)\b"
TRANSACTIONAL_SIGNALS = r"\b(buy|price|cost|cheap|discount|deal|coupon|order|purchase|hire|pricing)\b"
NAVIGATIONAL_SIGNALS = r"\b(login|sign in|sign up|download|official|website|app)\b"
INFORMATIONAL_SIGNALS = r"\b(how|what|why|when|where|who|guide|tutorial|learn|explain|definition|meaning)\b"


def _heuristic_classify(keyword: str) -> Optional[SearchIntent]:
    kw = keyword.lower()
    if re.search(COMPARISON_SIGNALS, kw):
        return SearchIntent.comparison
    if re.search(TRANSACTIONAL_SIGNALS, kw):
        return SearchIntent.transactional
    if re.search(NAVIGATIONAL_SIGNALS, kw):
        return SearchIntent.navigational
    if re.search(INFORMATIONAL_SIGNALS, kw):
        return SearchIntent.informational
    return None  # Ambiguous — fall through to LLM


# ─── LLM Fallback ─────────────────────────────────────────────────────────────

async def _llm_classify(keyword: str) -> SearchIntent:
    """
    Calls LLMService to classify intent when heuristics are ambiguous.
    Returns one of the SearchIntent enum values.
    """
    from app.llm.service import llm_service
    result = await llm_service.classify_intent(keyword)
    try:
        return SearchIntent(result)
    except ValueError:
        return SearchIntent.informational  # safe fallback


# ─── Public API ───────────────────────────────────────────────────────────────

async def classify_intent(keyword: str) -> SearchIntent:
    """
    Hybrid intent classifier:
    1. Runs heuristic rules (instant, zero cost).
    2. Falls back to LLM only if heuristics are ambiguous.
    """
    intent = _heuristic_classify(keyword)
    if intent is not None:
        return intent
    return await _llm_classify(keyword)
