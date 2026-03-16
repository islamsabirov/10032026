from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

# Ma'lumotlar bazasi engine
engine = create_async_engine(
    settings.db_url,
    echo=True,
    future=True
)

# Async session maker
AsyncSessionMaker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base model deklaratsiyasi
Base = declarative_base()


async def get_session() -> AsyncSession:
    """Dependency: DB session olish"""
    async with AsyncSessionMaker() as session:
        return session
