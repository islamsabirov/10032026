from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, update

from config import settings
from db import get_session
from db.models import User, Code, Payment

router = Router()


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi adminligini tekshirish"""
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Admin panel"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz.")
        return
    
    text = (
        "🔐 <b>Admin panel</b>\n\n"
        "📊 <b>Statistika:</b>\n"
        "/stats - umumiy statistika\n\n"
        "👥 <b>Foydalanuvchilar:</b>\n"
        "/users - foydalanuvchilar ro'yxati\n"
        "/makevip [user_id] - VIP qilish\n\n"
        "🔑 <b>Kodlar:</b>\n"
        "/addcode [kod] - yangi kod qo'shish\n"
        "/codes - barcha kodlar\n\n"
        "💰 <b>To'lovlar:</b>\n"
        "/payments - to'lovlar ro'yxati"
    )
    
    await message.answer(text)


@router.message(Command("stats"))
async def stats_handler(message: Message):
    """Statistika ko'rsatish"""
    if not is_admin(message.from_user.id):
        return
    
    async with get_session() as session:
        # Foydalanuvchilar soni
        users_count = await session.scalar(select(func.count(User.id)))
        
        # VIP foydalanuvchilar
        vip_count = await session.scalar(
            select(func.count(User.id)).where(User.is_vip == True)
        )
        
        # Kodlar soni
        codes_count = await session.scalar(select(func.count(Code.id)))
        
        # Ishlatilgan kodlar
        used_codes = await session.scalar(
            select(func.count(Code.id)).where(Code.is_used == True)
        )
        
        # To'lovlar
        payments_count = await session.scalar(select(func.count(Payment.id)))
        paid_count = await session.scalar(
            select(func.count(Payment.id)).where(Payment.status == "paid")
        )
    
    text = (
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"• Jami: {users_count}\n"
        f"• VIP: {vip_count}\n"
        f"• Oddiy: {users_count - vip_count}\n\n"
        f"🔑 <b>Kodlar:</b>\n"
        f"• Jami: {codes_count}\n"
        f"• Ishlatilgan: {used_codes}\n"
        f"• Qolgan: {codes_count - used_codes}\n\n"
        f"💰 <b>To'lovlar:</b>\n"
        f"• Jami: {payments_count}\n"
        f"• To'langan: {paid_count}\n"
        f"• Kutilayotgan: {payments_count - paid_count}"
    )
    
    await message.answer(text)


@router.message(Command("addcode"))
async def add_code(message: Message, command: CommandObject):
    """Yangi kod qo'shish"""
    if not is_admin(message.from_user.id):
        return
    
    code_text = command.args
    if not code_text:
        await message.answer("❌ Iltimos, kod matnini kiriting: /addcode KOD123")
        return
    
    async with get_session() as session:
        # Kod mavjudligini tekshirish
        existing = await session.execute(
            select(Code).where(Code.code == code_text)
        )
        if existing.scalar_one_or_none():
            await message.answer(f"❌ `{code_text}` kodi allaqachon mavjud.")
            return
        
        # Yangi kod qo'shish
        new_code = Code(code=code_text)
        session.add(new_code)
        await session.commit()
    
    await message.answer(f"✅ <code>{code_text}</code> kodi muvaffaqiyatli qo'shildi.")


@router.message(Command("makevip"))
async def make_vip(message: Message, command: CommandObject):
    """Foydalanuvchini VIP qilish"""
    if not is_admin(message.from_user.id):
        return
    
    args = command.args
    if not args or not args.isdigit():
        await message.answer("❌ Foydalanuvchi ID sini kiriting: /makevip 123456789")
        return
    
    user_id = int(args)
    
    async with get_session() as session:
        # Foydalanuvchini topish
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(f"❌ {user_id} ID li foydalanuvchi topilmadi.")
            return
        
        # VIP qilish
        user.is_vip = True
        await session.commit()
    
    await message.answer(f"✅ Foydalanuvchi <code>{user_id}</code> VIP qilindi.")


@router.message(Command("users"))
async def users_list(message: Message):
    """Foydalanuvchilar ro'yxati"""
    if not is_admin(message.from_user.id):
        return
    
    async with get_session() as session:
        result = await session.execute(
            select(User).order_by(User.joined_at.desc()).limit(10)
        )
        users = result.scalars().all()
    
    if not users:
        await message.answer("📭 Hali foydalanuvchilar yo'q.")
        return
    
    text = "📋 <b>Oxirgi 10 foydalanuvchi:</b>\n\n"
    for user in users:
        text += (
            f"🆔 <code>{user.telegram_id}</code>\n"
            f"📝 {user.first_name or ''} {user.last_name or ''}\n"
            f"👑 VIP: {'✅' if user.is_vip else '❌'}\n"
            f"📅 {user.joined_at.strftime('%d.%m.%Y')}\n"
            f"➖➖➖➖➖➖➖\n"
        )
    
    await message.answer(text)


@router.callback_query(F.data == "buy_vip")
async def buy_vip_callback(callback: CallbackQuery):
    """VIP sotib olish callback"""
    await callback.message.edit_text(
        "💳 <b>VIP obuna sotib olish</b>\n\n"
        "1️⃣ Click: 123456789\n"
        "2️⃣ Payme: 987654321\n\n"
        "To'lovdan so'ng chekni @admin ga yuboring."
    )
    await callback.answer()        
