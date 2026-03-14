from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db import AsyncSessionMaker
from bot.db.models import Payment, User
from bot.services.codes import get_or_create_user


router = Router()


class VipStates(StatesGroup):
    waiting_screenshot = State()


TARIFFS = {
    20: 20000,  # 20 kun uchun summa (so'm)
    30: 30000,  # 30 kun uchun summa (so'm)
}


@router.callback_query(F.data.startswith("vip:plan:"))
async def cb_vip_plan(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    try:
        days = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Noto‘g‘ri tarif.", show_alert=True)
        return

    amount = TARIFFS.get(days)
    if amount is None:
        await callback.answer("Bu tarif mavjud emas.", show_alert=True)
        return

    await state.set_state(VipStates.waiting_screenshot)
    await state.update_data(days=days, amount=amount)

    text = (
        f"Tanlagan tarifingiz: {days} kun VIP.\n"
        f"To‘lov summasi: <b>{amount} so‘m</b>.\n\n"
        "To‘lovni Payme/Uzcard/Visa orqali amalga oshiring, so‘ng shu yerga "
        "to‘lov chek skrinshotini rasm sifatida yuboring.\n\n"
        "Admin to‘lovni tasdiqlaganidan keyin VIP rejim faollashadi."
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(VipStates.waiting_screenshot, F.photo)
async def handle_vip_screenshot(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    days: int = data.get("days", 0)
    amount: int = data.get("amount", 0)

    if not days or not amount:
        await message.answer("Tarif ma'lumotlari topilmadi. Iltimos, VIP menyudan qayta tanlang.")
        await state.clear()
        return

    async with AsyncSessionMaker() as session:  # type: AsyncSession
        user: User = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )

        payment = Payment(
            user_id=user.id,
            amount=amount,
            days=days,
            status="pending",
        )
        session.add(payment)
        await session.flush()
        await session.commit()

    # Adminlarga xabar yuborish
    caption = (
        f"Yangi VIP to‘lov so‘rovi #{payment.id}\n"
        f"Foydalanuvchi: @{message.from_user.username or message.from_user.id}\n"
        f"Telegram ID: {message.from_user.id}\n"
        f"Tarif: {days} kun\n"
        f"Summa: {amount} so‘m"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=f"payment:approve:{payment.id}",
        ),
        InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"payment:reject:{payment.id}",
        ),
    )

    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=kb.as_markup(),
            )
        except Exception:
            continue

    await message.answer(
        "To‘lov chek skrinshoti adminlarga yuborildi. Iltimos, tasdiqlashni kuting."
    )
    await state.clear()

