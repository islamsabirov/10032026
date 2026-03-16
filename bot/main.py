import sys
import os
import logging
from aiohttp import web

# Root va bot papkalarni import yo‘lida qo‘shish
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings
from db import init_db
from handlers import admin_router, codes_router, user_menu_router, vip_router

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Webhook sozlamalari
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{settings.webhook_url}{WEBHOOK_PATH}"

# Bot va Dispatcher
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Routers
dp.include_router(user_menu_router)
dp.include_router(codes_router)
dp.include_router(vip_router)
dp.include_router(admin_router)

async def on_startup(app: web.Application):
    """Webhook o'rnatish va DB ishga tushirish"""
    logger.info("Database ishga tushmoqda...")
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    """Webhook o'chirish va sessiyalarni yopish"""
    await bot.delete_webhook()
    await bot.session.close()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("Webhook va sessiyalar yopildi")

def create_app() -> web.Application:
    """Aiohttp ilovasini yaratish"""
    app = web.Application()
    
    # Webhook handler
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Server {port}-portda ishga tushmoqda...")
    web.run_app(create_app(), host="0.0.0.0", port=port)
