import httpx
from typing import List
from app.services.serp.provider import SERPProvider
from app.models.schemas import SERPResult
from app.core.config import settings


class SerpApiProvider(SERPProvider):
    """
    Production-grade SERP provider using SerpApi (serpapi.com) or ValueSERP.
    Activate by setting SERP_PROVIDER=api in your .env.

    Advantages over DirectScraperProvider:
    - Reliable across all keywords
    - No anti-bot issues
    - Returns structured JSON — no HTML parsing needed
    - Works with JS-rendered pages
    """

    BASE_URL = "https://serpapi.com/search"

    async def fetch(self, keyword: str, top_n: int = 5) -> List[SERPResult]:
        if not settings.serp_api_key:
            raise ValueError("SERP_API_KEY is required when SERP_PROVIDER=api")

        params = {
            "q": keyword,
            "api_key": settings.serp_api_key,
            "num": top_n,
            "hl": "en",
            "gl": "us",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:top_n]:
            results.append(SERPResult(
                url=item.get("link", ""),
                title=item.get("title"),
                meta_description=item.get("snippet"),
                h1=[item.get("title", "")],
                h2=[],
                h3=[],
                word_count=0,    # SerpApi doesn't return full page content
                faq_items=[],
                raw_text=item.get("snippet", ""),
            ))
        return results
