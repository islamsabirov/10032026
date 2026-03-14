from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMember

from bot.config import settings


async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, str | None]:
    """
    Kanal obunasini tekshiradi.

    :return: (is_member, invite_link_or_username_yoki_None)
    """
    channel = settings.required_channel
    if not channel:
        # Agar kanal ko'rsatilmagan bo'lsa, obuna talab qilinmaydi
        return True, None

    try:
        member: ChatMember = await bot.get_chat_member(chat_id=channel, user_id=user_id)
    except TelegramBadRequest:
        # Kanal topilmasa yoki boshqa xato bo'lsa, xavfsizlik uchun kirishga ruxsat bermaymiz
        return False, channel

    status = getattr(member, "status", None)
    if status in {"member", "administrator", "creator"}:
        return True, None

    return False, channel

