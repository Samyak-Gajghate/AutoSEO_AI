import json
import time
import asyncio
from typing import List, Optional
import openai
from app.core.config import settings
from app.llm.prompt_manager import get_prompt_template
from app.utils.token_tracker import log_usage
from app.models.schemas import SearchIntent

MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # seconds (doubled each retry)


class LLMService:
    """
    Central AI orchestration layer.
    All LLM calls in the app go through this class.
    Handles: prompt loading, token budgets, retries, cost logging.
    """

    def __init__(self):
        self._client: Optional[openai.AsyncOpenAI] = None

    def client(self) -> openai.AsyncOpenAI:
        if not self._client:
            self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

    async def _call(
        self,
        uid: str,
        feature: str,
        prompt: str,
        system: str = "You are a helpful SEO assistant.",
        max_tokens: int = 2000,
        temperature: float = 0.4,
    ) -> tuple[str, str]:
        """
        Internal method. Calls GPT-4o-mini with retry + cost logging.
        Returns (response_text, prompt_version).
        """
        template = await get_prompt_template(feature)
        prompt_version = template["version"]

        for attempt in range(MAX_RETRIES):
            try:
                t0 = time.time()
                response = await self.client().chat.completions.create(
                    model="gpt-4o-mini",
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                )
                latency_ms = int((time.time() - t0) * 1000)

                usage = response.usage
                await log_usage(
                    uid=uid,
                    feature=feature,
                    tokens_in=usage.prompt_tokens,
                    tokens_out=usage.completion_tokens,
                    model="gpt-4o-mini",
                    latency_ms=latency_ms,
                )

                return response.choices[0].message.content, prompt_version

            except (openai.RateLimitError, openai.APIConnectionError) as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(RETRY_BACKOFF * (2 ** attempt))

    # ─── Public Methods ───────────────────────────────────────────────────────

    async def classify_intent(self, keyword: str, uid: str = "system") -> str:
        """LLM fallback for intent classification (heuristics run first)."""
        template = await get_prompt_template("intent")
        prompt = template["template_text"].format(keyword=keyword)
        raw, _ = await self._call(uid, "intent", prompt, max_tokens=50)
        data = json.loads(raw)
        return data.get("intent", "informational")

    async def generate_outline(
        self,
        uid: str,
        keyword: str,
        intent: SearchIntent,
        competitor_context: str,
    ) -> tuple[List[dict], str]:
        """Returns (outline_items, prompt_version)."""
        template = await get_prompt_template("outline")
        prompt = template["template_text"].format(
            intent=intent.value,
            keyword=keyword,
            competitor_context=competitor_context[:4000],
        )
        raw, prompt_ver = await self._call(uid, "outline", prompt, max_tokens=1500)
        data = json.loads(raw)
        return data.get("outline", []), prompt_ver

    async def generate_article(
        self,
        uid: str,
        keyword: str,
        intent: SearchIntent,
        outline: List[dict],
    ) -> tuple[dict, str]:
        """Returns ({"content", "meta_title", "meta_description"}, prompt_version)."""
        template = await get_prompt_template("article")
        outline_text = "\n".join(
            f"{'#' * item.get('level', 2)} {item.get('heading', '')}"
            for item in outline
        )
        prompt = template["template_text"].format(
            intent=intent.value,
            keyword=keyword,
            outline=outline_text,
        )
        raw, prompt_ver = await self._call(uid, "article", prompt, max_tokens=4000)
        data = json.loads(raw)
        return data, prompt_ver

    async def evaluate_content(
        self,
        uid: str,
        keyword: str,
        article: str,
        competitor_context: str,
    ) -> tuple[int, List[str], str]:
        """Returns (ai_score, feedback_points, prompt_version)."""
        template = await get_prompt_template("score")
        prompt = template["template_text"].format(
            keyword=keyword,
            competitor_context=competitor_context[:3000],
            article=article[:6000],
        )
        raw, prompt_ver = await self._call(uid, "score", prompt, max_tokens=600)
        data = json.loads(raw)
        return data.get("ai_score", 50), data.get("feedback_points", []), prompt_ver

    async def suggest_improvements(
        self,
        uid: str,
        keyword: str,
        article: str,
        competitor_context: str,
    ) -> dict:
        """Returns gap analysis dict."""
        template = await get_prompt_template("gap")
        prompt = template["template_text"].format(
            keyword=keyword,
            competitor_context=competitor_context[:3000],
            article=article[:5000],
        )
        raw, _ = await self._call(uid, "gap", prompt, max_tokens=600)
        return json.loads(raw)

    async def suggest_paragraph_variations(
        self,
        uid: str,
        paragraph: str,
        surrounding_context: str,
    ) -> List[dict]:
        """Returns list of 3 variation dicts {text, reasoning}."""
        template = await get_prompt_template("edit")
        prompt = template["template_text"].format(
            surrounding_context=surrounding_context[:3000],
            paragraph=paragraph,
        )
        raw, _ = await self._call(uid, "edit", prompt, max_tokens=800)
        data = json.loads(raw)
        return data.get("variations", [])


# Singleton instance used across the app
llm_service = LLMService()
