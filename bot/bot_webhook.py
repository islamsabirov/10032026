# bot_webhook.py

import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.filters import Command
from dotenv import load_dotenv

# 1️⃣ .env faylni o‘qish
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# 2️⃣ Logging sozlash
logging.basicConfig(level=logging.INFO)

# 3️⃣ Bot va Dispatcher yaratish
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 4️⃣ Webhook route
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://one0032026.onrender.com{WEBHOOK_PATH}"  # domain + route

# 5️⃣ Oddiy /start handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Bot ishga tushdi! ✅")

# 6️⃣ Webhook handler (Telegram xabarlarini qabul qiladi)
async def handle(request):
    update = Update(**await request.json())
    await dp.process_update(update)
    return web.Response(text="ok")

# 7️⃣ Aiohttp server sozlamalari
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)

# 8️⃣ Bot webhookni o‘rnatish
async def on_startup(app):
    logging.info("Webhook o‘rnatilyapti...")
    # avval eski webhookni o‘chirib tashlash
    await bot.delete_webhook(drop_pending_updates=True)
    # yangi webhookni o‘rnatish
    await bot.set_webhook(WEBHOOK_URL)

app.on_startup.append(on_startup)

# 9️⃣ Serverni ishga tushirish
if __name__ == "__main__":
    logging.info("Server ishga tushmoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)
