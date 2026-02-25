from app.llm.service import llm_service
from app.rag.embedder import embed_single
from app.rag.pgvector_store import retrieve_similar


async def analyze_content_gap(
    uid: str,
    project_id: str,
    keyword: str,
    article: str,
) -> dict:
    """
    1. Embeds the user's article
    2. Retrieves competitor chunks from pgvector for this project
    3. LLM identifies missing subtopics, weak sections, semantic gaps
    Returns gap analysis dict.
    """
    # Get competitor context from pgvector
    article_vector = await embed_single(article[:3000])
    competitor_chunks = await retrieve_similar(
        project_id=project_id,
        query_vector=article_vector,
        top_k=10,
    )
    competitor_context = "\n---\n".join(competitor_chunks)

    return await llm_service.suggest_improvements(
        uid=uid,
        keyword=keyword,
        article=article,
        competitor_context=competitor_context,
    )
