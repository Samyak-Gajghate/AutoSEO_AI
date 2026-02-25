from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.core.rate_limiter import limiter, STANDARD_LIMIT, GENERATION_LIMIT
from app.core.token_budget import enforce_budget
from app.models.schemas import (
    CreateProjectRequest, ProjectResponse, ProjectStatus,
    AnalyzeSERPRequest, AnalyzeSERPResponse,
    GenerateOutlineRequest, GenerateOutlineResponse,
    GenerateContentRequest, GenerateContentResponse,
    ScoreContentRequest, SEOScoreResponse,
    SuggestEditRequest, SuggestEditResponse, EditVariation,
    AuthorityScoreResponse, AuthorityCluster,
    TokenUsageSummary, PipelineStatusResponse,
)
from google.cloud import firestore

router = APIRouter()
_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=dict)
async def create_project(
    body: CreateProjectRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new keyword project for the current user."""
    db = get_db()
    now = datetime.now(timezone.utc)
    doc_ref = db.collection("projects").document()
    await doc_ref.set({
        "user_id": user["uid"],
        "keyword": body.keyword,
        "status": ProjectStatus.draft.value,
        "created_at": now,
        "updated_at": now,
        "pipeline_steps": [],
    })
    return {"id": doc_ref.id, "keyword": body.keyword, "status": "DRAFT"}


@router.get("/projects", response_model=list)
async def list_projects(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = db.collection("projects").where("user_id", "==", user["uid"]).stream()
    projects = []
    async for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        projects.append(d)
    return projects


@router.get("/projects/{project_id}", response_model=dict)
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.collection("projects").document(project_id).get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(404, "Project not found.")
    d = doc.to_dict()
    d["id"] = project_id
    return d


@router.get("/projects/{project_id}/pipeline", response_model=dict)
async def get_pipeline_status(project_id: str, user: dict = Depends(get_current_user)):
    from app.services.pipeline_service import get_pipeline_state
    db = get_db()
    doc = await db.collection("projects").document(project_id).get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(404, "Project not found.")
    steps = await get_pipeline_state(project_id)
    return {"project_id": project_id, "steps": steps}


# ── Full Pipeline ─────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/run")
async def run_pipeline(project_id: str, user: dict = Depends(get_current_user)):
    """
    Runs the full pipeline: SERP → intent → outline → content → score.
    Each step is stored before the next begins (retry-safe).
    """
    await enforce_budget(user["uid"], "article")
    db = get_db()
    doc = await db.collection("projects").document(project_id).get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(404, "Project not found.")

    from app.services.pipeline_service import run_full_pipeline
    result = await run_full_pipeline(
        project_id=project_id,
        keyword=doc.to_dict()["keyword"],
        uid=user["uid"],
    )
    return result


# ── Content Gap ───────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/analyze-gap")
async def analyze_gap(project_id: str, user: dict = Depends(get_current_user)):
    await enforce_budget(user["uid"], "gap")
    db = get_db()
    doc = await db.collection("projects").document(project_id).get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(404, "Project not found.")

    proj = doc.to_dict()
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT content_text FROM article_versions WHERE project_id=:pid ORDER BY version_num DESC LIMIT 1"),
            {"pid": project_id},
        )
        row = result.fetchone()
        article = row[0] if row else ""

    from app.services.gap_service import analyze_content_gap
    gap = await analyze_content_gap(
        uid=user["uid"],
        project_id=project_id,
        keyword=proj["keyword"],
        article=article,
    )
    return gap


# ── AI-Assisted Editing ───────────────────────────────────────────────────────

@router.post("/suggest-edit", response_model=SuggestEditResponse)
async def suggest_edit(
    body: SuggestEditRequest,
    user: dict = Depends(get_current_user),
):
    await enforce_budget(user["uid"], "edit")
    from app.llm.service import llm_service
    variations_raw = await llm_service.suggest_paragraph_variations(
        uid=user["uid"],
        paragraph=body.paragraph,
        surrounding_context=body.surrounding_context,
    )
    variations = [EditVariation(**v) for v in variations_raw[:3]]
    return SuggestEditResponse(variations=variations)


# ── Topical Authority ─────────────────────────────────────────────────────────

@router.get("/authority-score", response_model=AuthorityScoreResponse)
async def get_authority_score(user: dict = Depends(get_current_user)):
    await enforce_budget(user["uid"], "authority")
    from app.services.authority_service import compute_authority_score
    clusters_raw = await compute_authority_score(uid=user["uid"])
    clusters = [AuthorityCluster(**c) for c in clusters_raw]
    return AuthorityScoreResponse(user_id=user["uid"], clusters=clusters)


# ── Token Usage ───────────────────────────────────────────────────────────────

@router.get("/usage", response_model=TokenUsageSummary)
async def get_usage_summary(user: dict = Depends(get_current_user)):
    from app.utils.token_tracker import get_monthly_summary
    summary = await get_monthly_summary(user["uid"])
    return TokenUsageSummary(**summary)
