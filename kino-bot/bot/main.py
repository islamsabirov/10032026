"""
Kino Bot - Minimal versiya
FastAPI + Aiogram 3.26.0
"""

import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from contextlib import asynccontextmanager

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot tokenini olish
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN topilmadi! Environment variables ni tekshiring.")
    raise ValueError("BOT_TOKEN topilmadi")

# Webhook sozlamalari
WEBHOOK_PATH = '/webhook'
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'kino_bot_secret')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Render URL

# Bot va dispatcher
storage = MemoryStorage()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

# Routerlarni ulash (minimal)
async def include_routers():
    logger.info("✅ Routerlarni ulash o'tkazib yuborildi (test uchun)")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Bot ishga tushmoqda...")
        await include_routers()

        if not WEBHOOK_URL:
            port = os.getenv('PORT', '8000')
            render_url = os.getenv('RENDER_EXTERNAL_URL', f'http://localhost:{port}')
            full_webhook_url = f"{render_url}{WEBHOOK_PATH}"
        else:
            full_webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

        # Webhook o'rnatish
        await bot.set_webhook(
            url=full_webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=['message', 'callback_query', 'chat_member']
        )

        # Webhook info
        webhook_info = await bot.get_webhook_info()
        logger.info(f"✅ Webhook o'rnatildi: {webhook_info.url}")

        # Bot info
        bot_info = await bot.me()
        logger.info(f"🤖 Bot: @{bot_info.username} (ID: {bot_info.id})")

    except Exception as e:
        logger.error(f"❌ Startup xatolik: {e}")

    yield

    # Shutdown
    try:
        logger.info("🛑 Bot to'xtatilmoqda...")
        await bot.delete_webhook()
        await bot.session.close()
        logger.info("✅ Bot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Shutdown xatolik: {e}")

# FastAPI ilovasi
app = FastAPI(lifespan=lifespan, title="Kino Bot API", version="1.0.0")

# Health check endpoint
@app.get("/")
@app.get("/health")
async def health_check():
    try:
        webhook_info = await bot.get_webhook_info()
        bot_info = await bot.me()
        return {
            "status": "healthy",
            "bot": {"username": bot_info.username, "id": bot_info.id, "is_running": True},
            "webhook": {"url": webhook_info.url, "pending_updates": webhook_info.pending_update_count}
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def webhook(request: Request) -> dict:
    try:
        update_data = await request.json()
        await dp.feed_update(bot, update_data)
        return {"status": "ok", "update_id": update_data.get("update_id")}
    except Exception as e:
        logger.error(f"❌ Webhook xatolik: {e}")
        return {"status": "error", "message": str(e)}

# Test endpoint
@app.get("/test")
async def test():
    return {"message": "Bot API ishlayapti!", "version": "1.0.0"}

# Ishga tushirish
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run("bot.main:app", host="0.0.0.0", port=port, reload=False)
