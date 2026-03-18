from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings
from bot.database import async_session
from bot.models import User, Payment
from sqlalchemy import select, update
from datetime import datetime, timedelta

router = Router()

@router.message(Command("premium"))
async def cmd_premium(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💎 1 Oy - {settings.PRICE_1_MONTH:,} so'm",
            callback_data="buy_1_month"
        )],
        [InlineKeyboardButton(
            text=f"💎 3 Oy - {settings.PRICE_3_MONTH:,} so'm",
            callback_data="buy_3_month"
        )],
        [InlineKeyboardButton(
            text=f"👑 Lifetime - {settings.PRICE_LIFETIME:,} so'm",
            callback_data="buy_lifetime"
        )],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_premium")]
    ])
    
    await message.answer(
        f"💎 <b>Premium Obuna</b>\n\n"
        f"✅ Cheksiz kino ko'rish\n"
        f"✅ Kunlik limitsiz\n"
        f"✅ Yangi kinolar birinchi bo'lib sizga\n"
        f"✅ Support 24/7\n\n"
        f"<b>Narxlar:</b>\n"
        f"• 1 Oy: {settings.PRICE_1_MONTH:,} so'm\n"
        f"• 3 Oy: {settings.PRICE_3_MONTH:,} so'm\n"
        f"• Lifetime: {settings.PRICE_LIFETIME:,} so'm\n\n"
        f"📩 To'lov uchun @admin_username ga yozing yoki pastdagi tugmani bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    plan = callback.data.replace("buy_", "")
    prices = {"1_month": settings.PRICE_1_MONTH, "3_month": settings.PRICE_3_MONTH, "lifetime": settings.PRICE_LIFETIME}
    amount = prices.get(plan, 0)
    
    # Payment yozuvini yaratish
    async with async_session() as session:
        payment = Payment(
            user_id=callback.from_user.id,
            amount=amount,
            plan=plan,
            payment_id=f"pay_{callback.from_user.id}_{int(datetime.now().timestamp())}"
        )
        session.add(payment)
        await session.commit()
    
    await callback.answer("💳 To'lov ma'lumotlari yuborildi", show_alert=True)
    
    # Adminlarga xabar
    for admin_id in settings.ADMIN_IDS:
        await callback.bot.send_message(
            admin_id,
            f"💰 <b>Yangi buyurtma!</b>\n\n"
            f"👤 User: {callback.from_user.first_name} (@{callback.from_user.username})\n"
            f"ID: <code>{callback.from_user.id}</code>\n"
            f"📦 Plan: {plan}\n"
            f"💵 Summa: {amount:,} so'm\n"
            f"🔖 Payment ID: <code>{payment.payment_id}</code>\n\n"
            f"✅ Tasdiqlash: /activate {callback.from_user.id} {plan}",
            parse_mode="HTML"
        )
    
    await callback.message.edit_text(
        "✅ Buyurtma qabul qilindi!\n\n"
        "📩 Admin tez orada to'lov ma'lumotlarini yuboradi.\n"
        "To'lovdan so'ng premium darhol faollashadi! 🎉",
    )

@router.callback_query(F.data == "cancel_premium")
async def cancel_premium(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("❌ Bekor qilindi")

# Admin uchun: premium faollashtirish
@router.message(Command("activate"), F.from_user.id.in_(settings.ADMIN_IDS))
async def cmd_activate_premium(message: types.Message):
    try:
        _, user_id, plan = message.text.split()
        user_id = int(user_id)
        
        # Premium muddatini hisoblash
        if plan == "1_month":
            expire = datetime.now() + timedelta(days=30)
        elif plan == "3_month":
            expire = datetime.now() + timedelta(days=90)
        else:  # lifetime
            expire = None  # Cheksiz
        
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == user_id)
                .values(is_premium=True, premium_expire=expire)
            )
            await session.commit()
        
        # Userga xabar
        try:
            await message.bot.send_message(
                user_id,
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"✅ Premium obunangiz faollashtirildi!\n"
                f"{'📅 Muddat: 30 kun' if plan == '1_month' else '📅 Muddat: 90 kun' if plan == '3_month' else '👑 Muddat: Cheksiz'}\n\n"
                f"🎬 Endi cheksiz kino ko'rishingiz mumkin!",
                parse_mode="HTML"
            )
        except:
            pass  # User botni block qilgan bo'lishi mumkin
        
        await message.answer(f"✅ User {user_id} uchun premium faollashtirildi!")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")