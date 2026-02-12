import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
# Set scraper/pipeline loggers to INFO, httpx to WARNING
logging.getLogger("app.scrapers").setLevel(logging.INFO)
logging.getLogger("app.pipeline").setLevel(logging.INFO)
logging.getLogger("app.services").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from .pipeline.scheduler import start_scheduler

    start_scheduler()
    yield
    from .pipeline.scheduler import shutdown_scheduler

    shutdown_scheduler()


app = FastAPI(
    title="ASEAN Trade Monitor",
    description="News aggregation and analysis platform for Russia-ASEAN trade cooperation research",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .api import analytics, news, scrape, summarize, tags  # noqa: E402

app.include_router(news.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(summarize.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
