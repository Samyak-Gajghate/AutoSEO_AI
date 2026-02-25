from datetime import datetime, timezone
from typing import Optional
from google.cloud import firestore

# Firestore client (initialized lazily)
_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db


async def log_usage(
    uid: str,
    feature: str,
    tokens_in: int,
    tokens_out: int,
    model: str,
    latency_ms: int,
    cost_usd: Optional[float] = None,
):
    """
    Log a single LLM call to Firestore usage_logs collection.
    Called by LLMService after every generation.
    """
    if cost_usd is None:
        # Rough cost estimate: $0.50/1M input + $1.50/1M output (gpt-4o-mini rates)
        cost_usd = (tokens_in * 0.0000005) + (tokens_out * 0.0000015)

    db = get_db()
    await db.collection("usage_logs").add({
        "user_id": uid,
        "feature": feature,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 6),
        "model": model,
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc),
    })


async def get_monthly_token_count(uid: str) -> int:
    """
    Returns total tokens consumed by a user in the current calendar month.
    Used by token_budget.enforce_budget().
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    docs = (
        db.collection("usage_logs")
        .where("user_id", "==", uid)
        .where("timestamp", ">=", month_start)
        .stream()
    )

    total = 0
    async for doc in docs:
        data = doc.to_dict()
        total += data.get("tokens_in", 0) + data.get("tokens_out", 0)
    return total


async def get_monthly_summary(uid: str) -> dict:
    """
    Returns a structured usage summary for the dashboard token widget.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    docs = (
        db.collection("usage_logs")
        .where("user_id", "==", uid)
        .where("timestamp", ">=", month_start)
        .stream()
    )

    total_tokens = 0
    total_cost = 0.0
    by_feature: dict[str, int] = {}

    async for doc in docs:
        data = doc.to_dict()
        t = data.get("tokens_in", 0) + data.get("tokens_out", 0)
        total_tokens += t
        total_cost += data.get("cost_usd", 0.0)
        feature = data.get("feature", "unknown")
        by_feature[feature] = by_feature.get(feature, 0) + t

    return {
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "by_feature": by_feature,
        "month": now.strftime("%B %Y"),
    }
