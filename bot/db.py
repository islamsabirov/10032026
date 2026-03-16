import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./bot.db"

# Engine yaratish
engine = create_async_engine(
    DATABASE_URL,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base model
Base = declarative_base()


# Session olish uchun
async def get_session():
    async with SessionLocal() as session:
        yield session


# DB init qilish
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
