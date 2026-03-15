import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings
from db import init_db
from handlers import admin_router, codes_router, user_menu_router, vip_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = settings.webhook_url  # .env dan o'qiladi

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())


async def on_startup():
    """Webhook o'rnatish"""
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
    logger.info(f"Webhook o'rnatildi: {WEBHOOK_URL}{WEBHOOK_PATH}")


async def on_shutdown():
    """Webhook tozalash"""
    await bot.delete_webhook()
    logger.info("Webhook o'chirildi")


async def init_app():
    """Routerlarni ulash va databaseni ishga tushirish"""
    dp.include_router(user_menu_router)
    dp.include_router(codes_router)
    dp.include_router(vip_router)
    dp.include_router(admin_router)
    
    logger.info("Database ishga tushmoqda...")
    await init_db()
    
    return dp


async def main():
    """Aiohttp serverni ishga tushirish"""
    app = web.Application()
    
    # Routers va databaseni ishga tushirish
    await init_app()
    
    # Webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Startup/shutdown eventlari
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Dispatcher va botni app ga ulash
    setup_application(app, dp, bot=bot)
    
    # Health check endpoint (Render uchun)
    async def health_check(request):
        return web.Response(text="Bot is running", status=200)
    
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Serverni ishga tushirish
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Server {port}-portda ishga tushmoqda...")
    
    return app


if __name__ == "__main__":
    try:
        app = asyncio.run(main())
        web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
