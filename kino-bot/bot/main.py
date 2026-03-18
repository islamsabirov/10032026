import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI, Request
from aiogram.webhook.aiohttp_server import setup_application

from bot.config import settings
from bot.database import init_db
from bot.handlers import user, admin, premium

# ======================
# Logging
# ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================
# Bot & Dispatcher
# ======================
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Routers
dp.include_routers(user.router, admin.router, premium.router)

# ======================
# FastAPI app (Webhooks)
# ======================
app = FastAPI()

@app.get("/")
async def health():
    """Health check endpoint"""
    me = await bot.get_me()
    return {"status": "ok", "bot": me.username}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhook updates"""
    try:
        update_json = await request.json()
        update = types.Update(**update_json)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.exception("Webhook error:")
        return {"ok": False, "error": str(e)}

# ======================
# Startup & Shutdown
# ======================
async def on_startup():
    """Bot va DB ishga tushirish"""
    await init_db()
    if settings.WEBHOOK_URL:
        await bot.set_webhook(
            f"{settings.WEBHOOK_URL}/webhook",
            allowed_updates=dp.resolve_used_update_types()
        )
        logger.info(f"✅ Webhook set: {settings.WEBHOOK_URL}/webhook")

async def on_shutdown():
    """Bot to‘xtaganda resurslarni tozalash"""
    await bot.session.close()
    logger.info("🔴 Bot stopped")

# ======================
# Polling (local)
# ======================
def run_polling():
    """Local development uchun polling"""
    async def main():
        await on_startup()
        try:
            logger.info("🚀 Bot polling started")
            await dp.start_polling(bot)
        finally:
            await on_shutdown()

    asyncio.run(main())

# ======================
# Webhook (Render yoki hosting)
# ======================
def run_webhook():
    """Render yoki webhook hosting uchun FastAPI + Aiogram"""
    setup_application(app, dp, bot=bot)
    return app

# ======================
# Entry point
# ======================
if __name__ == "__main__":
    import sys
    if "--webhook" in sys.argv:
        run_webhook()
    else:
        run_polling()
