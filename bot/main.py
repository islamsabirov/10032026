import sys
import os
import logging
from aiohttp import web

# Python path-ga root va bot papkalarni qo‘shish
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings
from db import init_db
from handlers import admin_router, codes_router, user_menu_router, vip_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{settings.webhook_url}{WEBHOOK_PATH}"

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# ---------------- Startup / Shutdown ----------------
async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    logger.info("Bot shutdown boshlandi...")
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    await bot.session.close()
    logger.info("Bot sessiyasi yopildi")

# ---------------- Initialize Routers ----------------
async def init_app():
    dp.include_router(user_menu_router)
    dp.include_router(codes_router)
    dp.include_router(vip_router)
    dp.include_router(admin_router)
    logger.info("Database ishga tushmoqda...")
    await init_db()

# ---------------- Create aiohttp App ----------------
async def create_app():
    await init_app()
    app = web.Application()

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Health check
    async def health(request):
        return web.Response(text="Bot is running", status=200)

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    return app

# ---------------- Command / Menu Handlers ----------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🎬 Kino qo‘shish", "🎟 VIP")
        kb.add("🛠 Admin")
        await message.answer("Salom! Botga xush kelibsiz. Menyudan tanlang:", reply_markup=kb)
    except Exception as e:
        logger.error(f"Start command xato: {e}")

@dp.message(F.text == "🎬 Kino qo‘shish")
async def menu_add_movie(message: types.Message):
    try:
        if message.from_user.id not in settings.admin_ids:
            await message.answer("Siz admin emassiz, kino qo‘sha olmaysiz!")
            return
        await message.answer("Kino qo‘shish funktsiyasi ishlamoqda...")
        # Bu yerga admin_router/kino qo‘shish funksiyasini chaqirish mumkin
    except Exception as e:
        logger.error(f"Kino qo‘shish xato: {e}")

@dp.message(F.text == "🎟 VIP")
async def menu_vip(message: types.Message):
    try:
        await message.answer("VIP bo‘limiga xush kelibsiz!")
    except Exception as e:
        logger.error(f"VIP menyu xato: {e}")

@dp.message(F.text == "🛠 Admin")
async def menu_admin(message: types.Message):
    try:
        if message.from_user.id in settings.admin_ids:
            await message.answer("Admin bo‘limiga xush kelibsiz!")
        else:
            await message.answer("Siz admin emassiz!")
    except Exception as e:
        logger.error(f"Admin menyu xato: {e}")

# ---------------- Inline Example ----------------
@dp.callback_query(F.data == "confirm_add")
async def callback_confirm_add(callback: types.CallbackQuery):
    try:
        await callback.message.answer("Kino qo‘shildi ✅")
        await callback.answer()
    except Exception as e:
        logger.error(f"Callback xato: {e}")

# ---------------- Main ----------------
async def main():
    app = await create_app()
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Server {port} portda ishga tushdi")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
