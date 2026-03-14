from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import AsyncSessionMaker
from bot.services.codes import get_movie_by_code, get_or_create_user, register_code_usage
from bot.services.limits import can_use_code
from bot.services.subscription import check_subscription


router = Router()

# Oddiy foydalanuvchi uchun kunlik kod limiti
DAILY_LIMIT = 3


@router.message(F.text & ~F.text.startswith("/"))
async def handle_code(message: Message) -> None:
    code = message.text.strip()
    if not code:
        return

    bot = message.bot

    # Avval kanal obunasini tekshiramiz
    is_member, channel_link = await check_subscription(bot, message.from_user.id)
    if not is_member:
        text = (
            "Kod ishlatishdan oldin kanalga obuna bo‘lishingiz kerak.\n\n"
            f"👉 Kanal: {channel_link}\n"
            "Obuna bo‘lgach, yana kodni yuboring."
        )
        await message.answer(text)
        return

    async with AsyncSessionMaker() as session:  # type: AsyncSession
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )

        # Limit tekshiruvi
        if not await can_use_code(session, user, DAILY_LIMIT):
            await message.answer(
                "Bugungi kunlik kod limitidan oshib ketdingiz. "
                "Ertaga yana urinib ko‘ring yoki VIP bo‘lishni o‘ylab ko‘ring."
            )
            return

        movie = await get_movie_by_code(session, code)
        if movie is None:
            await message.answer("❌ Bunday kod topilmadi yoki kino o‘chirib tashlangan.")
            return

        await register_code_usage(session, user, movie)
        await session.commit()

    await message.answer(
        f"✅ Kod tasdiqlandi.\n\nKino ssilkasi:\n{movie.channel_post_link}"
    )

