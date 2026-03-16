from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Start komandasi"""
    welcome_text = (
        f"👋 Assalomu alaykum, {message.from_user.full_name}!\n\n"
        "🤖 Botimizga xush kelibsiz. Quyidagi menyudan foydalanishingiz mumkin:\n"
        "📚 Kurslar - barcha kurslar ro'yxati\n"
        "👤 Profil - shaxsiy ma'lumotlar\n"
        "🔑 Kod kiritish - maxsus kodni kiritish\n"
        "❓ Yordam - botdan foydalanish"
    )
    
    # Menyu tugmalari
    kb = ReplyKeyboardBuilder()
    kb.button(text="📚 Kurslar")
    kb.button(text="👤 Profil")
    kb.button(text="🔑 Kod kiritish")
    kb.button(text="❓ Yordam")
    kb.adjust(2)  # 2 ustun
    
    await message.answer(welcome_text, reply_markup=kb.as_markup(resize_keyboard=True))


@router.message(Command("menu"))
async def show_menu(message: Message):
    """Menyu ko'rsatish"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Kurslar"), KeyboardButton(text="👤 Profil")],
            [KeyboardButton(text="🔑 Kod kiritish"), KeyboardButton(text="❓ Yordam")]
        ],
        resize_keyboard=True
    )
    await message.answer("📋 Asosiy menyu:", reply_markup=kb)


@router.message(lambda msg: msg.text == "👤 Profil")
async def profile_handler(message: Message):
    """Profil ma'lumotlari"""
    user = message.from_user
    text = (
        f"👤 <b>Sizning profilingiz:</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📝 Ism: {user.full_name}\n"
        f"🔗 Username: @{user.username if user.username else 'yo‘q'}\n"
        f"⭐ VIP: {'✅ Ha' if False else '❌ Yo‘q'}"  # Bu yerda DB dan tekshirish kerak
    )
    await message.answer(text)


@router.message(lambda msg: msg.text == "📚 Kurslar")
async def courses_handler(message: Message):
    """Kurslar ro'yxati"""
    text = (
        "📚 <b>Mavjud kurslar:</b>\n\n"
        "1. Python asoslari - 3 oy\n"
        "2. Web dasturlash - 4 oy\n"
        "3. Telegram botlar - 2 oy\n\n"
        "Batafsil ma'lumot uchun /course nomi"
    )
    await message.answer(text)


@router.message(lambda msg: msg.text == "❓ Yordam")
async def help_handler(message: Message):
    """Yordam bo'limi"""
    text = (
        "❓ <b>Botdan foydalanish:</b>\n\n"
        "/start - botni ishga tushirish\n"
        "/menu - asosiy menyu\n"
        "/getcode - kod olish (VIP)\n"
        "/vip - VIP haqida ma'lumot\n"
        "/buyvip - VIP sotib olish\n\n"
        "Admin bilan bog'lanish: @admin"
    )
    await message.answer(text)


@router.message(lambda msg: msg.text == "🔑 Kod kiritish")
async def enter_code_handler(message: Message):
    """Kod kiritish bo'limi"""
    text = (
        "🔑 <b>Kod kiritish</b>\n\n"
        "Maxsus kodingiz bo'lsa, uni quyidagi formatda yuboring:\n"
        "<code>/use KOD123</code>\n\n"
        "Agar kodingiz bo'lmasa, /getcode orqali olishingiz mumkin."
    )
    await message.answer(text)
