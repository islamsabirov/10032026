import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Lokal paketlardan import (paket sifatida ishga tushirilganda ishlaydi)
from bot.config import settings
from bot.db import init_db
from bot.handlers import admin_router, codes_router, user_menu_router, vip_router


# Logging sozlamasi
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Asosiy bot funksiyasi: botni ishga tushiradi, dispatcher va routerlarni sozlaydi, DB bilan ulashadi."""
    logger.info("Bot ishga tushmoqda...")

    # Bot yaratish
    bot = Bot(
        token=settings.bot_token,
        parse_mode=ParseMode.HTML
    )

    # Dispatcher (FSM storage bilan)
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    routers = [user_menu_router, codes_router, vip_router, admin_router]
    for router in routers:
        dp.include_router(router)

    # Database ishga tushirish
    logger.info("Database ishga tushmoqda...")
    await init_db()

    # Bot polling boshlash
    logger.info("Bot polling boshladi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        # Paket sifatida ishga tushirilganda asyncio.run orqali asosiy funksiya ishga tushadi
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
