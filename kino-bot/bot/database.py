import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings

# ======================
# DB fayl pathini tekshirish
# ======================
db_file = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
db_dir = os.path.dirname(db_file)
if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# ======================
# Async engine va session
# ======================
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# ======================
# Base model
# ======================
class Base(DeclarativeBase):
    pass

# ======================
# DB yaratish
# ======================
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)