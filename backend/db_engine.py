"""Database engine, session factory, and connection pooling for Clutsch."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

# Connection string from environment, with a sensible local-dev default.
# Managed Postgres providers (Render, Heroku, etc.) hand out a plain
# postgresql:// URL, which SQLAlchemy would default to a sync driver we
# don't install — normalize to the asyncpg dialect explicitly.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://clutsch:clutsch_dev_2024@localhost:5432/clutsch"
)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# asyncpg connections are bound to the event loop they were opened on — reusing
# a pooled connection from a different loop raises "attached to a different
# loop" / "Event loop is closed". FastAPI's TestClient (and anything else that
# doesn't run the whole process on one persistent loop, e.g. per-test
# asyncio.run() calls) can create a fresh loop per call, which pooled
# connections don't survive across. NullPool opens a new connection per
# checkout and never reuses it, sidestepping the problem — set
# SQLALCHEMY_NULL_POOL=true (the test CI workflow does this) rather than
# using it in production, where connection reuse across one stable event
# loop is what the pool_size/max_overflow tuning below is actually for.
_use_null_pool = os.environ.get("SQLALCHEMY_NULL_POOL") == "true"

if _use_null_pool:
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)
else:
    # Connection pool: 5-20 connections, 30s timeout, 10s recycle
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=15,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a session and closes it on completion."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables (for development — in production use Alembic)."""
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables (for testing)."""
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)