from typing import List, Optional
from google.cloud import firestore
from datetime import datetime, timezone

_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db

PIPELINE_STEPS = [
    "serp_analyze",
    "intent_detect",
    "outline_generate",
    "content_generate",
    "score",
    "optimization",
]


async def get_pipeline_state(project_id: str) -> List[dict]:
    db = get_db()
    doc = await db.collection("projects").document(project_id).get()
    if not doc.exists:
        return []
    data = doc.to_dict()
    return data.get("pipeline_steps", [
        {"step": s, "status": "not_started"} for s in PIPELINE_STEPS
    ])


async def mark_step(project_id: str, step: str, status: str, result_ref: Optional[str] = None):
    """
    Mark a pipeline step as pending/done/failed.
    Stored inside the project document for easy polling.
    """
    db = get_db()
    doc_ref = db.collection("projects").document(project_id)
    doc = await doc_ref.get()
    steps: List[dict] = doc.to_dict().get("pipeline_steps", [
        {"step": s, "status": "not_started"} for s in PIPELINE_STEPS
    ])

    for s in steps:
        if s["step"] == step:
            s["status"] = status
            if result_ref:
                s["result_ref"] = result_ref
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            break

    await doc_ref.update({"pipeline_steps": steps})


async def run_full_pipeline(
    project_id: str,
    keyword: str,
    uid: str,
) -> dict:
    """
    Executes the full analysis pipeline step by step.
    Each step's result is persisted before the next begins.
    On retry, completed steps are skipped automatically.

    Steps:
      1. serp_analyze   → Scrape and cache SERP data
      2. intent_detect  → Classify search intent
      3. outline_generate → Generate AI outline
      4. content_generate → Generate full article
      5. score          → Run SEO scoring

    NOTE: Steps run synchronously in-request for MVP.
    Future: dispatch each step to Redis/RQ for durability.
    """
    from app.services.serp.direct_scraper import DirectScraperProvider
    from app.services.serp.serp_api import SerpApiProvider
    from app.services.intent_service import classify_intent
    from app.llm.service import llm_service
    from app.rag.chunker import chunk_text
    from app.rag.embedder import embed_texts, embed_single
    from app.rag.pgvector_store import store_embeddings, retrieve_similar
    from app.services.scoring.scorer import score_content
    from app.core.config import settings
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal

    db = get_db()
    steps = await get_pipeline_state(project_id)
    done = {s["step"] for s in steps if s["status"] == "done"}

    # ── Step 1: SERP Analysis ─────────────────────────────────────────────
    if "serp_analyze" not in done:
        await mark_step(project_id, "serp_analyze", "pending")
        provider = (SerpApiProvider() if settings.serp_provider == "api"
                    else DirectScraperProvider())
        serp_results = await provider.fetch(keyword)
        competitor_texts = [r.raw_text or "" for r in serp_results]

        # Cache in Firestore
        await db.collection("serp_data").document(project_id).set({
            "project_id": project_id,
            "keyword": keyword,
            "results": [r.model_dump() for r in serp_results],
            "cached_at": datetime.now(timezone.utc),
        })
        await mark_step(project_id, "serp_analyze", "done", f"serp_data/{project_id}")
    else:
        doc = await db.collection("serp_data").document(project_id).get()
        from app.models.schemas import SERPResult
        competitor_texts = [r.get("raw_text", "") for r in doc.to_dict().get("results", [])]

    # ── Step 2: Intent Detection ──────────────────────────────────────────
    if "intent_detect" not in done:
        await mark_step(project_id, "intent_detect", "pending")
        intent = await classify_intent(keyword)
        await db.collection("projects").document(project_id).update({
            "intent": intent.value,
        })
        await mark_step(project_id, "intent_detect", "done")
    else:
        proj_doc = await db.collection("projects").document(project_id).get()
        from app.models.schemas import SearchIntent
        intent = SearchIntent(proj_doc.to_dict().get("intent", "informational"))

    # ── Embed competitor content into pgvector ────────────────────────────
    all_text = " ".join(competitor_texts)
    chunks = chunk_text(all_text)
    if chunks:
        vectors = await embed_texts(chunks)
        await store_embeddings(project_id, chunks, vectors)

    competitor_context = all_text[:4000]

    # ── Step 3: Outline Generation ────────────────────────────────────────
    if "outline_generate" not in done:
        await mark_step(project_id, "outline_generate", "pending")
        outline, outline_prompt_ver = await llm_service.generate_outline(
            uid=uid, keyword=keyword, intent=intent,
            competitor_context=competitor_context,
        )
        await db.collection("projects").document(project_id).update({
            "outline": outline,
            "outline_prompt_ver": outline_prompt_ver,
        })
        await mark_step(project_id, "outline_generate", "done")
    else:
        proj_doc = await db.collection("projects").document(project_id).get()
        outline = proj_doc.to_dict().get("outline", [])

    # ── Step 4: Article Generation ────────────────────────────────────────
    if "content_generate" not in done:
        await mark_step(project_id, "content_generate", "pending")
        article_data, article_prompt_ver = await llm_service.generate_article(
            uid=uid, keyword=keyword, intent=intent, outline=outline,
        )

        # Get next version number
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT COALESCE(MAX(version_num),0)+1 FROM article_versions WHERE project_id=:pid"),
                {"pid": project_id},
            )
            version_num = result.scalar()

            await session.execute(
                text("""
                    INSERT INTO article_versions (project_id, version_num, content_text, prompt_ver)
                    VALUES (:pid, :v, :content, :pv)
                """),
                {
                    "pid": project_id,
                    "v": version_num,
                    "content": article_data.get("content", ""),
                    "pv": article_prompt_ver,
                },
            )
            await session.commit()

        await db.collection("projects").document(project_id).update({
            "status": "GENERATED",
            "meta_title": article_data.get("meta_title", ""),
            "meta_description": article_data.get("meta_description", ""),
            "current_version": version_num,
        })
        await mark_step(project_id, "content_generate", "done")
    else:
        proj_doc = await db.collection("projects").document(project_id).get()
        proj_data = proj_doc.to_dict()
        version_num = proj_data.get("current_version", 1)
        article_data = {
            "meta_title": proj_data.get("meta_title", ""),
            "meta_description": proj_data.get("meta_description", ""),
        }
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT content_text FROM article_versions WHERE project_id=:pid AND version_num=:v"),
                {"pid": project_id, "v": version_num},
            )
            row = result.fetchone()
            article_data["content"] = row[0] if row else ""

    # ── Step 5: Scoring ───────────────────────────────────────────────────
    if "score" not in done:
        await mark_step(project_id, "score", "pending")
        score_result = await score_content(
            uid=uid,
            project_id=project_id,
            keyword=keyword,
            article=article_data.get("content", ""),
            meta_title=article_data.get("meta_title", ""),
            meta_description=article_data.get("meta_description", ""),
            competitor_context=competitor_context,
            version_num=version_num,
        )
        await db.collection("seo_reports").document(project_id).set({
            **score_result,
            "project_id": project_id,
            "version_num": version_num,
            "created_at": datetime.now(timezone.utc),
        })
        await db.collection("projects").document(project_id).update({"status": "SCORED"})
        await mark_step(project_id, "score", "done")
    else:
        report_doc = await db.collection("seo_reports").document(project_id).get()
        score_result = report_doc.to_dict() if report_doc.exists else {}

    return {
        "project_id": project_id,
        "intent": intent.value,
        "version_num": version_num,
        "score": score_result,
    }
