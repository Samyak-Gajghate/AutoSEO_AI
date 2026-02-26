"""
Iterative Optimization Service

Allows re-generating specific parts of an existing article:
  - outline only  → re-generate outline, keep article
  - article only  → re-generate article from existing outline
  - full          → re-generate both outline + article
  - score         → re-score without regeneration

Each call increments the Neon `article_versions` version number
so the full history is preserved.
"""
from typing import Literal
from datetime import datetime, timezone
from sqlalchemy import text
from google.cloud import firestore
from app.core.database import AsyncSessionLocal
from app.llm.service import llm_service
from app.models.schemas import SearchIntent

OptimizeTarget = Literal["outline", "article", "full", "score"]

_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db


async def optimize_content(
    uid: str,
    project_id: str,
    target: OptimizeTarget = "full",
    custom_instructions: str = "",
) -> dict:
    """
    Re-generates the requested part of the project content.

    Args:
        uid:                  Firebase UID of the requesting user.
        project_id:           Project to optimize.
        target:               What to regenerate: outline|article|full|score
        custom_instructions:  Optional extra instructions appended to prompts.

    Returns:
        Updated version dict with new_version_num and score.
    """
    db = get_db()

    # ── Load project ──────────────────────────────────────────────────────────
    doc = await db.collection("projects").document(project_id).get()
    if not doc.exists:
        raise ValueError(f"Project {project_id} not found.")
    proj = doc.to_dict()

    keyword = proj.get("keyword", "")
    intent = SearchIntent(proj.get("intent", "informational"))
    current_outline = proj.get("outline", [])

    # ── Load current article text from Neon ───────────────────────────────────
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT content_text, version_num
                FROM article_versions
                WHERE project_id = :pid
                ORDER BY version_num DESC LIMIT 1
            """),
            {"pid": project_id},
        )
        row = result.fetchone()
        current_content = row[0] if row else ""
        current_version = row[1] if row else 0

    new_version = current_version + 1

    # ── SERP context from Firestore cache ────────────────────────────────────
    serp_doc = await db.collection("serp_data").document(project_id).get()
    competitor_context = ""
    if serp_doc.exists:
        results = serp_doc.to_dict().get("results", [])
        competitor_context = " ".join(r.get("raw_text", "") for r in results)[:4000]

    # ── Step: Re-generate outline ─────────────────────────────────────────────
    new_outline = current_outline
    if target in ("outline", "full"):
        # Inject custom instructions into competitor context
        ctx = competitor_context
        if custom_instructions:
            ctx = f"User instructions: {custom_instructions}\n\n{ctx}"

        new_outline, outline_ver = await llm_service.generate_outline(
            uid=uid,
            keyword=keyword,
            intent=intent,
            competitor_context=ctx,
        )
        await db.collection("projects").document(project_id).update({
            "outline": new_outline,
            "outline_prompt_ver": outline_ver,
            "updated_at": datetime.now(timezone.utc),
        })

    # ── Step: Re-generate article ─────────────────────────────────────────────
    new_content = current_content
    meta_title = proj.get("meta_title", "")
    meta_description = proj.get("meta_description", "")

    if target in ("article", "full"):
        article_data, article_ver = await llm_service.generate_article(
            uid=uid,
            keyword=keyword,
            intent=intent,
            outline=new_outline,
        )
        new_content = article_data.get("content", "")
        meta_title = article_data.get("meta_title", meta_title)
        meta_description = article_data.get("meta_description", meta_description)

        await db.collection("projects").document(project_id).update({
            "meta_title": meta_title,
            "meta_description": meta_description,
            "current_version": new_version,
            "status": "GENERATED",
            "updated_at": datetime.now(timezone.utc),
        })

    # ── Persist new version in Neon ───────────────────────────────────────────
    if target in ("article", "full"):
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO article_versions
                        (project_id, version_num, content_text)
                    VALUES (:pid, :v, :content)
                """),
                {"pid": project_id, "v": new_version, "content": new_content},
            )
            await session.commit()
    else:
        new_version = current_version  # No new version for outline-only or score-only

    # ── Step: Re-score ────────────────────────────────────────────────────────
    from app.services.scoring.scorer import score_content
    score_result = await score_content(
        uid=uid,
        project_id=project_id,
        keyword=keyword,
        article=new_content,
        meta_title=meta_title,
        meta_description=meta_description,
        competitor_context=competitor_context,
        version_num=new_version,
    )

    # Update project status to OPTIMIZED if this was a re-run
    await db.collection("projects").document(project_id).update({
        "status": "OPTIMIZED",
        "seo_score": score_result["combined_score"],
        "updated_at": datetime.now(timezone.utc),
    })

    return {
        "project_id": project_id,
        "target": target,
        "new_version_num": new_version,
        "score": score_result,
    }
