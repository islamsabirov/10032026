from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards
from bot.config import settings
from bot.db import AsyncSessionMaker
from bot.db.models import Movie, Payment, User
from bot.services.stats import get_basic_stats, get_latest_vip_users
from bot.services.vip import get_payment_by_id, set_vip


router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(F.text == "/admin")
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Bu bo‘lim faqat adminlar uchun.")
        return

    await message.answer(
        "Admin paneliga xush kelibsiz. Kerakli bo‘limni tanlang:",
        reply_markup=keyboards.admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    async with AsyncSessionMaker() as session:  # type: AsyncSession
        stats = await get_basic_stats(session)

    text = (
        "📈 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"🎬 Aktiv kinolar: {stats['active_movies']}\n"
        f"🔢 Jami kod ishlatilishlari: {stats['total_code_usages']}\n"
        f"📅 Bugungi kod ishlatilishlari: {stats['today_code_usages']}\n"
        f"👑 Aktiv VIP foydalanuvchilar: {stats['active_vip_users']}\n"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "admin:vip_users")
async def cb_admin_vip_users(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    async with AsyncSessionMaker() as session:  # type: AsyncSession
        users = await get_latest_vip_users(session)

    if not users:
        await callback.message.answer("Hozircha VIP foydalanuvchilar yo‘q.")
        await callback.answer()
        return

    lines = ["👑 <b>VIP foydalanuvchilar</b> (so‘nggi)"]
    for u in users:
        line = f"- ID: {u.telegram_id}"
        if u.username:
            line += f" (@{u.username})"
        if u.vip_until:
            line += f" — VIP tugash sanasi: {u.vip_until.date()}"
        lines.append(line)

    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "admin:add_movie")
async def cb_admin_add_movie_info(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    text = (
        "Yangi kino qo‘shish uchun quyidagi formatda xabar yuboring:\n\n"
        "<code>/addmovie CODE | Kino nomi | https://t.me/channel/123</code>"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(F.text.startswith("/addmovie"))
async def cmd_add_movie(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    try:
        _, rest = message.text.split(" ", 1)
        code, title, link = [part.strip() for part in rest.split("|", 3)[:3]]
    except ValueError:
        await message.answer(
            "Noto‘g‘ri format.\nTo‘g‘ri format:\n"
            "<code>/addmovie CODE | Kino nomi | https://t.me/channel/123</code>"
        )
        return

    async with AsyncSessionMaker() as session:  # type: AsyncSession
        stmt = select(Movie).where(Movie.code == code)
        result = await session.execute(stmt)
        movie = result.scalar_one_or_none()
        if movie:
            movie.title = title
            movie.channel_post_link = link
            movie.is_active = True
        else:
            movie = Movie(
                code=code,
                title=title,
                channel_post_link=link,
                is_active=True,
            )
            session.add(movie)
        await session.commit()

    await message.answer("Kino muvaffaqiyatli saqlandi.")


@router.callback_query(F.data == "admin:delete_movie")
async def cb_admin_delete_movie_info(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    await callback.message.answer(
        "Kino o‘chirish uchun kodni yuboring:\n<code>/delmovie CODE</code>"
    )
    await callback.answer()


@router.message(F.text.startswith("/delmovie"))
async def cmd_del_movie(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Kod ko‘rsatilmagan. Format: <code>/delmovie CODE</code>")
        return

    code = parts[1].strip()
    async with AsyncSessionMaker() as session:  # type: AsyncSession
        stmt = select(Movie).where(Movie.code == code)
        result = await session.execute(stmt)
        movie = result.scalar_one_or_none()
        if not movie:
            await message.answer("Bu kod bo‘yicha kino topilmadi.")
            return

        movie.is_active = False
        await session.commit()

    await message.answer("Kino o‘chirildi (faolsizlantirildi).")


@router.callback_query(F.data.startswith("payment:"))
async def cb_payment_action(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Noto‘g‘ri format.", show_alert=True)
        return

    action, payment_id_str = parts[1], parts[2]
    try:
        payment_id = int(payment_id_str)
    except ValueError:
        await callback.answer("Noto‘g‘ri payment ID.", show_alert=True)
        return

    async with AsyncSessionMaker() as session:  # type: AsyncSession
        payment = await get_payment_by_id(session, payment_id)
        if not payment:
            await callback.answer("To‘lov topilmadi.", show_alert=True)
            return

        stmt = select(User).where(User.id == payment.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
            return

        if action == "approve":
            payment.status = "approved"
            await set_vip(session, user, payment.days)
            await session.commit()

            try:
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "🎉 VIP rejimingiz faollashtirildi!\n"
                        f"Muddati: {payment.days} kun."
                    ),
                )
            except Exception:
                pass

            await callback.message.edit_caption(
                (callback.message.caption or "") + "\n\n✅ Admin tomonidan tasdiqlandi."
            )
            await callback.answer("To‘lov tasdiqlandi.")
        elif action == "reject":
            payment.status = "rejected"
            await session.commit()

            try:
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text="❌ VIP to‘lovingiz admin tomonidan rad etildi.",
                )
            except Exception:
                pass

            await callback.message.edit_caption(
                (callback.message.caption or "") + "\n\n❌ Admin tomonidan rad etildi."
            )
            await callback.answer("To‘lov rad etildi.")
        else:
            await callback.answer("Noto‘g‘ri amal.", show_alert=True)

