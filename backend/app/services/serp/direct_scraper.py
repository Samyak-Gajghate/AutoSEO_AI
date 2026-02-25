import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.services.serp.provider import SERPProvider
from app.models.schemas import SERPResult

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

GOOGLE_SEARCH_URL = "https://www.google.com/search"


class DirectScraperProvider(SERPProvider):
    """
    Fetches SERP via direct HTTP + BeautifulSoup.
    Works well for MVP. For production reliability swap to SerpApiProvider.
    Falls back to partial content on individual page failures.
    """

    async def fetch(self, keyword: str, top_n: int = 5) -> List[SERPResult]:
        urls = await self._get_serp_urls(keyword, top_n)
        tasks = [self._scrape_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, SERPResult)]

    async def _get_serp_urls(self, keyword: str, top_n: int) -> List[str]:
        """
        Scrapes Google Search results page to extract top organic URLs.
        Note: This is best-effort. For reliability use SerpApiProvider.
        """
        params = {"q": keyword, "num": top_n + 2, "hl": "en"}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                resp = await client.get(GOOGLE_SEARCH_URL, params=params, headers=HEADERS)
                soup = BeautifulSoup(resp.text, "html.parser")
                urls = []
                for a in soup.select("a[href]"):
                    href = a["href"]
                    if href.startswith("/url?q="):
                        url = href.split("/url?q=")[1].split("&")[0]
                        if url.startswith("http") and "google.com" not in url:
                            urls.append(url)
                        if len(urls) >= top_n:
                            break
                return urls
            except Exception:
                return []

    async def _scrape_url(self, url: str) -> SERPResult:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=HEADERS)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Extract headings
                h1 = [t.get_text(strip=True) for t in soup.find_all("h1")]
                h2 = [t.get_text(strip=True) for t in soup.find_all("h2")]
                h3 = [t.get_text(strip=True) for t in soup.find_all("h3")]

                # Raw text
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                raw_text = soup.get_text(separator=" ", strip=True)
                word_count = len(raw_text.split())

                # FAQ items
                faq_items = []
                for el in soup.select("[itemtype*='FAQPage'] .faq-question, details summary, .faq h3"):
                    faq_items.append(el.get_text(strip=True))

                # Meta
                title_tag = soup.find("title")
                meta_desc = soup.find("meta", attrs={"name": "description"})

                return SERPResult(
                    url=url,
                    title=title_tag.get_text(strip=True) if title_tag else None,
                    meta_description=meta_desc["content"] if meta_desc and meta_desc.get("content") else None,
                    h1=h1[:5],
                    h2=h2[:15],
                    h3=h3[:20],
                    word_count=word_count,
                    faq_items=faq_items[:10],
                    raw_text=raw_text[:8000],  # cap to avoid huge payloads
                )
            except Exception as e:
                # Graceful degradation: return partial result
                return SERPResult(url=url, raw_text=f"[Scrape failed: {e}]")
