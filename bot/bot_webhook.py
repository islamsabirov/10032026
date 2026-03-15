# bot_webhook.py

import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.filters import Command
from dotenv import load_dotenv

# 1️⃣ .env faylni o‘qish
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# 2️⃣ Logging
logging.basicConfig(level=logging.INFO)

# 3️⃣ Bot va Dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 4️⃣ Webhook route
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://one0032026.onrender.com{WEBHOOK_PATH}"

# 5️⃣ /start handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Bot ishga tushdi! ✅")

# 6️⃣ Webhook POST handler
async def handle(request):
    update = Update(**await request.json())
    await dp.process_update(update)
    return web.Response(text="ok")

# 7️⃣ Aiohttp server sozlamalari
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)

# 8️⃣ Browser uchun GET route (server ishlashini tekshirish)
app.router.add_get("/", lambda request: web.Response(text="Bot server ishlayapti ✅"))

# 9️⃣ Webhookni o‘rnatish
async def on_startup(app):
    logging.info("Webhook o‘rnatilyapti...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

app.on_startup.append(on_startup)

# 10️⃣ Serverni ishga tushirish
if __name__ == "__main__":
    logging.info("Server ishga tushmoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)
