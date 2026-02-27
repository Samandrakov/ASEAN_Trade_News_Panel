from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
)


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

    # FTS5 virtual table for full-text search
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
            USING fts5(title, body, content='articles', content_rowid='id')
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ai
            AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, body)
                VALUES (new.id, new.title, new.body);
            END
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ad
            AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, body)
                VALUES ('delete', old.id, old.title, old.body);
            END
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_au
            AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, body)
                VALUES ('delete', old.id, old.title, old.body);
                INSERT INTO articles_fts(rowid, title, body)
                VALUES (new.id, new.title, new.body);
            END
        """))
        # Populate FTS for already-existing articles
        await conn.execute(text(
            "INSERT OR IGNORE INTO articles_fts(articles_fts) VALUES('rebuild')"
        ))

    # Lightweight schema migrations for columns added after initial deploy
    _migrations = [
        "ALTER TABLE scrape_maps ADD COLUMN cron_expression VARCHAR(128)",
        "ALTER TABLE scrape_maps ADD COLUMN feed_type VARCHAR(32) DEFAULT 'sitemap'",
        # User isolation for bookmarks and alerts
        "ALTER TABLE article_bookmarks ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE",
        "ALTER TABLE alerts ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE",
        # Indexes for scrape_runs
        "CREATE INDEX IF NOT EXISTS ix_scrape_runs_source ON scrape_runs(source)",
        "CREATE INDEX IF NOT EXISTS ix_scrape_runs_status ON scrape_runs(status)",
        "CREATE INDEX IF NOT EXISTS ix_scrape_runs_started_at ON scrape_runs(started_at)",
        # Composite index for tag queries
        "CREATE INDEX IF NOT EXISTS ix_article_tags_type_value ON article_tags(tag_type, tag_value)",
        # Composite index for article date + country queries
        "CREATE INDEX IF NOT EXISTS ix_articles_date_country ON articles(published_date, country)",
    ]
    async with engine.begin() as conn:
        for stmt in _migrations:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column/index already exists


async def get_db():
    async with async_session() as session:
        yield session
