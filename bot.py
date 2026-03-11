import os
import sys
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import atexit
import signal

# .env faylini yuklash
load_dotenv()

# Logging sozlamalari
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID_STR = os.getenv("OWNER_ID", "")

# Token tekshirish
if not BOT_TOKEN:
    log.critical("❌ BOT_TOKEN topilmadi!")
    sys.exit(1)

if not OWNER_ID_STR:
    log.critical("❌ OWNER_ID topilmadi!")
    sys.exit(1)

try:
    OWNER_ID = int(OWNER_ID_STR)
except ValueError:
    log.critical("❌ OWNER_ID raqam bo'lishi kerak!")
    sys.exit(1)

# Telegram imports
from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler,
    CommandHandler, MessageHandler, filters,
)
from telegram.error import Forbidden, NetworkError, BadRequest, TimedOut, RetryAfter, TelegramError

# Local imports
from database import db
from handlers import cmd_start, cmd_help, cmd_rand, cmd_search, msg_handler, cb_handler


# Global error handler
async def error_handler(update, ctx):
    err = ctx.error
    if isinstance(err, Forbidden):
        if update and hasattr(update, "effective_user") and update.effective_user:
            try:
                db.user_mark_left(update.effective_user.id)
            except:
                pass
        return

    if isinstance(err, RetryAfter):
        log.warning(f"Flood limit: {err.retry_after}s")
        await asyncio.sleep(err.retry_after)
        return

    if isinstance(err, (NetworkError, TimedOut)):
        log.warning(f"Tarmoq xatosi: {err}")
        return

    if isinstance(err, BadRequest):
        log.warning(f"BadRequest: {err}")
        return

    log.error("Xatolik yuz berdi:", exc_info=err)
    try:
        await ctx.bot.send_message(
            OWNER_ID,
            f"⚠️ <b>Bot xatosi!</b>\n<code>{type(err).__name__}: {str(err)[:300]}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# Bot startup
async def on_startup(app: Application):
    try:
        me = await app.bot.get_me()
        log.info(f"✅ @{me.username} | Owner: {OWNER_ID}")
        log.info(f"👥 {db.user_count()} user | 🎬 {db.movie_count()} kino")
        try:
            await app.bot.send_message(
                OWNER_ID,
                f"🟢 <b>KinoProBot ishga tushdi!</b>\n"
                f"🤖 @{me.username}\n"
                f"👥 Foydalanuvchilar: <b>{db.user_count()}</b>\n"
                f"🎬 Kinolar: <b>{db.movie_count()}</b>\n"
                f"📡 Polling 24/7",
                parse_mode="HTML",
            )
        except TelegramError:
            pass
    except Exception as e:
        log.error(f"Startup xatosi: {e}")


# Minimal health check server (Render)
async def health_check_server():
    try:
        from aiohttp import web

        async def handle(request):
            return web.Response(text="Bot is running!")

        app = web.Application()
        app.router.add_get("/", handle)
        app.router.add_get("/health", handle)

        runner = web.AppRunner(app)
        await runner.setup()

        port = int(os.getenv("PORT", 10000))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        log.info(f"✅ Health check server running on port {port}")
    except ImportError:
        log.warning("⚠️ aiohttp o'rnatilmagan, web server ishlamaydi")
    except Exception as e:
        log.error(f"Web server xatosi: {e}")


# Lock fayl
lock_file = "/tmp/bot.lock"
if os.path.exists(lock_file):
    log.critical("❌ Bot allaqachon ishlayapti!")
    sys.exit(1)

with open(lock_file, "w") as f:
    f.write(str(os.getpid()))

atexit.register(lambda: os.remove(lock_file) if os.path.exists(lock_file) else None)


# Signal handling
async def shutdown():
    log.info("🛑 Bot to'xtatilmoqda...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [t.cancel() for t in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("✅ Shutdown complete.")
    sys.exit(0)


def setup_signal_handlers(loop):
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    except NotImplementedError:
        log.warning("Signal handlers container muhitida ishlamasligi mumkin.")


# Bot run
async def run_bot():
    log.info("🔄 Bot ishga tushyapti...")

    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("rand", cmd_rand))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("panel", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, msg_handler))
    app.add_error_handler(error_handler)

    # Polling
    await app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# Main
async def main():
    # Signal handler
    loop = asyncio.get_running_loop()
    setup_signal_handlers(loop)

    # Health check
    asyncio.create_task(health_check_server())

    # Bot
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
