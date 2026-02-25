from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# Rate limiter instance — used as a decorator on routes
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
        headers={"Retry-After": "60"},
    )


# Per-route limits (import and use as decorators):
#   @limiter.limit("30/minute")   -- standard API calls
#   @limiter.limit("10/minute")   -- heavy LLM generation routes
STANDARD_LIMIT = "30/minute"
GENERATION_LIMIT = "10/minute"
EDIT_LIMIT = "20/minute"

# Request body guards
MAX_ARTICLE_LENGTH_WORDS = 5000
MAX_CHUNK_COUNT = 50
MAX_TOKENS_PER_REQUEST = 10_000
