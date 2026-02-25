from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncSession:
    """FastAPI dependency for DB sessions."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """
    Run once on startup. Creates pgvector extension and all tables.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id  TEXT NOT NULL,
                chunk_text  TEXT NOT NULL,
                embedding   vector(1536)
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS embeddings_ivfflat_idx
            ON embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS article_versions (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id   TEXT NOT NULL,
                version_num  INT NOT NULL,
                content_text TEXT NOT NULL,
                seo_score    INT,
                prompt_ver   TEXT,
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """))
