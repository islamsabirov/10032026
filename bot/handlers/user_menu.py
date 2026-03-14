from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot import keyboards
from bot.config import settings


router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    text = (
        "Assalomu alaykum!\n\n"
        "Bu bot orqali kod kiritib kino ssilkasini olishingiz, "
        "shuningdek VIP rejimga ulanishingiz mumkin."
    )
    await message.answer(text, reply_markup=keyboards.main_menu_keyboard())


@router.callback_query(F.data == "menu:enter_code")
async def cb_enter_code(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Kino kodini kiriting (masalan, <code>ABC123</code>)."
    )
    await callback.answer()


@router.callback_query(F.data == "menu:vip")
async def cb_vip(callback: CallbackQuery) -> None:
    text = (
        "VIP rejim orqali kundalik kod limitlarisiz kino olishingiz mumkin.\n\n"
        "Quyidagi tariflardan birini tanlang:"
    )
    await callback.message.answer(text, reply_markup=keyboards.vip_tariffs_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:stats")
async def cb_stats_placeholder(callback: CallbackQuery) -> None:
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Bu bo‘lim faqat adminlar uchun.", show_alert=True)
        return

    await callback.message.answer(
        "Admin paneliga kirish uchun /admin komandasini yuboring."
    )
    await callback.answer()

