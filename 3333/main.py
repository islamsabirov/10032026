# ============================================
# ASOSIY BOT — main.py
# ============================================

import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN, WEBHOOK_URL, PORT
import database as db
from handlers import (
    # Start & Menu
    start_handler,
    check_subscription_callback,
    main_menu_callback,
    premium_menu_callback,
    buy_menu_callback,
    buy_plan_callback,
    referral_callback,
    my_profile_callback,

    # Payment
    send_screenshot_callback,
    receive_screenshot,

    # Admin
    admin_command,
    admin_stats_callback,
    admin_pending_callback,
    approve_payment_callback,
    reject_payment_callback,
    admin_broadcast_callback,
    broadcast_message_handler,
    give_premium_command,
    cancel_handler,

    # States
    WAITING_SCREENSHOT,
    WAITING_BROADCAST,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    # Database yaratish
    db.init_db()
    logger.info("✅ Database tayyor")

    app = Application.builder().token(BOT_TOKEN).build()

    # ---- SCREENSHOT ConversationHandler ----
    screenshot_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(send_screenshot_callback, pattern=r"^send_screenshot_")
        ],
        states={
            WAITING_SCREENSHOT: [
                MessageHandler(filters.PHOTO, receive_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_screenshot),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        per_user=True,
        per_chat=True,
    )

    # ---- BROADCAST ConversationHandler ----
    broadcast_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$")
        ],
        states={
            WAITING_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        per_user=True,
        per_chat=True,
    )

    # ---- HANDLERLARNI QO'SHISH ----

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("give", give_premium_command))
    app.add_handler(CommandHandler("cancel", cancel_handler))

    # Conversations
    app.add_handler(screenshot_conv)
    app.add_handler(broadcast_conv)

    # Callback queries
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(premium_menu_callback, pattern="^premium_menu$"))
    app.add_handler(CallbackQueryHandler(buy_menu_callback, pattern="^buy_menu$"))
    app.add_handler(CallbackQueryHandler(buy_plan_callback, pattern=r"^buy_(1_month|3_month|1_year|lifetime)$"))
    app.add_handler(CallbackQueryHandler(referral_callback, pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(my_profile_callback, pattern="^my_profile$"))

    # Admin callbacks
    app.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_pending_callback, pattern="^admin_pending$"))
    app.add_handler(CallbackQueryHandler(approve_payment_callback, pattern=r"^approve_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_payment_callback, pattern=r"^reject_\d+$"))

    # ---- ISHGA TUSHIRISH ----
    is_production = os.environ.get("RENDER") == "true"

    if is_production:
        # Render.com uchun Webhook
        logger.info("🚀 Webhook rejimida ishlamoqda...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        # Local uchun Polling
        logger.info("🔄 Polling rejimida ishlamoqda (local)...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
