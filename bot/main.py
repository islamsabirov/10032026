import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings
from .db import init_db
from .handlers import admin_router, codes_router, user_menu_router, vip_router


# Logging sozlamasi
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Bot ishga tushmoqda...")

    # Bot yaratish
    bot = Bot(
        token=settings.bot_token,
        parse_mode=ParseMode.HTML
    )

    # Dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    dp.include_router(user_menu_router)
    dp.include_router(codes_router)
    dp.include_router(vip_router)
    dp.include_router(admin_router)

    # Database ishga tushirish
    logger.info("Database ishga tushmoqda...")
    await init_db()

    # Bot polling
    logger.info("Bot polling boshladi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")