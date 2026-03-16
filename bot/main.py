import os
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import settings
from bot.db import init_db
from bot.handlers import admin_router, codes_router, user_menu_router, vip_router


# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# WEBHOOK
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{settings.webhook_url}/webhook"


# BOT
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


# ROUTERS
dp.include_router(user_menu_router)
dp.include_router(codes_router)
dp.include_router(vip_router)
dp.include_router(admin_router)


# STARTUP
async def on_startup(app: web.Application):

    logger.info("Bot ishga tushmoqda...")

    os.makedirs("data", exist_ok=True)

    await init_db()

    await bot.set_webhook(WEBHOOK_URL)

    logger.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")


# SHUTDOWN
async def on_shutdown(app: web.Application):

    logger.info("Bot o'chmoqda...")

    await bot.delete_webhook(drop_pending_updates=True)

    await bot.session.close()
    await dp.storage.close()


# APP CREATE
def create_app():

    app = web.Application()

    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    async def health(request):
        return web.Response(text="Bot ishlayapti")

    app.router.add_get("/", health)

    return app


# RUN SERVER
if __name__ == "__main__":

    PORT = int(os.getenv("PORT", 8080))

    logger.info(f"Server {PORT} portda ishga tushdi")

    web.run_app(create_app(), host="0.0.0.0", port=PORT)
