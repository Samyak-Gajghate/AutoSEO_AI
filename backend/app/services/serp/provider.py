from abc import ABC, abstractmethod
from typing import List
from app.models.schemas import SERPResult


class SERPProvider(ABC):
    """
    Abstract interface for SERP data providers.
    Swap implementations via SERP_PROVIDER env var:
      - "direct"  → DirectScraperProvider (BeautifulSoup)
      - "api"     → SerpApiProvider (paid API, more reliable)
    """

    @abstractmethod
    async def fetch(self, keyword: str, top_n: int = 5) -> List[SERPResult]:
        """
        Fetch top-N SERP results for a keyword.
        Returns a list of SERPResult objects.
        """
        ...
