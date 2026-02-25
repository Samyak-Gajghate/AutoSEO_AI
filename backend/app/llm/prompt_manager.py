from typing import Optional
from google.cloud import firestore

_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db


# Default prompt templates (seeded if Firestore collection is empty)
DEFAULT_TEMPLATES = {
    "intent": {
        "version": "v1",
        "template_text": (
            "You are an SEO strategist. Classify the search intent of this keyword "
            "into exactly one of: informational, transactional, comparison, navigational.\n"
            "Keyword: {keyword}\n"
            "Respond with JSON: {{\"intent\": \"<label>\"}}"
        ),
    },
    "outline": {
        "version": "v1",
        "template_text": (
            "You are an expert SEO content strategist.\n"
            "Search Intent: {intent}\n"
            "Target Keyword: {keyword}\n"
            "Competitor Structure:\n{competitor_context}\n\n"
            "Generate a superior SEO outline that outperforms the competitors. "
            "Tailor the structure to the search intent. Include:\n"
            "- Semantic keyword clusters\n"
            "- A dedicated FAQ section\n"
            "- Internal linking anchor suggestions\n"
            "Respond with JSON: {{\"outline\": [{{"
            "\"heading\": \"...\", \"level\": 1|2|3, \"notes\": \"...\"}}]}}"
        ),
    },
    "article": {
        "version": "v1",
        "template_text": (
            "You are an expert SEO content writer.\n"
            "Search Intent: {intent}\n"
            "Target Keyword: {keyword}\n"
            "Outline:\n{outline}\n\n"
            "Write a complete, 1200-2000 word SEO-optimized article. Include:\n"
            "- Proper heading hierarchy\n"
            "- Natural keyword usage\n"
            "- A FAQ section at the end\n"
            "Respond with JSON: {{\"content\": \"...\", \"meta_title\": \"...\", "
            "\"meta_description\": \"...\"}}"
        ),
    },
    "score": {
        "version": "v1",
        "template_text": (
            "You are an SEO quality evaluator.\n"
            "Target Keyword: {keyword}\n"
            "Competitor Context:\n{competitor_context}\n\n"
            "Article:\n{article}\n\n"
            "Evaluate this article. Return JSON:\n"
            "{{\"ai_score\": 0-100, \"feedback_points\": [\"...\", ...], "
            "\"missing_topics\": [\"...\", ...]}}"
        ),
    },
    "edit": {
        "version": "v1",
        "template_text": (
            "You are an SEO content editor.\n"
            "Article context:\n{surrounding_context}\n\n"
            "Paragraph to improve:\n{paragraph}\n\n"
            "Provide exactly 3 improved variations. Each must be better for SEO and readability.\n"
            "Respond with JSON: {{\"variations\": ["
            "{{\"text\": \"...\", \"reasoning\": \"...\"}}]}}"
        ),
    },
    "gap": {
        "version": "v1",
        "template_text": (
            "You are an SEO content gap analyst.\n"
            "Target Keyword: {keyword}\n"
            "Competitor content themes:\n{competitor_context}\n\n"
            "User article:\n{article}\n\n"
            "Identify content gaps. Respond with JSON:\n"
            "{{\"missing_subtopics\": [...], \"weak_sections\": [...], "
            "\"semantic_keywords\": [...]}}"
        ),
    },
    "authority": {
        "version": "v1",
        "template_text": (
            "You are an SEO topical authority analyst.\n"
            "Here are the user's content clusters:\n{clusters}\n\n"
            "For each cluster, label it and suggest 1-3 additional articles "
            "that would strengthen topical authority.\n"
            "Respond with JSON: {{\"clusters\": ["
            "{{\"label\": \"...\", \"suggestions\": [\"...\"]}}]}}"
        ),
    },
}


async def get_prompt_template(feature: str) -> dict:
    """
    Loads the active prompt template for a feature from Firestore.
    Falls back to DEFAULT_TEMPLATES if not found.
    Returns: { "id": str, "version": str, "template_text": str }
    """
    db = get_db()
    query = (
        db.collection("prompt_templates")
        .where("feature", "==", feature)
        .where("is_active", "==", True)
        .limit(1)
    )
    docs = [doc async for doc in query.stream()]

    if docs:
        data = docs[0].to_dict()
        return {
            "id": docs[0].id,
            "version": data.get("version", "v1"),
            "template_text": data["template_text"],
        }

    # Fallback to defaults
    default = DEFAULT_TEMPLATES.get(feature, {"version": "v1", "template_text": "{prompt}"})
    return {
        "id": f"default_{feature}",
        "version": default["version"],
        "template_text": default["template_text"],
    }
