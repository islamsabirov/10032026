from sqlalchemy.ext.asyncio import AsyncEngine

from .base import Base, engine


async def init_db(db_engine: AsyncEngine | None = None) -> None:
    """Create all database tables."""
    eng = db_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
