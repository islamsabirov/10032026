"""
Kino Bot - Asosiy fayl
FastAPI + Aiogram 3.15.0
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

# Handlerlarni kechiktirib import qilish (circular import oldini olish)
async def include_routers():
    """Routerlarni ulash"""
    try:
        from bot.handlers import user, admin, premium
        
        dp.include_router(user.router)
        dp.include_router(admin.router)
        dp.include_router(premium.router)
        
        logger.info("✅ Routerlar muvaffaqiyatli ulandi")
    except Exception as e:
        logger.error(f"❌ Routerlarni ulashda xatolik: {e}")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup va shutdown eventlari
    """
    # Startup
    try:
        logger.info("🚀 Bot ishga tushmoqda...")
        
        # Routerlarni ulash
        await include_routers()
        
        # Webhook URL ni yaratish
        if not WEBHOOK_URL:
            port = os.getenv('PORT', '10000')
            render_url = os.getenv('RENDER_EXTERNAL_URL', f'http://localhost:{port}')
            full_webhook_url = f"{render_url}{WEBHOOK_PATH}"
        else:
            full_webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        
        # Webhook ni o'rnatish
        await bot.set_webhook(
            url=full_webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=['message', 'callback_query', 'chat_member']
        )
        
        # Webhook info
        webhook_info = await bot.get_webhook_info()
        logger.info(f"✅ Webhook o'rnatildi: {webhook_info.url}")
        
        # Bot ma'lumotlari
        bot_info = await bot.me()
        logger.info(f"🤖 Bot: @{bot_info.username} (ID: {bot_info.id})")
        
    except Exception as e:
        logger.error(f"❌ Startup xatolik: {e}")
    
    yield  # App ishlaydi
    
    # Shutdown
    try:
        logger.info("🛑 Bot to'xtatilmoqda...")
        await bot.delete_webhook()
        await bot.session.close()
        logger.info("✅ Bot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Shutdown xatolik: {e}")

# FastAPI ilovasi
app = FastAPI(
    title="Kino Bot API",
    description="Telegram kino boti uchun webhook server",
    version="1.0.0",
    lifespan=lifespan
)

# Health check endpoint
@app.get("/")
@app.get("/health")
async def health_check():
    """Bot holatini tekshirish"""
    try:
        webhook_info = await bot.get_webhook_info()
        bot_info = await bot.me()
        
        return {
            "status": "healthy",
            "bot": {
                "username": bot_info.username,
                "id": bot_info.id,
                "is_running": True
            },
            "webhook": {
                "url": webhook_info.url,
                "pending_updates": webhook_info.pending_update_count,
                "is_set": webhook_info.url is not None
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def webhook(request: Request) -> dict:
    """
    Telegram dan kelgan update larni qabul qilish
    """
    try:
        # Request body ni o'qish
        update_data = await request.json()
        logger.debug(f"📩 Webhook keldi: {update_data.get('update_id')}")
        
        # Update ni dispatcher ga yuborish
        await dp.feed_update(bot, update_data)
        
        return {
            "status": "ok",
            "update_id": update_data.get('update_id')
        }
    except Exception as e:
        logger.error(f"❌ Webhook xatolik: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

# Webhook status endpoint
@app.get("/webhook-info")
async def webhook_info():
    """Webhook sozlamalari haqida ma'lumot"""
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "max_connections": webhook_info.max_connections,
            "last_error_date": str(webhook_info.last_error_date) if webhook_info.last_error_date else None,
            "last_error_message": webhook_info.last_error_message,
            "last_synchronization_error_date": str(webhook_info.last_synchronization_error_date) if webhook_info.last_synchronization_error_date else None,
            "allowed_updates": webhook_info.allowed_updates
        }
    except Exception as e:
        return {"error": str(e)}

# Bot info endpoint
@app.get("/bot-info")
async def bot_info():
    """Bot haqida ma'lumot"""
    try:
        bot_data = await bot.me()
        return {
            "id": bot_data.id,
            "username": bot_data.username,
            "first_name": bot_data.first_name,
            "can_join_groups": bot_data.can_join_groups,
            "can_read_all_group_messages": bot_data.can_read_all_group_messages,
            "supports_inline_queries": bot_data.supports_inline_queries
        }
    except Exception as e:
        return {"error": str(e)}

# Test endpoint
@app.get("/test")
async def test():
    """Test endpoint"""
    return {
        "message": "Bot API ishlayapti!",
        "version": "1.0.0",
        "aiogram_version": "3.15.0",
        "fastapi_version": "0.115.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        "bot.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Production da reload=False bo'lishi kerak
    )
