from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.message(Command("vip"))
async def vip_info(message: Message):
    """VIP haqida ma'lumot"""
    text = (
        "👑 <b>VIP foydalanuvchilar uchun imkoniyatlar:</b>\n\n"
        "✅ Kunlik 5 ta kod olish\n"
        "✅ Yangi kurslardan birinchi bo'lib xabardor bo'lish\n"
        "✅ Maxsus VIP kanalga qo'shilish\n"
        "✅ Barcha kurslarga chegirma\n"
        "✅ Shaxsiy kurator\n\n"
        "⭐ <b>VIP obuna narxi:</b> 50 000 so'm/oy\n\n"
        "VIP bo'lish uchun /buyvip"
    )
    
    # Inline tugmalar
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Sotib olish", callback_data="buy_vip")
    kb.button(text="❓ Savol-javob", callback_data="vip_faq")
    kb.adjust(1)
    
    await message.answer(text, reply_markup=kb.as_markup())


@router.message(Command("buyvip"))
async def buy_vip(message: Message):
    """VIP sotib olish"""
    text = (
        "💳 <b>VIP obuna sotib olish</b>\n\n"
        "To'lov qilish uchun quyidagi ma'lumotlardan birini tanlang:\n\n"
        "1️⃣ Click: 123456789\n"
        "2️⃣ Payme: 987654321\n"
        "3️⃣ Uzum Bank: 555667788\n\n"
        "To'lovdan so'ng chekni @admin ga yuboring."
    )
    
    # To'lov variantlari
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Click", url="https://click.uz")],
            [InlineKeyboardButton(text="✅ Payme", url="https://payme.uz")],
            [InlineKeyboardButton(text="📞 Admin bilan bog'lanish", url="https://t.me/admin")]
        ]
    )
    
    await message.answer(text, reply_markup=kb)


@router.message(Command("vipmenu"))
async def vip_menu(message: Message):
    """VIP menyu (faqat VIP lar uchun)"""
    # Bu yerda VIP tekshiruvi bo'lishi kerak
    text = (
        "👑 <b>VIP menyu:</b>\n\n"
        "/getcode - kod olish\n"
        "/vipcourse - maxsus kurslar\n"
        "/vipchat - VIP chat\n"
        "/vipsupport - VIP yordam"
    )
    await message.answer(text)
