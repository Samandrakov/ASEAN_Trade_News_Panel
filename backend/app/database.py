from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False,
    pool_size=2,
    max_overflow=3,
    pool_recycle=300,
)

# Enable WAL mode for better concurrent access
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        from . import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    # Lightweight migrations for new columns
    async with engine.begin() as conn:
        try:
            await conn.execute(
                text("ALTER TABLE scrape_maps ADD COLUMN cron_expression VARCHAR(128)")
            )
        except Exception:
            pass  # Column already exists


async def get_db():
    async with async_session() as session:
        yield session
