"""
╔══════════════════════════════════════════════════════════════╗
║   🎬  KinoProBot — Professional Telegram Bot                 ║
║   ✅  24/7 Polling — Render / VPS / Lokal                    ║
║   ✅  Admin panel, Statistika, Kanallar, Xabarnoma           ║
║   ✅  Majburiy obuna, Reklama, Kino kanal                    ║
╚══════════════════════════════════════════════════════════════╝
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
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
            db.user_mark_left(update.effective_user.id)
        return
    
    # Flood limit
    if isinstance(err, RetryAfter):
        log.warning(f"Flood limit: {err.retry_after}s")
        time.sleep(err.retry_after)
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


def main():
    """Asosiy funksiya"""
    log.info("🔄 Bot ishga tushyapti...")
    
    # Application yaratish
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # Handlerlarni qo'shish
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("rand",   cmd_rand))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("panel",  cmd_start))
    app.add_handler(CommandHandler("admin",  cmd_start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        msg_handler,
    ))
    
    # Error handler
    app.add_error_handler(error_handler)

    log.info("🔄 Polling boshlandi (24/7)...")
    
    # Botni ishga tushirish
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=30,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("⛔ Bot to'xtatildi (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log.critical(f"❌ Kritik xato: {e}", exc_info=True)
        sys.exit(1)
