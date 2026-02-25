import openai
from typing import List
from app.core.config import settings

_client = None


def get_openai_client():
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a list of text strings using OpenAI's
    text-embedding-3-small (1536 dimensions, cost-efficient).

    Returns a list of embedding vectors (list of floats), same order as input.
    """
    if not texts:
        return []

    client = get_openai_client()

    response = await client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )

    return [item.embedding for item in response.data]


async def embed_single(text: str) -> List[float]:
    """Convenience wrapper for embedding a single string."""
    results = await embed_texts([text])
    return results[0] if results else []
