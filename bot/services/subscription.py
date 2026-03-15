from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMember

from bot.config import settings


async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, str | None]:
    if not settings.required_channels:
        return True, None
    
    for channel in settings.required_channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        except TelegramBadRequest:
            return False, channel
        
        status = getattr(member, "status", None)
        if status not in {"member", "administrator", "creator"}:
            return False, channel
    
    return True, None
