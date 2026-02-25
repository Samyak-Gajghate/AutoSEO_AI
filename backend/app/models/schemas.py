from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class SearchIntent(str, Enum):
    informational = "informational"
    transactional = "transactional"
    comparison = "comparison"
    navigational = "navigational"


class ProjectStatus(str, Enum):
    draft = "DRAFT"
    analyzed = "ANALYZED"
    generated = "GENERATED"
    scored = "SCORED"
    optimized = "OPTIMIZED"
    final = "FINAL"


class PipelineStepStatus(str, Enum):
    not_started = "not_started"
    pending = "pending"
    done = "done"
    failed = "failed"


# ─── SERP ─────────────────────────────────────────────────────────────────────

class SERPResult(BaseModel):
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: List[str] = []
    h2: List[str] = []
    h3: List[str] = []
    word_count: int = 0
    faq_items: List[str] = []
    raw_text: Optional[str] = None


class AnalyzeSERPRequest(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=200)
    project_id: str


class AnalyzeSERPResponse(BaseModel):
    project_id: str
    keyword: str
    intent: SearchIntent
    results: List[SERPResult]
    cached: bool = False


# ─── Projects ─────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=200)


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    keyword: str
    intent: Optional[SearchIntent] = None
    status: ProjectStatus = ProjectStatus.draft
    created_at: datetime
    updated_at: datetime


# ─── Content ──────────────────────────────────────────────────────────────────

class GenerateOutlineRequest(BaseModel):
    project_id: str


class GenerateOutlineResponse(BaseModel):
    project_id: str
    outline: List[dict]  # [{ heading, level, notes }]
    intent: SearchIntent
    prompt_version: str


class GenerateContentRequest(BaseModel):
    project_id: str
    outline: List[dict]


class GenerateContentResponse(BaseModel):
    project_id: str
    version_num: int
    content_text: str
    word_count: int
    meta_title: str
    meta_description: str
    prompt_version: str


# ─── Scoring ──────────────────────────────────────────────────────────────────

class ScoreContentRequest(BaseModel):
    project_id: str
    version_num: int


class SEOScoreResponse(BaseModel):
    project_id: str
    version_num: int
    rule_score: int
    ai_score: int
    combined_score: int
    feedback_points: List[str]


# ─── Editing ──────────────────────────────────────────────────────────────────

class SuggestEditRequest(BaseModel):
    project_id: str
    paragraph: str = Field(..., max_length=2000)
    surrounding_context: str = Field(..., max_length=4000)


class EditVariation(BaseModel):
    text: str
    reasoning: str


class SuggestEditResponse(BaseModel):
    variations: List[EditVariation]  # always 3


# ─── Authority ────────────────────────────────────────────────────────────────

class AuthorityCluster(BaseModel):
    label: str
    keywords: List[str]
    score: float  # 0.0 – 1.0
    suggestions: List[str]


class AuthorityScoreResponse(BaseModel):
    user_id: str
    clusters: List[AuthorityCluster]


# ─── Token Usage ──────────────────────────────────────────────────────────────

class TokenUsageSummary(BaseModel):
    total_tokens: int
    total_cost_usd: float
    by_feature: dict
    month: str


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class PipelineStep(BaseModel):
    step: str
    status: PipelineStepStatus
    result_ref: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    project_id: str
    steps: List[PipelineStep]
