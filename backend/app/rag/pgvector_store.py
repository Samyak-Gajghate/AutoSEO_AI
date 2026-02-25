from typing import List
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def store_embeddings(project_id: str, chunks: List[str], vectors: List[List[float]]):
    """
    Batch-upserts chunks and their embedding vectors into Neon pgvector.
    Old embeddings for this project_id are replaced to keep the store fresh.
    """
    async with AsyncSessionLocal() as session:
        # Clear existing embeddings for this project
        await session.execute(
            text("DELETE FROM embeddings WHERE project_id = :pid"),
            {"pid": project_id},
        )

        # Batch insert new embeddings
        for chunk, vector in zip(chunks, vectors):
            await session.execute(
                text("""
                    INSERT INTO embeddings (project_id, chunk_text, embedding)
                    VALUES (:pid, :chunk, :vec::vector)
                """),
                {
                    "pid": project_id,
                    "chunk": chunk,
                    "vec": str(vector),
                },
            )

        await session.commit()


async def retrieve_similar(
    project_id: str,
    query_vector: List[float],
    top_k: int = 8,
) -> List[str]:
    """
    Retrieves top-k most similar chunks for a given query vector using
    cosine similarity via pgvector's <=> operator.

    Returns a list of chunk text strings ordered by similarity.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT chunk_text
                FROM embeddings
                WHERE project_id = :pid
                ORDER BY embedding <=> :vec::vector
                LIMIT :k
            """),
            {
                "pid": project_id,
                "vec": str(query_vector),
                "k": top_k,
            },
        )
        rows = result.fetchall()
        return [row[0] for row in rows]
