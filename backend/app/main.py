from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limiter import limiter
from app.core.config import settings
from app.core.database import init_db
from app.api.routes.projects import router as projects_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoSEO AI API",
        description="AI-powered autonomous SEO optimization platform",
        version="1.0.0",
    )

    # ── Rate Limiter ──────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────────
    app.include_router(projects_router, prefix="/api/v1", tags=["projects"])

    # ── Startup ───────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        await init_db()

    # ── Health Check ──────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
