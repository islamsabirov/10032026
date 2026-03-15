```python
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from .config import settings
from .db import init_db
from .handlers import admin_router, codes_router, user_menu_router, vip_router


# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------- MAIN FUNCTION ----------------
async def main() -> None:
    logger.info("🚀 Bot ishga tushmoqda...")

    # Bot yaratish (aiogram 3.7+ uchun to'g'ri usul)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # Dispatcher yaratish
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    dp.include_router(user_menu_router)
    dp.include_router(codes_router)
    dp.include_router(vip_router)
    dp.include_router(admin_router)

    # Database ishga tushirish
    logger.info("📂 Database ishga tushmoqda...")
    await init_db()

    # Polling boshlash
    logger.info("📡 Bot polling boshladi...")
    await dp.start_polling(bot)


# ---------------- START BOT ----------------
if __name__ == "__main__":
    try:
        asyncio.run(main())

    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Bot to'xtatildi")
```
