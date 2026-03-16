from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from datetime import datetime

from db import get_session
from db.models import Code, User
from sqlalchemy import select, update

router = Router()


@router.message(Command("getcode"))
async def get_code(message: Message):
    """Yangi kod olish"""
    user_id = message.from_user.id
    
    # Foydalanuvchini tekshirish (VIP yoki yo'q)
    # Hozircha hamma olishi mumkin, keyin VIP tekshiruvi qo'shiladi
    
    async with get_session() as session:
        # Ishlatilmagan kodni topish
        result = await session.execute(
            select(Code).where(Code.is_used == False).limit(1)
        )
        code = result.scalar_one_or_none()
        
        if code:
            # Kodni ishlatilgan deb belgilash
            code.is_used = True
            code.used_by = user_id
            code.used_at = datetime.now()
            
            # Foydalanuvchini bazaga qo'shish (agar mavjud bo'lmasa)
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                new_user = User(
                    telegram_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                session.add(new_user)
            
            await session.commit()
            
            await message.answer(
                f"✅ <b>Sizning kodingiz:</b>\n"
                f"<code>{code.code}</code>\n\n"
                f"Kodni kurslarni ochish uchun ishlatishingiz mumkin."
            )
        else:
            await message.answer("❌ Kechirasiz, kodlar tugagan.")


@router.message(Command("use"))
async def use_code(message: Message, command: CommandObject):
    """Kodni ishlatish"""
    code_text = command.args
    
    if not code_text:
        await message.answer("❌ Iltimos, kodni kiriting: /use KOD123")
        return
    
    async with get_session() as session:
        # Kodni tekshirish
        result = await session.execute(
            select(Code).where(Code.code == code_text)
        )
        code = result.scalar_one_or_none()
        
        if not code:
            await message.answer("❌ Bunday kod mavjud emas.")
            return
        
        if code.is_used:
            await message.answer("❌ Bu kod allaqachon ishlatilgan.")
            return
        
        # Kodni ishlatish
        code.is_used = True
        code.used_by = message.from_user.id
        code.used_at = datetime.now()
        
        # Foydalanuvchini VIP qilish (agar kod VIP uchun bo'lsa)
        # Bu yerda kod turiga qarab ishlov berish mumkin
        
        await session.commit()
        
        await message.answer(
            f"✅ <b>Kod muvaffaqiyatli qabul qilindi!</b>\n\n"
            f"Siz endi maxsus kurslardan foydalanishingiz mumkin."
        )
