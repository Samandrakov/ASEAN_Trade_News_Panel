import logging
import secrets
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("asean_trade_monitor.log", encoding="utf-8"),
    ],
)
logging.getLogger("app.scrapers").setLevel(logging.INFO)
logging.getLogger("app.pipeline").setLevel(logging.INFO)
logging.getLogger("app.services").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Security warnings at startup
    if settings.jwt_secret.startswith("CHANGE-ME"):
        logger.warning(
            "JWT_SECRET is using the default value! Set JWT_SECRET in .env for production."
        )
    if not settings.admin_password_hash:
        logger.warning(
            "ADMIN_PASSWORD_HASH is not set! Using default password 'admin'. "
            "Generate a hash with: python -c \"import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())\" "
            "and set ADMIN_PASSWORD_HASH in .env"
        )

    await init_db()

    from .scrapers.seed_maps import seed_default_maps

    await seed_default_maps()

    from .pipeline.scheduler import start_scheduler

    start_scheduler()
    yield
    from .pipeline.scheduler import shutdown_scheduler

    shutdown_scheduler()


app = FastAPI(
    title="ASEAN Trade Monitor",
    description="News aggregation and analysis platform for Russia-ASEAN trade cooperation research",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.jwt_secret.startswith("CHANGE-ME") else None,
    redoc_url=None,
)

# Rate limit error handler
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response(
        content='{"detail":"Too many requests. Try again later."}',
        status_code=429,
        media_type="application/json",
    )


# CORS — restricted
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


from .api import analytics, auth, feeds, news, scrape, scrape_maps, summarize, tags  # noqa: E402

app.include_router(auth.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(summarize.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(scrape_maps.router, prefix="/api")
app.include_router(feeds.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
