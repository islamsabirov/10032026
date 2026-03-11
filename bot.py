import os
import sys
import time
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# .env faylini yuklash (local uchun)
load_dotenv()

# Logging sozlamalari (ENG BOSHIDA!)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
log = logging.getLogger("KinoPro")

# Environment variables
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID_STR: str = os.getenv("OWNER_ID", "")

# Token tekshirish
if not BOT_TOKEN:
    log.critical("❌ BOT_TOKEN topilmadi!")
    log.critical("   Render → Environment Variables → BOT_TOKEN=tokeningiz")
    sys.exit(1)

# OWNER_ID tekshirish
if not OWNER_ID_STR:
    log.critical("❌ OWNER_ID topilmadi!")
    log.critical("   Render → Environment Variables → OWNER_ID=12345678")
    sys.exit(1)

try:
    OWNER_ID = int(OWNER_ID_STR)
except ValueError:
    log.critical("❌ OWNER_ID raqam bo'lishi kerak!")
    sys.exit(1)

# Importlar (environment variables tekshirilgandan keyin)
from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler,
    CommandHandler, MessageHandler, filters,
)
from telegram.error import (
    TelegramError, Forbidden, NetworkError,
    BadRequest, TimedOut, RetryAfter,
)

# Local importlar
from database import db
from handlers import (
    cmd_start, cmd_help, cmd_rand,
    cmd_search, msg_handler, cb_handler,
)


async def error_handler(update: object, ctx) -> None:
    """Global xatolik handleri"""
    err = ctx.error
    
    # Foydalanuvchi botni bloklagan
    if isinstance(err, Forbidden):
        if update and hasattr(update, "effective_user") and update.effective_user:
            try:
                db.user_mark_left(update.effective_user.id)
            except:
                pass
        return
    
    # Flood limit
    if isinstance(err, RetryAfter):
        log.warning(f"Flood limit: {err.retry_after}s")
        await asyncio.sleep(err.retry_after)
        return
    
    # Tarmoq xatolari
    if isinstance(err, (NetworkError, TimedOut)):
        log.warning(f"Tarmoq xatosi: {err}")
        return
    
    # Bad request
    if isinstance(err, BadRequest):
        log.warning(f"BadRequest: {err}")
        return
    
    # Boshqa xatolar
    log.error("Xatolik yuz berdi:", exc_info=ctx.error)
    
    # Owner ga xabar berish
    try:
        await ctx.bot.send_message(
            OWNER_ID,
            f"⚠️ <b>Bot xatosi!</b>\n\n"
            f"<code>{type(err).__name__}: {str(err)[:300]}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass


async def on_startup(app: Application) -> None:
    """Bot ishga tushganda"""
    try:
        me = await app.bot.get_me()
        log.info(f"✅ @{me.username} | Owner: {OWNER_ID}")
        log.info(f"👥 {db.user_count()} user | 🎬 {db.movie_count()} kino")
        
        # Owner ga xabar
        try:
            await app.bot.send_message(
                OWNER_ID,
                f"🟢 <b>KinoProBot ishga tushdi!</b>\n\n"
                f"🤖 @{me.username}\n"
                f"👥 Foydalanuvchilar: <b>{db.user_count()}</b>\n"
                f"🎬 Kinolar: <b>{db.movie_count()}</b>\n"
                f"📡 Polling 24/7\n\n"
                f"📌 /start yuboring — panel ochiladi",
                parse_mode="HTML",
            )
        except TelegramError:
            pass
    except Exception as e:
        log.error(f"Startup xatosi: {e}")


# 🚀 RENDER UCHUN: Minimal web server (port xatosini oldini olish uchun)
async def health_check_server():
    """Render health check uchun minimal web server"""
    try:
        from aiohttp import web
        
        async def handle(request):
            return web.Response(text="Bot is running!")
        
        app = web.Application()
        app.router.add_get('/', handle)
        app.router.add_get('/health', handle)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Render 10000-portni kutadi
        port = int(os.getenv("PORT", 10000))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        log.info(f"✅ Health check server running on port {port}")
    except ImportError:
        log.warning("⚠️ aiohttp o'rnatilmagan, web server ishlamaydi")
    except Exception as e:
        log.error(f"Web server xatosi: {e}")


async def run_bot():
    """Botni asinxron ishga tushirish"""
    log.info("🔄 Bot ishga tushyapti...")
    
    # Application yaratish
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # Handlerlarni qo'shish
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("rand", cmd_rand))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("panel", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        msg_handler,
    ))
    
    # Error handler
    app.add_error_handler(error_handler)

    log.info("🔄 Polling boshlandi (24/7)...")
    
    # Botni ishga tushirish - PTB 21.6 uchun to'g'ri parametrlar
    await app.initialize()
    await app.start()
    
    # Polling ni boshlash
    try:
        await app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            read_timeout=30,
            write_timeout=30,
            connect_timeout=30,
            pool_timeout=30,
        )
        
        # Botni cheksiz ishga tushirish
        while True:
            await asyncio.sleep(3600)  # 1 soat
            log.debug("Bot ishlayapti...")
            
    except Exception as e:
        log.error(f"Polling xatosi: {e}")
    finally:
        await app.stop()


async def main():
    """Asosiy funksiya"""
    # Render uchun health check serverni ishga tushirish
    asyncio.create_task(health_check_server())
    
    # Botni ishga tushirish
    await run_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("⛔ Bot to'xtatildi (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log.critical(f"❌ Kritik xato: {e}", exc_info=True)
        sys.exit(1)
