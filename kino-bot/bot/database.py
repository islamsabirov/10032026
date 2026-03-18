import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings

logger = logging.getLogger(__name__)

# ======================
# DB fayl pathini tekshirish (faqat SQLite uchun)
# ======================
if settings.DATABASE_URL.startswith("sqlite"):
    db_file = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_file)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"✅ DB papka yaratildi: {db_dir}")

# ======================
# Async engine va session
# ======================
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
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
    """DB yaratish yoki mavjud bo‘lsa ulanish"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized")
