"""
╔══════════════════════════════════════════════════════════════╗
║   🎬  KinoProBot — Professional Telegram Bot                 ║
║   ✅  24/7 Polling — Render / VPS / Lokal                    ║
║   ✅  Admin panel, Statistika, Kanallar, Xabarnoma           ║
║   ✅  Majburiy obuna, Reklama, Kino kanal                    ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
from dotenv import load_dotenv

load_dotenv()  # faqat local uchun .env faylni o‘qish

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
OWNER_ID:  int = int(os.getenv("OWNER_ID"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
log = logging.getLogger("KinoPro")

if not BOT_TOKEN:
    log.critical("❌ BOT_TOKEN topilmadi!")
    log.critical("   Render → Environment Variables → BOT_TOKEN=tokeningiz")
    sys.exit(1)
if not OWNER_ID:
    log.critical("❌ OWNER_ID topilmadi!")
    log.critical("   Render → Environment Variables → OWNER_ID=12345678")
    sys.exit(1)

from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler,
    CommandHandler, MessageHandler, filters,
)
from telegram.error import (
    TelegramError, Forbidden, NetworkError,
    BadRequest, TimedOut, RetryAfter,
)
from database import db
from handlers import (
    cmd_start, cmd_help, cmd_rand,
    cmd_search, msg_handler, cb_handler,
)


async def error_handler(update: object, ctx) -> None:
    err = ctx.error
    if isinstance(err, Forbidden):
        if update and hasattr(update, "effective_user") and update.effective_user:
            db.user_mark_left(update.effective_user.id)
        return
    if isinstance(err, RetryAfter):
        log.warning(f"Flood limit: {err.retry_after}s")
        time.sleep(err.retry_after); return
    if isinstance(err, (NetworkError, TimedOut)):
        log.warning(f"Tarmoq: {err}"); return
    if isinstance(err, BadRequest):
        log.warning(f"BadRequest: {err}"); return
    log.error("Xato:", exc_info=ctx.error)
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
    me = await app.bot.get_me()
    log.info(f"✅ @{me.username} | Owner: {OWNER_ID}")
    log.info(f"👥 {db.user_count()} user | 🎬 {db.movie_count()} kino")
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
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

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
    app.add_error_handler(error_handler)

    log.info("🔄 Polling boshlandi (24/7)...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=30,
    )


if __name__ == "__main__":
    main()
