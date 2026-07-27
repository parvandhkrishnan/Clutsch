"""Database engine, session factory, and connection pooling for Clutsch."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Connection string from environment, with a sensible local-dev default
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://clutsch:clutsch_dev_2024@localhost:5432/clutsch"
)

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