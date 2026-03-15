from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import logging
import os

from .config import settings
from .handlers import admin_router, codes_router, user_menu_router, vip_router
from .db import init_db


WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{settings.webhook_url}{WEBHOOK_PATH}"


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    await init_db()
    logging.info("Webhook o'rnatildi!")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook o'chirildi.")


def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    dp.include_router(user_menu_router)
    dp.include_router(codes_router)
    dp.include_router(vip_router)
    dp.include_router(admin_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )

    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Server {port}-portda ishga tushyapti...")

    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
