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
WEBHOOK_URL = f"{settings.webhook_url}{WEBHOOK_PATH}"

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


async def on_startup(app: web.Application):
    """Webhook o'rnatish"""
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")


async def on_shutdown(app: web.Application):
    """Webhook o'chirish"""
    await bot.delete_webhook()
    logger.info("Webhook o'chirildi")


async def init_app():
    """Routerlar va database"""
    
    dp.include_router(user_menu_router)
    dp.include_router(codes_router)
    dp.include_router(vip_router)
    dp.include_router(admin_router)

    logger.info("Database ishga tushmoqda...")
    await init_db()


async def create_app():
    """Aiohttp ilovasini yaratish"""
    
    await init_app()

    app = web.Application()

    # Webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )

    webhook_handler.register(app, path=WEBHOOK_PATH)

    # Dispatcher integratsiyasi
    setup_application(app, dp, bot=bot)

    # Startup / shutdown
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Health check (Render uchun)
    async def health(request):
        return web.Response(text="Bot is running")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    return app


async def main():
    """Serverni ishga tushirish"""
    
    app = await create_app()

    port = int(os.environ.get("PORT", 8080))

    logger.info(f"Server {port} portda ishga tushdi")

    web.run_app(
        app,
        host="0.0.0.0",
        port=port
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
