import logging
from .base import engine, Base

logger = logging.getLogger(__name__)


async def init_db():
    """
    Barcha jadvallarni yaratadi.
    SQLAlchemy create_all() idempotent - agar jadvallar mavjud bo'lsa, qayta yaratmaydi.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database jadvallari yaratildi / tekshirildi.")
    except Exception as e:
        logger.error(f"❌ Database yaratishda xatolik: {e}")
        raise
